
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
feedback_ws = get_or_create_worksheet(sheet, "AI_Feedback", ["Headline", "Question", "AI Response", "Feedback", "Comment", "Timestamp"])


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
view_mode = st.sidebar.radio("View Mode", ["Live View", "Morning Digest", "Ask Agora"])
just_comments = st.sidebar.toggle("Just Comments Mode")

# --- Main logic ---
if view_mode == "Live View":
    add_fade_in_styles()

    reaction_emojis = {
    "Angry": "😡",
    "Sad": "😢",
    "Hopeful": "🌈",
    "Confused": "😕",
    "Neutral": "😐"
}

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
    # --- Topic Search ---
    st.subheader("Search a topic")
    topic = st.text_input("Enter a topic to explore:")

    headline_options = []
    post_dict = {}

    curated_subreddits = [
        "news", "worldnews", "politics", "uspolitics", "geopolitics",
        "MiddleEastNews", "GlobalNews", "TrueReddit", "technology", "science"
    ]

    if topic:
        for sub in curated_subreddits:
            try:
                for post in reddit.subreddit(sub).search(topic, sort="relevance", time_filter="week", limit=3):
                    if not post.stickied and post.title not in post_dict:
                        headline_options.append(post.title)
                        post_dict[post.title] = post
            except 
                
                continue
    elif manual_subreddit:
        try:
            for post in reddit.subreddit(manual_subreddit).hot(limit=15):
                if not post.stickied and post.title not in post_dict:
                    headline_options.append(post.title)
                    post_dict[post.title] = post
        except:
            pass

    if headline_options:
        selected_headline = st.radio("Select a headline:", headline_options)
    else:
        st.info("No headlines found. Try a different topic or subreddit.")
        selected_headline = None

            if selected_headline:
                post = post_dict[selected_headline]  # Get the corresponding Reddit post object
                submission = reddit.submission(id=post.id)
                submission.comments.replace_more(limit=0)
                comments = submission.comments[:30]

                st.markdown(f"### 📰 {selected_headline}")
                st.write(f"Number of comments fetched: {len(comments)}")

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

                    # Example: Display rest of the comments
                    for i, comment in enumerate(comments[:10]):
                        st.markdown(f"**Comment {i+1}**: {comment.body}")

                else:
                    st.warning("No comments found for this topic.")
        else:
            st.info("No relevant headlines found for this topic. Try a different search term.")

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

                submission = reddit.submission(id=post.id)
                submission.comments.replace_more(limit=0)
                comments = submission.comments[:30] 

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
                    })
            

            # Full Agora Mode
            # --- Full Agora Mode ---
            if not just_comments:
                with st.spinner("Gathering the emotional field..."):
                    summary = generate_ai_summary(selected_headline, emotion_groups)
                    st.success(summary)

            submission = reddit.submission(id=post.id)
            submission.comments.replace_more(limit=0)
            comments = submission.comments[:30] 

            # Load all reactions once
            all_reactions = pd.DataFrame(reaction_ws.get_all_records())
            

            # Display grouped comments
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

                        # Display comment block
                        st.markdown(f"""
                        <div class='comment-block'>
                            <strong>Comment {i+1}:</strong> {comment_text}
                            <br><small>{comment.get('author', '')} • {comment.get('created', '')} • Sentiment: {comment.get('score', '')}</small>
                        </div>
                        """, unsafe_allow_html=True)

                        # --- Live emoji reaction counters ---
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

                        # --- Optional reflection + reaction form ---
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

    from datetime import datetime, timedelta

    st.title("Morning Echoes — Agora Digest")
    add_fade_in_styles()

    # Load reflection data
    reflections_df = pd.DataFrame(reflections_ws.get_all_records())

    # Convert timestamps and filter for yesterday
    reflections_df["timestamp"] = pd.to_datetime(reflections_df["timestamp"], errors="coerce")
    reflections_df["date"] = reflections_df["timestamp"].dt.date

    yesterday = datetime.utcnow().date() - timedelta(days=1)
    yesterday_data = reflections_df[reflections_df["date"] == yesterday]

    if yesterday_data.empty:
        st.info("No reflections from yesterday — the Field rests.")
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
                try:
                    summary = generate_ai_summary(headline, grouped)
                except Exception as e:
                    summary = f"Error generating summary: {str(e)}"

            time.sleep(1)
            centered_quote(summary)
            time.sleep(1.5)
            insert_field_memory()
            st.markdown("<br><br>", unsafe_allow_html=True)

        closing_blessing()

