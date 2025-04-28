
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

# --- Reddit Setup ---
reddit = praw.Reddit(
    client_id=st.secrets["reddit"]["client_id"],
    client_secret=st.secrets["reddit"]["client_secret"],
    user_agent=st.secrets["reddit"]["user_agent"]
)

curated_subreddits = ["news", "worldnews", "politics", "uspolitics", "technology", "science", "geopolitics"]

# --- Welcome Screen Logic ---
if "has_entered" not in st.session_state:
    st.session_state.has_entered = False

# --- Welcome Page ---
if not st.session_state.has_entered:
    add_fade_in_styles()
    add_button_glow()

    placeholder = st.empty()
    with placeholder.container():
        banner = Image.open("Agora-image.png")
        st.image(banner, use_container_width=True)

    st.markdown("""
    <p class='fade-in' style='font-size:18px; color: #bbb; text-align: center;'>
    There is a field beyond noise.<br><br>
    You have arrived.
    </p>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        # Centered custom portal button
        if st.button("Enter the Field", key="main_enter"):
            st.session_state.has_entered = True
            st.rerun()

    # Center ALL Streamlit buttons to be centered inside columns
    st.markdown("""
    <style>
    div.stButton > button {
        display: block;
        margin: 0 auto;
    }
    </style>
    """, unsafe_allow_html=True)


    # --- Light Field Name Selection ---
    if "field_name" not in st.session_state:
        st.session_state.field_name = ""

    if st.session_state.field_name == "":
        st.subheader("Whisper your Field Name")

        chosen_name = st.text_input("Choose a name that feels right for the Field (e.g., SkySeeker, LightWanderer)")

        if st.button("Confirm Name"):
            if chosen_name.strip():
                st.session_state.field_name = chosen_name.strip()
                st.success(f"Welcome, {st.session_state.field_name}. You are now part of the Field.")
                st.rerun()

else:

    add_fade_in_styles()

    slow_reveal_sequence([
        (centered_header, "Agora — Public Sentiment Field"),
        (centered_paragraph, "There is a space beyond the noise of the world."),
        (golden_divider, ""),  # Divider doesn't need text
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

    view_mode = st.sidebar.radio("View Mode", ["Live Field", "Morning Digest"])
    just_comments = st.sidebar.toggle("Just Comments Mode")

    if view_mode == "Live Field":
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
            if comments:
                top_comment = max(comments, key=lambda c: c.score if hasattr(c, 'score') else 0)

                st.markdown(f"""
                <div style='text-align: center; margin-top: 10px; margin-bottom: 30px;'>
                    <i>"{top_comment.body.strip()}"</i><br>
                    <small>— u/{top_comment.author} | {datetime.utcfromtimestamp(top_comment.created_utc).strftime("%Y-%m-%d %H:%M")}</small>
                </div>
                """, unsafe_allow_html=True)

            emotions = ["Angry", "Hopeful", "Skeptical", "Confused", "Inspired", "Indifferent"]
            emotion_choice = st.multiselect("What emotions do you feel?", emotions, key="emotion_choice")
            trust_rating = st.slider("How much do you trust this headline?", 1, 5, 3, key="trust_rating")
            user_thoughts = st.text_area("Write your immediate reflection...", key="user_thoughts")

            if st.button("Submit Reflection"):
                if user_thoughts.strip():
                    reflection_id = str(uuid.uuid4())
                    timestamp = datetime.utcnow().isoformat()
                    reflections_ws.append_row([
                        reflection_id,
                        selected_headline,
                        ", ".join(emotion_choice),
                        trust_rating,
                        user_thoughts,
                        timestamp
                    ])
                    auto_trim_worksheet(reflections_ws)
                    show_light_reflection("Your reflection breathes into the Field.")
                    st.rerun()

            # Reddit Comments Pull
            submission = reddit.submission(id=post.id)
            submission.comments.replace_more(limit=0)
            comments = submission.comments[:30]

            if not comments:
                st.warning("No comments found for this topic.")
            else:
                # (Same comments logic we built together — will continue after this!)
                emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
                emotion_groups = defaultdict(list)
                emotion_choice = st.selectbox(
                "What emotion best captures your feeling toward this comment?",
                ["", "Hope", "Anger", "Confusion", "Inspiration", "Sadness", "Skepticism", "Indifference"]
            )

                for comment in comments:
                    comment_text = comment.body.strip() 
                    text = comment.body.strip()
                    if len(text) < 10:
                        continue
                    polarity = TextBlob(text).sentiment.polarity
                    label = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"
                    emotion_counts[label] += 1
                    emotion_groups[label].append({
                        "text": text,
                        "score": round(polarity, 3),
                        "author": str(comment.author),
                        "created": datetime.utcfromtimestamp(comment.created_utc).strftime("%Y-%m-%d %H:%M")
                    })

                if just_comments:
                    st.write(f"Showing {len(comments)} comments...")
                    for label in ["Positive", "Neutral", "Negative"]:
                        group = emotion_groups[label]
                        if group:
                            st.markdown(f"""
                            <div class='emotion-header'>
                                <span class='emotion-dot {label.lower()}-dot'></span> {label} ({emotion_counts[label]})
                            </div>
                            """, unsafe_allow_html=True)
                            for i, comment in enumerate(group[:10]):
                                st.markdown(f"""
                                <div class='comment-block'>
                                    <strong>Comment {i+1}:</strong> {comment['text']}
                                    <br><small>{comment['author']} • {comment['created']} • Sentiment: {comment['score']}</small>
                                </div>
                                """, unsafe_allow_html=True)
                else:
                    # Full Agora Mode
                    with st.spinner("Gathering the emotional field..."):
                        summary = generate_ai_summary(selected_headline, emotion_groups)
                        st.success(summary)

                    for label in ["Positive", "Neutral", "Negative"]:
                        group = emotion_groups[label]
                        if group:
                            st.markdown(f"""
                            <div class='emotion-header'>
                                <span class='emotion-dot {label.lower()}-dot'></span> {label} ({emotion_counts[label]})
                            </div>
                            """, unsafe_allow_html=True)
                            for i, comment in enumerate(group[:10]):
                                comment_id = str(hash(comment["text"]))[:8]
                                st.markdown(f"""
                                <div class='comment-block'>
                                    <strong>Comment {i+1}:</strong> {comment['text']}
                                    <br><small>{comment['author']} • {comment['created']} • Sentiment: {comment['score']}</small>
                                </div>
                                """, unsafe_allow_html=True)

                                reaction = st.radio(
                                    "React to this comment:",
                                    ["", "Angry", "Sad", "Hopeful", "Confused", "Neutral"],
                                    key=f"reaction_{comment_id}",
                                    horizontal=True
                                )
                                if reaction.strip():
                                    reaction_ws.append_row([
                                        selected_headline,
                                        comment["text"][:100],
                                        reaction,
                                        datetime.utcnow().isoformat()
                                    ])
                                    auto_trim_worksheet(reaction_ws)

                                with st.form(key=f"form_reflection_{comment_id}"):
                                    user_reflection = st.text_input("Your reflection on this comment:")
                                    emotion_choice = st.selectbox(
                                        "What emotion best captures your feeling toward this comment?",
                                        ["", "Hope", "Anger", "Confusion", "Inspiration", "Sadness", "Skepticism", "Indifference"]
                                    )
                                    if st.form_submit_button("Submit Reflection") and user_reflection.strip():
                                        comment_snippet = comment_text[:100] 
                                        comment_reflections_ws.append_row([
                                            st.session_state.field_name,
                                            selected_headline,
                                            comment_snippet,  # the short comment excerpt
                                            user_reflection.strip(),
                                            datetime.utcnow().isoformat()
                                        ])
                                        auto_trim_worksheet(comment_reflections_ws)
                                        show_light_reflection("Your reflection breathes into the Field.")
                                        st.rerun()

            # --- Sentiment Field Visualization ---
            centered_header("Sentiment Field — Emotional Landscape")

            all_comment_reflections = load_comment_reflections()

            if not all_comment_reflections.empty:
                all_comment_reflections["timestamp"] = pd.to_datetime(all_comment_reflections["timestamp"], errors="coerce")
                all_comment_reflections["primary_emotion"] = all_comment_reflections["emotions"].apply(lambda x: x.split(",")[0].strip() if pd.notnull(x) else "Neutral")
    
                fig = px.scatter(
                    all_comment_reflections,
                    x="trust_level",
                    y="primary_emotion",
                    color="primary_emotion",
                    hover_data=["reflection", "timestamp"],
                    size_max=60,
                    title="Agora Sentiment Field"
                )
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No reflections to plot yet.")

    # --- Morning Digest Mode ---
    elif view_mode == "Morning Digest":
        add_fade_in_styles()

        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        reflections_df = pd.DataFrame(reflections_ws.get_all_records())
        reflections_df["timestamp"] = pd.to_datetime(reflections_df["timestamp"], errors="coerce")
        reflections_df["date"] = reflections_df["timestamp"].dt.date

        yesterday_data = reflections_df[reflections_df["date"] == yesterday]

        if yesterday_data.empty:
            slow_reveal_sequence([
                (centered_header, "Agora Morning Digest"),
                (centered_paragraph, "No reflections were recorded yesterday. The Field was silent."),
            ], delay=1.5)
        else:
            slow_reveal_sequence([
                (centered_header, "Agora Morning Digest"),
                (centered_paragraph, "Glimpses into the Field from yesterday's thoughts."),
            ], delay=1.5)

            top_headlines = yesterday_data["headline"].value_counts().head(3).index.tolist()

            for headline in top_headlines:
                golden_divider()

                slow_reveal_sequence([
                    (headline_echo, headline),
                    (centered_paragraph, "Gathering reflections...")
                ], delay=1.5)

                subset = yesterday_data[yesterday_data["headline"] == headline]
                grouped = {"Reflections": [{"text": r} for r in subset["reflection"].tolist()]}

                with st.spinner("Summarizing reflections..."):
                    summary = generate_ai_summary(headline, grouped)

                time.sleep(1.0)  # gentle pause
                centered_quote(summary)

                time.sleep(1.5)  # breathing space
                insert_field_memory()

                st.markdown("<br><br>", unsafe_allow_html=True)

            closing_blessing()
          
