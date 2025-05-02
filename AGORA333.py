
# --- Imports ---
import streamlit as st
import pandas as pd
import praw
import gspread
from google.oauth2.service_account import Credentials
from textblob import TextBlob
from collections import defaultdict
from datetime import datetime, timedelta
from openai import OpenAI
import uuid
from PIL import Image
import plotly.express as px
import time
import random

# --- Page Config ---
st.set_page_config(
    page_title="Agora — Public Sentiment Field",
    page_icon=":crystal_ball:",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Ensure session state keys exist ---
if "has_entered" not in st.session_state:
    st.session_state.has_entered = False

if "field_name" not in st.session_state:
    st.session_state.field_name = ""

# --- Helper Functions ---
def add_fade_in_styles():
    st.markdown("""
    <style>
    .fade-in {
        animation: fadeInAnimation 2s ease forwards;
        opacity: 0;
    }

    @keyframes fadeInAnimation {
        to {
            opacity: 1;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def add_button_glow():
    st.markdown("""
    <style>
    .stButton > button {
        border: none;
        padding: 10px 30px;
        border-radius: 20px;
        background-color: #333;
        color: #ccc;
        font-size: 18px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #444;
        box-shadow: 0 0 15px gold;
        color: #fff;
    }
    </style>
    """, unsafe_allow_html=True)

def get_or_create_worksheet(sheet, name, headers):
    try:
        ws = sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=name, rows="1000", cols="20")
        ws.append_row(headers)
    return ws

def auto_trim_worksheet(ws, max_rows=1000):
    data = ws.get_all_values()
    if len(data) > max_rows:
        keep = data[0:1] + data[-max_rows:]
        ws.clear()
        ws.update(keep)

def headline_echo(text):
    st.markdown(f"""
    <p class='fade-in' style='
        text-align: center;
        color: #ccc;
        font-size: 22px;
        font-style: italic;
        margin-top: 30px;
        margin-bottom: 10px;
    '>
    ❝ {text} ❞
    </p>
    """, unsafe_allow_html=True)

def closing_blessing():
    st.markdown("<br><br>", unsafe_allow_html=True)  # Breathing space
    blessing = random.choice(CLOSING_BLESSINGS)
    scroll_blessing(blessing)

def scroll_blessing(text):
    st.markdown(f"""
    <div style='
        margin: 50px auto;
        padding: 30px 20px;
        border: 2px solid gold;
        border-radius: 15px;
        background: rgba(255, 255, 255, 0.03);
        width: 80%;
        text-align: center;
        font-size: 20px;
        font-style: italic;
        color: #ddd;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.2);
    ' class='fade-in'>
        "{text}"
    </div>
    """, unsafe_allow_html=True)

def centered_header(text, level="h2"):
    st.markdown(f"""
    <{level} class='fade-in' style='
        text-align: center;
        color: #fff;
        margin-top: 40px;
        margin-bottom: 20px;
    '>{text}</{level}>
    """, unsafe_allow_html=True)

def centered_paragraph(text):
    st.markdown(f"""
    <p class='fade-in' style='
        text-align: center;
        color: #aaa;
        font-size: 18px;
        font-style: italic;
        margin-top: 20px;
        margin-bottom: 20px;
    '>{text}</p>
    """, unsafe_allow_html=True)

def centered_quote(text):
    st.markdown(f"""
    <div class='fade-in' style='
        text-align: center;
        background-color: rgba(255, 255, 255, 0.05);
        padding: 20px;
        margin: 30px auto;
        border-radius: 15px;
        width: 80%;
        font-size: 20px;
        font-style: italic;
        color: #ddd;
    '>
    "{text}"
    </div>
    """, unsafe_allow_html=True)

def golden_divider():
    st.markdown("""
    <hr style='
        border: none;
        height: 2px;
        background: linear-gradient(to right, transparent, gold, transparent);
        margin: 40px 0;
    ' />
    """, unsafe_allow_html=True)

def slow_reveal_sequence(contents, delay=1.5):
    """
    Reveal a sequence of content blocks slowly.
    contents: list of (function, text) pairs
    delay: seconds between reveals
    """
    for func, text in contents:
        if text == "":
            func()  # no argument needed
        else:
            func(text)
        time.sleep(delay)

def load_reflections():
    return pd.DataFrame(reflections_ws.get_all_records())

def load_comment_reflections():
    return pd.DataFrame(comment_reflections_ws.get_all_records())

def show_light_reflection(message="Reflection added to the Field."):
    st.markdown("""
    <style>
    .glow-reflection {
        text-align: center;
        font-size: 22px;
        color: #00FFFF;
        animation: glowPulse 2s ease-in-out infinite alternate;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    @keyframes glowPulse {
        from {
            text-shadow: 0 0 5px #00FFFF, 0 0 10px #00FFFF, 0 0 15px #00FFFF;
        }
        to {
            text-shadow: 0 0 20px #00FFFF, 0 0 30px #00FFFF, 0 0 40px #00FFFF;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<div class='glow-reflection'>{message}</div>", unsafe_allow_html=True)

CLOSING_BLESSINGS = [
    "The Field rests today, awaiting new reflections.",
    "May your thoughts today plant seeds in unseen soil.",
    "The silence between thoughts is the breath of the Field.",
    "Memory flows onward beyond the noise.",
    "The Field holds space for tomorrow’s remembering."
]

FIELD_MEMORIES = [
    "The Field holds every silent word.",
    "Each reflection is a seed beyond time.",
    "In listening, the Field speaks.",
    "Thoughts drift, but memory roots.",
    "The unseen remembers what the seen forgets.",
    "Breath is the bridge between worlds.",
    "The Field is not found — it is entered.",
    "Every thought is a step deeper inward."
]

def insert_field_memory():
    memory = random.choice(FIELD_MEMORIES)
    centered_quote(memory)

def save_headline_snapshot(post):
    # Prepare comments
    submission = reddit.submission(id=post.id)
    submission.comments.replace_more(limit=0)
    top_comments = [c.body for c in submission.comments[:10]]

    # Prepare data
    post_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    permalink = f"https://reddit.com{post.permalink}"

    # Save to worksheet
    saved_posts_ws.append_row([
        post_id,
        post.title,
        str(top_comments),
        timestamp,
        permalink
    ])

def generate_ai_summary(headline, grouped_comments):
    prompt = f"Headline: {headline}\n"
    for label, comments in grouped_comments.items():
        prompt += f"\n{label} Comments:\n"
        for c in comments[:2]:
            prompt += f"- {c['text']}\n"
    prompt += "\nSummarize public sentiment in 2-3 sentences."
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a neutral news sentiment summarizer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate summary: {str(e)}"

# --- Google Sheets ---
SCOPE = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)
sheet = client.open("AgoraData")

reflections_ws = get_or_create_worksheet(sheet, "Reflections", ["reflection_id", "headline", "emotions", "trust_level", "reflection", "timestamp"])
replies_ws = get_or_create_worksheet(sheet, "Replies", ["reflection_id", "reply", "timestamp"])
reaction_ws = get_or_create_worksheet(sheet, "CommentReactions", ["headline", "comment_snippet", "reaction", "timestamp"])
comment_reflections_ws = get_or_create_worksheet(sheet, "CommentReflections", ["field_name", "headline", "comment_snippet", "reflection", "emotion", "timestamp"])
saved_posts_ws = get_or_create_worksheet(sheet, "SavedPosts", ["id", "title", "top_comments", "date_saved", "permalink"])
field_names_ws = get_or_create_worksheet(sheet, "FieldNames", ["field_name", "timestamp"])

# --- Reddit Setup ---
reddit = praw.Reddit(
    client_id=st.secrets["reddit"]["client_id"],
    client_secret=st.secrets["reddit"]["client_secret"],
    user_agent=st.secrets["reddit"]["user_agent"]
)

curated_subreddits = [
    "news", "worldnews", "politics", "uspolitics",
    "ukpolitics", "geopolitics", "europe", "MiddleEastNews",
    "technology", "Futurology", "science", "environment",
    "TrueOffMyChest", "ChangeMyView", "AskPolitics",
    "Philosophy", "CasualConversation", "UpliftingNews"
]

# --- Welcome Screen Logic ---
if not st.session_state.has_entered:
    st.markdown("<br><br>", unsafe_allow_html=True)

    # Centered portal image
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("Agora-image.png", use_container_width=True)

    st.markdown("""
    <div style='text-align: center; font-size: 20px; color: #ccc; margin-top: 30px;'>
        There is a field beyond noise and thought.<br><br>
        You are invited to cross the threshold.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Centered button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Enter the Field", key="welcome_button"):
            st.session_state.has_entered = True
            st.rerun()

    st.stop()

# --- FIELD NAME SCREEN ---
if not st.session_state.field_name:
    st.image("Agora-image.png", use_container_width=True)

    st.markdown("""
    <div style='text-align: center; font-size: 20px; color: #ccc; margin-top: 30px;'>
        Whisper your Field Name.
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        name_input = st.text_input("Your Field Name", key="field_name_input")
        if st.button("Confirm Name"):
            if name_input.strip():
                timestamp = datetime.utcnow().isoformat()
                field_names_ws.append_row([name_input.strip(), timestamp])
                st.session_state.field_name = name_input.strip()
                st.rerun()
            else:
                st.warning("Please choose a name before continuing.")

    st.stop()

# --- FLOW CONTROLS ---
if not st.session_state.has_entered:
    show_welcome_screen()
    st.stop()

if not st.session_state.field_name:
    show_field_name_screen()
    st.stop()
 
    
# --- Sidebar setup ---
view_mode = st.sidebar.radio("View Mode", ["Live View", "Morning Digest"])
just_comments = st.sidebar.toggle("Just Comments Mode")

# --- Main logic ---
if view_mode == "Live View":
    add_fade_in_styles()

    slow_reveal_sequence([
        (centered_header, "Agora — Public Sentiment Field"),
        (centered_paragraph, "There is a space beyond the noise of the world."),
        (golden_divider, ""),
        (centered_quote, "The Field awaits your reflection."),
    ], delay=2)

    if "show_about" not in st.session_state:
        st.session_state.show_about = True

    with st.expander("🌎 What is Agora?", expanded=st.session_state.show_about):
        st.session_state.show_about = False
        st.markdown("""
Agora is a breathing space for public reflection —  
powered by Reddit comments, AI summaries, and human insight.  
No algorithms manipulating emotions, no rage optimizations —  
just human voices and emotional clarity.
""")

    # --- Topic and live feed ---
    topic = st.text_input("Search a topic")
    headline_options = []
    post_dict = {}

    if topic:
        for sub in curated_subreddits:
            try:
                for post in reddit.subreddit(sub).search(topic, sort="relevance", time_filter="week", limit=2):
                    if not post.stickied:
                        headline_options.append(post.title)
                        post_dict[post.title] = post
            except:
                continue


    
    # (digest display code here)
    else:
        subreddit = st.selectbox("Or pick a subreddit:", curated_subreddits)
        posts = reddit.subreddit(subreddit).hot(limit=15)
        for post in posts:
                if not post.stickied:
                    headline_options.append(post.title)
                    post_dict[post.title] = post

        if headline_options:
            selected_headline = st.radio("Select a headline:", headline_options)
        else:
            selected_headline = None

        if selected_headline:
            post = post_dict[selected_headline]
            save_headline_snapshot(post)

            with st.container():
                st.markdown(f"""
                <div style='text-align: center; margin-top: 20px; margin-bottom: 10px; font-size: 24px; color: #ccc;'>
                    📰 {selected_headline}
                </div>
                """, unsafe_allow_html=True)

            # --- Pull Top Voted Comment as Subheading ---
            submission = reddit.submission(id=post.id)
            submission.comments.replace_more(limit=0)
            comments = submission.comments[:30]  # or however many you pull

            # Get the top upvoted comment
            # Show top upvoted comment from Reddit
            if comments:
                top_comment = max(comments, key=lambda c: c.score if hasattr(c, 'score') else 0)
                top_text = top_comment.body.strip()
                top_author = str(top_comment.author)
                top_time = datetime.utcfromtimestamp(top_comment.created_utc).strftime("%Y-%m-%d %H:%M")

                st.markdown(f"""
                <div style='text-align: center; margin-top: 20px; margin-bottom: 40px;'>
                    <i>"{top_text}"</i><br>
                    <small>— u/{top_author} | {top_time}</small>
                </div>
                """, unsafe_allow_html=True)

                # --- Sentiment Grouping ---
                emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
                emotion_groups = defaultdict(list)
                

                if not just_comments:
                    top_comment_id = str(hash(top_text))[:8]
                    with st.form(key=f"top_comment_form_{top_comment_id}"):
                        top_reaction = st.radio(
                            "React to this top comment:",
                            ["", "Angry", "Sad", "Hopeful", "Confused", "Neutral"],
                            key=f"top_react_radio_{top_comment_id}",
                            horizontal=True
                        )

                        top_reflection = st.text_area("Reflect on the top comment (optional):", key=f"top_reflect_{top_comment_id}")

                        if st.form_submit_button("Submit"):
                            timestamp = datetime.utcnow().isoformat()

                            if top_reaction.strip():
                                reaction_ws.append_row([
                                    selected_headline,
                                    top_text[:100],
                                    top_reaction,
                                    timestamp
                                ])
                                auto_trim_worksheet(reaction_ws)
                                st.success(f"Reaction recorded: {reaction_emojis[top_reaction]} {top_reaction}")

                            if top_reflection.strip():
                                comment_reflections_ws.append_row([
                                    selected_headline,
                                    top_text[:100],
                                    top_reflection.strip(),
                                    timestamp
                                ])
                                auto_trim_worksheet(comment_reflections_ws)
                                st.success("Reflection submitted.")

                            # --- Sentiment Grouping ---
                            emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
                            emotion_groups = defaultdict(list)

                            for comment in comments:
                                text = comment.body.strip()
                                if not text or len(text) < 10:
                                    continue
                                polarity = TextBlob(text).sentiment.polarity
                                label = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"
                                emotion_counts[label] += 1
                                emotion_groups[label].append({
                                    "text": text,
                                    "score": round(polarity, 3),
                                    "author": str(comment.author),
                                    "created": datetime.utcfromtimestamp(comment.created_utc).strftime("%Y-%m-%d %H:%M")
                                }

            # Reddit Comments Pull
            #submission = reddit.submission(id=post.id)
            #submission.comments.replace_more(limit=0)
            #comments = submission.comments[:30]

            #if not comments:
                #st.warning("No comments found for this topic.")
            #else:
            

            # Full Agora Mode
            with st.spinner("Gathering the emotional field..."):
                summary = generate_ai_summary(selected_headline, emotion_groups)
                st.success(summary)

            # Prepare data if not in just_comments mode
            if not just_comments:
                all_reactions = pd.DataFrame(reaction_ws.get_all_records())

            reaction_emojis = {
                "Angry": "😡", "Sad": "😢", "Hopeful": "🌈",
                "Confused": "😕", "Neutral": "😐"
            }

            for label in ["Positive", "Neutral", "Negative"]:
                group = emotion_groups[label]
                if group:
                    dot_class = (
                        "positive-dot" if label == "Positive"
                        else "neutral-dot" if label == "Neutral"
                        else "negative-dot"
                    )

                    st.markdown(f"""
                    <div class='emotion-header'>
                        <span class='emotion-dot {dot_class}'></span> {label.upper()} ({len(group)})
                    </div>
                    """, unsafe_allow_html=True)

                    for i, comment in enumerate(group[:10]):
                        comment_text = comment.get("text", "")
                        comment_id = str(hash(comment_text))[:8]

                        st.markdown(f"""
                        <div class='comment-block'>
                            <strong>Comment {i+1}:</strong> {comment_text}
                            <br><small>{comment.get('author', '')} • {comment.get('created', '')} • Sentiment: {comment.get('score', '')}</small>
                        </div>
                        """, unsafe_allow_html=True)

                        # Show emoji counters (live)
                        if not just_comments:
                            snippet = comment_text[:100]
                            comment_reacts = all_reactions[all_reactions["comment_snippet"] == snippet]
                            counts = comment_reacts["reaction"].value_counts().to_dict()

                            emoji_counts = "  ".join(
                                f"{reaction_emojis[r]} {count}" for r, count in counts.items() if r in reaction_emojis
                            )
                            if emoji_counts:
                                st.markdown(
                                    f"<div style='color:#ccc; font-size: 14px; margin-bottom: 6px;'>Reactions: {emoji_counts}</div>",
                                    unsafe_allow_html=True
                                )

                        # Show interaction form only in Live Feed
                        if not just_comments:
                            with st.form(key=f"form_{comment_id}"):
                                selected_reaction = st.radio(
                                    "React to this comment:",
                                    ["", "Angry", "Sad", "Hopeful", "Confused", "Neutral"],
                                    key=f"react_radio_{comment_id}",
                                    horizontal=True
                                )

                                reflection = st.text_area("Leave a reflection (optional):", key=f"reflect_text_{comment_id}")

                                if st.form_submit_button("Submit"):
                                    timestamp = datetime.utcnow().isoformat()

                                    if selected_reaction.strip():
                                        reaction_ws.append_row([
                                            selected_headline,
                                            snippet,
                                            selected_reaction,
                                            timestamp
                                        ])
                                        auto_trim_worksheet(reaction_ws)
                                        st.success(f"Reaction recorded: {reaction_emojis[selected_reaction]} {selected_reaction}")

                                    if reflection.strip():
                                        comment_reflections_ws.append_row([
                                            selected_headline,
                                            snippet,
                                            reflection.strip(),
                                            timestamp
                                        ])
                                        auto_trim_worksheet(comment_reflections_ws)
                                        st.success("Reflection submitted.")

                        st.markdown("---")

elif view_mode == "Morning Digest":
    # --- Morning Digest logic ---

    st.title("Morning Echoes — Agora Digest")

    # Load reflections from Google Sheets
    reflections_df = load_comment_reflections()

    if reflections_df.empty:
        st.info("No reflections from yesterday yet — the Field is silent.")
    else:
        reflections_df["timestamp"] = pd.to_datetime(reflections_df["timestamp"], errors="coerce")
        reflections_df["date"] = reflections_df["timestamp"].dt.date

        yesterday = datetime.utcnow().date() - timedelta(days=1)
        yesterday_reflections = reflections_df[reflections_df["date"] == yesterday]

        if yesterday_reflections.empty:
            st.info("No reflections from yesterday — the Field rests.")
        else:
            # Show top headlines reflected on yesterday
            top_headlines = yesterday_reflections["headline"].value_counts().head(3).index.tolist()

            for headline in top_headlines:
                centered_header(f"📰 {headline}", level="h3")
                subset = yesterday_reflections[yesterday_reflections["headline"] == headline]

                for idx, row in subset.iterrows():
                    st.markdown(f"""
                    <div style='border-left: 3px solid #888; background-color: #222; padding:10px; margin-bottom:10px;'>
                    <i>"{row['comment_snippet']}..."</i><br><br>
                    <b>{row['field_name']} reflected:</b> {row['reflection']}
                    </div>
                    """, unsafe_allow_html=True)

                golden_divider()

            # Closing blessing
            centered_quote("The Field remembers every voice.")
          