elif view_mode == "Ask Agora":
    st.markdown("## Ask Agora: Conversational Assistant")
    st.markdown("Reflect on any headline and the public sentiment around it.")

    if "post_dict" not in st.session_state or not st.session_state.post_dict:
        st.warning("No headlines loaded. Please visit Agora Mode first.")
    else:
        post_dict = st.session_state.post_dict
        headlines = list(post_dict.keys())

        if not headlines:
            st.warning("No headlines found. Try browsing a subreddit first.")
        else:
            selected_title = st.selectbox("Choose a headline to explore:", headlines)
            selected_post = post_dict[selected_title]

            submission = reddit.submission(id=selected_post.id)
            submission.comments.replace_more(limit=0)
            top_comments = sorted(submission.comments.list(), key=lambda c: getattr(c, 'score', 0), reverse=True)
            top_comments = [c for c in top_comments if len(c.body.strip()) > 10][:10]

            grouped = {"Positive": [], "Neutral": [], "Negative": []}
            for comment in top_comments:
                text = comment.body.strip()[:200]
                polarity = TextBlob(text).sentiment.polarity
                label = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"
                grouped[label].append(f'"{text}"')

            grouped_summary = ""
            for label in ["Positive", "Neutral", "Negative"]:
                if grouped[label]:
                    grouped_summary += f"{label} Comments:\n" + "\n".join(grouped[label]) + "\n\n"

            try:
                sentiment_summary = generate_ai_summary(selected_title, emotion_groups)
            except:
                sentiment_summary = "Sentiment data is not yet available."

            st.markdown("### Ask a question about this headline")
            suggested_questions = [
                "What emotions are people expressing here?",
                "Why might this topic be so divisive?",
                "What do these comments reveal about public opinion?",
                "What might a constructive next step look like?",
                "How could someone respond to this sentiment thoughtfully?",
                "What deeper issue is this headline tapping into?",
                "What are the risks of ignoring this perspective?"
            ]

            selected_prompt = st.radio("Choose a suggested question (optional):", [""] + suggested_questions)
            user_question = st.chat_input("Or ask your own question here")

            if not user_question and selected_prompt:
                user_question = selected_prompt

            if user_question:
                st.chat_message("user").write(user_question)

                prompt = f"""Headline: "{selected_title}"

Grouped Reddit comment sentiment:
{grouped_summary}

AI summary of public sentiment:
{sentiment_summary}

The user asks: "{user_question}"

Answer as a thoughtful assistant helping the user understand the range of emotional responses and what they might reveal about deeper public concerns.
"""

                try:
                    openai_client = OpenAI(api_key=st.secrets["openai"]["api_key"])
                    response = openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    reply = response.choices[0].message.content
                except Exception as e:
                    reply = (
                        "The AI assistant is currently unavailable. "
                        "Please check your OpenAI API key or billing status."
                    )
                    st.error(str(e))

                st.chat_message("assistant").write(reply)

                with st.form(key="ai_feedback_form"):
                    st.markdown("**Do you agree with the assistant's summary?**")
                    feedback = st.radio("Your response:", ["", "Agree", "Disagree", "Partially Agree"])
                    comments = st.text_area("Optional: Tell us why or add your own insights")

                    if st.form_submit_button("Submit Feedback"):
                        timestamp = datetime.utcnow().isoformat()
                        feedback_ws.append_row([
                            selected_title, user_question, reply, feedback, comments, timestamp
                        ])
                        auto_trim_worksheet(feedback_ws)
                        st.success("Thanks for your feedback!")

        

elif view_mode == "Ask Agora":
    st.markdown("## Ask Agora: Conversational Assistant")
    st.markdown("Reflect on any headline and the public sentiment around it.")

    if "post_dict" not in st.session_state or not st.session_state.post_dict:
        st.warning("No headlines loaded. Please visit Agora Mode first.")
    else:
        post_dict = st.session_state.post_dict
        headlines = list(post_dict.keys())

        if not headlines:
            st.warning("No headlines found. Try browsing a subreddit first.")
        else:
            selected_title = st.selectbox("Choose a headline to explore:", headlines)
            selected_post = post_dict[selected_title]

            submission = reddit.submission(id=selected_post.id)
            submission.comments.replace_more(limit=0)
            top_comments = sorted(submission.comments.list(), key=lambda c: getattr(c, 'score', 0), reverse=True)
            top_comments = [c for c in top_comments if len(c.body.strip()) > 10][:10]

            comment_summary = ""
            for i, comment in enumerate(top_comments, 1):
                polarity = TextBlob(comment.body).sentiment.polarity
                label = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"
                comment_summary += f"{i}. \"{comment.body.strip()[:200]}\" ({label})\n"

            try:
                sentiment_summary = generate_ai_summary(selected_title, emotion_groups)
            except:
                sentiment_summary = "Sentiment data is not yet available."

            # Suggested + custom question input
            st.markdown("### Ask a question about this headline")
            suggested_questions = [
                "What emotions are people expressing here?",
                "Why might this topic be so divisive?",
                "What do these comments reveal about public opinion?",
                "What might a constructive next step look like?",
                "How could someone respond to this sentiment thoughtfully?",
                "What deeper issue is this headline tapping into?",
                "What are the risks of ignoring this perspective?"
            ]

            selected_prompt = st.radio("Choose a suggested question (optional):", [""] + suggested_questions)
            user_question = st.chat_input("Or ask your own question here")

            if not user_question and selected_prompt:
                user_question = selected_prompt

            if user_question:
                st.chat_message("user").write(user_question)

                prompt = f"""Headline: "{selected_title}"

Summary of top 5 Reddit comments:
{comment_summary}

AI summary of public sentiment:
{sentiment_summary}

The user asks: "{user_question}"

Answer as a thoughtful assistant helping the user understand online sentiment and its possible meaning.
"""

                try:
                    openai_client = OpenAI(api_key=st.secrets["openai"]["api_key"])
                    response = openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    reply = response.choices[0].message.content
                except Exception as e:
                    reply = (
                        "The AI assistant is currently unavailable. "
                        "Please check your OpenAI API key or billing status."
                    )
                    st.error(str(e))

                st.chat_message("assistant").write(reply)





        



        
        









          
