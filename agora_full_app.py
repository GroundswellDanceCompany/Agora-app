import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import praw
from openai import OpenAI
from textblob import TextBlob
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import random
import time
import plotly.express as px
from PIL import Image

# ----------------------
# --- Helper Functions ---
# ----------------------

def get_or_create_worksheet(sheet, name, headers):
    try:
        ws = sheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=name, rows="1000", cols="20")
        ws.append_row(headers)
    return ws

def auto_trim_worksheet(ws, max_rows=1000):
    data = ws.get_all_values()
    num_rows = len(data)
    if num_rows > max_rows:
        # Keep headers + last max_rows rows
        rows_to_keep = data[0:1] + data[-max_rows:]
        ws.clear()
        ws.update(rows_to_keep)

# --- Data Loading ---
def load_reflections():
    return pd.DataFrame(reflections_ws.get_all_records())

def load_replies():
    return pd.DataFrame(replies_ws.get_all_records())

# --- AI and Summaries ---
def generate_ai_summary(headline, grouped_comments):
    prompt = f"Headline: {headline}\n"
    for label, comments in grouped_comments.items():
        prompt += f"\n{label} Comments:\n"
        for c in comments[:2]:
            prompt += f"- {c['text']}\n"
    prompt += "\nSummarize public sentiment in 2-3 sentences. Be neutral and insightful."
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a news analyst summarizing emotional sentiment."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "**Summary unavailable. The field waits.**"

# --- Emotional Intelligence ---
def detect_collective_mood():
    reflections_df = load_reflections()
    if reflections_df.empty:
        return "Silent"

    reflections_df["timestamp"] = pd.to_datetime(reflections_df["timestamp"], errors="coerce")
    reflections_df = reflections_df.dropna(subset=["timestamp"])
    reflections_df["date"] = reflections_df["timestamp"].dt.date

    today = datetime.utcnow().date()
    today_reflections = reflections_df[reflections_df["date"] == today]

    if today_reflections.empty:
        return "Silent"

    mood_counter = {
        "Hopeful": 0,
        "Angry": 0,
        "Confused": 0,
        "Skeptical": 0,
        "Inspired": 0,
        "Indifferent": 0
    }

    for emotions in today_reflections["emotions"]:
        if pd.isnull(emotions):
            continue
        for mood in mood_counter:
            if mood in emotions:
                mood_counter[mood] += 1

    if max(mood_counter.values()) == 0:
        return "Silent"

    return max(mood_counter, key=mood_counter.get)

# --- Visual & UX ---
def add_button_glow():
    st.markdown("""
    <style>
    div.stButton > button {
        background-color: #222;
        color: #fff;
        border-radius: 8px;
        padding: 0.5em 2em;
        transition: box-shadow 0.5s, background-color 0.5s;
        border: 1px solid #555;
    }
    div.stButton > button:hover {
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
        background-color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

def add_fade_in_styles():
    st.markdown("""
    <style>
    @keyframes fadeInSlow {
        0% {opacity: 0;}
        100% {opacity: 1;}
    }
    .fade-in {
        animation: fadeInSlow 2s ease-in forwards;
    }
    img {
        animation: fadeInSlow 2.5s ease-in forwards;
    }
    div[data-testid="stPlotlyChart"] {
        animation: fadeInSlow 2s ease-in forwards;
    }
    </style>
    """, unsafe_allow_html=True)

def add_custom_loader():
    st.markdown("""
    <style>
    .listening {
      font-size: 20px;
      color: #aaa;
      text-align: center;
      margin-top: 50px;
      animation: pulseDots 2s infinite;
    }
    @keyframes pulseDots {
      0% { opacity: 0.2; }
      50% { opacity: 1; }
      100% { opacity: 0.2; }
    }
    </style>
    """, unsafe_allow_html=True)

def centered_header(text, level="h2"):
    st.markdown(f"<{level} style='text-align: center; color: #fff;'>{text}</{level}>", unsafe_allow_html=True)

def show_inspirational_whisper():
    quotes = [
        "“The pulse of humanity can be felt if you listen softly.”",
        "“Beyond headlines, there are heartbeats.”",
        "“Every thought leaves a trace on the collective field.”",
        "“Hope hums quietly beneath the noise.”",
        "“Emotion is the language of the field.”",
        "“The field remembers what we dare to feel.”",
    ]
    whisper = random.choice(quotes)
    st.markdown(f"<p style='font-style: italic; color: #bbb; text-align: center;'>{whisper}</p>", unsafe_allow_html=True)

# ----------------------
# --- App Start ---
# ----------------------

st.set_page_config(
    page_title="Agora — Public Sentiment Field",
    page_icon=":crystal_ball:",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Custom CSS (all combined here) ---
st.markdown("""
<style>
.comment-block {
  border-left: 4px solid #00FFFF;
  background-color: #222;
  color: white;
  padding: 10px;
  margin-bottom: 10px;
  transition: all 0.3s ease;
}

.comment-block:hover {
  background-color: #333;
  box-shadow: 0 0 10px rgba(0,255,255,0.4);
}

.emotion-header {
    text-align: center;
    font-size: 22px;
    font-weight: 400;
    color: #ccc;
    margin-top: 30px;
    margin-bottom: 10px;
}

.emotion-dot {
    height: 14px;
    width: 14px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 8px;
}

.positive-dot { background-color: #32CD32; }
.neutral-dot { background-color: #AAAAAA; }
.negative-dot { background-color: #FF6347; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.fade-in {
  opacity: 0;
  animation: fadeInAnimation ease 1s;
  animation-fill-mode: forwards;
  animation-delay: 0.2s;
}

@keyframes fadeInAnimation {
  0% { opacity: 0; }
  100% { opacity: 1; }
}
</style>
""", unsafe_allow_html=True)

# --- Setup Services ---
SCOPE = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)
sheet = client.open("AgoraData")
reflections_ws = get_or_create_worksheet(sheet, "Reflections", ["reflection_id", "headline", "emotions", "trust_level", "reflection", "timestamp"])
replies_ws = get_or_create_worksheet(sheet, "Replies", ["reflection_id", "reply", "timestamp"])
reaction_ws = get_or_create_worksheet(sheet, "CommentReactions", ["headline", "comment_snippet", "reaction", "timestamp"])
comment_reflections_ws = get_or_create_worksheet(sheet, "CommentReflections", ["headline", "comment_snippet", "reflection", "timestamp"])

reddit = praw.Reddit(
    client_id=st.secrets["reddit"]["client_id"],
    client_secret=st.secrets["reddit"]["client_secret"],
    user_agent=st.secrets["reddit"]["user_agent"]
)

# --- Session State for Welcome Page ---
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

    if st.button("Enter the Field"):
        st.session_state.has_entered = True
        st.rerun()

    st.stop()

# --- Live Agora ---
add_fade_in_styles()

centered_header("Agora — The Collective Pulse", level="h1")

# Emotional Weather Badge
mood_today = detect_collective_mood()
mood_colors = {
    "Hopeful": "#7CFC00",
    "Angry": "#FF4500",
    "Confused": "#9370DB",
    "Skeptical": "#D3D3D3",
    "Inspired": "#00CED1",
    "Indifferent": "#A9A9A9",
    "Silent": "#555555"
}
badge_color = mood_colors.get(mood_today, "#555555")

st.markdown(f"""
<div style='background-color: {badge_color};
    padding: 8px 20px;
    border-radius: 30px;
    text-align: center;
    font-size: 18px;
    color: black;
    width: fit-content;
    margin: auto;
    margin-bottom: 20px;'>
Today’s Emotional Weather: {mood_today}
</div>
""", unsafe_allow_html=True)

# --- UI Choices ---
just_comments = st.toggle("I'm just here for the comments")
view_mode = st.sidebar.radio("View Mode", ["Live View", "Morning Digest"])

if view_mode == "Live View":
    curated_subreddits = ["news", "worldnews", "politics", "uspolitics", "ukpolitics", "europe", "MiddleEastNews", "technology", "Futurology", "science", "space", "environment", "geopolitics", "AutoNews"]

    topic = st.text_input("Enter a topic to listen across curated subreddits")
    headline_options, post_dict = [], {}

    if topic:
        for sub in curated_subreddits:
            try:
                for post in reddit.subreddit(sub).search(topic, sort="relevance", time_filter="week", limit=2):
                    if not post.stickied:
                        headline_options.append(post.title)
                        post_dict[post.title] = post
            except:
                continue
        page_size = 5
        total_pages = len(headline_options) // page_size + int(len(headline_options) % page_size > 0)
        page = st.number_input("Page", min_value=1, max_value=total_pages, step=1) if total_pages > 1 else 1
        start, end = (page - 1) * page_size, page * page_size
        paged_headlines = headline_options[start:end]
        selected_headline = st.radio("Select a headline to reflect on:", paged_headlines)
    else:
        selected_headline = None

    if selected_headline:
    post = post_dict[selected_headline]

    # --- Headline and Immediate Reflection (your nice container) ---
    with st.container():
        st.markdown(f"""<div class='fade-in'>
            <div style='text-align: center; font-size: 26px; font-weight: 400; color: #ccc; margin-top: 20px; margin-bottom: 30px;'>
                📰 {selected_headline}
            </div>
            <div style='text-align: center; margin-bottom: 40px;'>
                <h3 style='color: #aaa;'>Your Immediate Reflection</h3>
            </div>
        </div>""", unsafe_allow_html=True)

        # --- Reflection form ---
        emotions = ["Angry", "Hopeful", "Skeptical", "Confused", "Inspired", "Indifferent"]

        emotion_choice = st.multiselect(
            "What emotions do you feel?", emotions, key="emotion_choice"
        )
        trust_rating = st.slider(
            "How much do you trust this headline?", 1, 5, 3, key="trust_rating"
        )
        user_thoughts = st.text_area(
            "Write your immediate reflection...", key="user_thoughts"
        )

        if st.button("Submit Reflection"):
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
            st.success("Reflection submitted!")
            # --- Clear form fields ---
            st.session_state["emotion_choice"] = []
            st.session_state["trust_rating"] = 3
            st.session_state["user_thoughts"] = ""

    # --- NOW (still inside if selected_headline) ---
    submission = reddit.submission(id=post.id)
    submission.comments.replace_more(limit=0)
    comments = submission.comments[:30]

    # (then you go on with comments, reactions, public reflections, field...)

else:
    st.warning("Please select a headline first.")

        emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
        emotion_groups = defaultdict(list)

        for comment in comments:
            text = comment.body.strip()
            if len(text) < 10:
                continue
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
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
                icon, color = emoji_map[label]
                centered_header(f"{icon} {label} ({emotion_counts[label]})", level="h2")
                group = emotion_groups[label]
                if group:
                    for i, comment in enumerate(group[:10]):
                        st.markdown(f"""
                        <div style='border-left: 4px solid {color}; background-color:#222; color:white; padding:10px; margin-bottom:10px;'>
                            <strong>Comment {i+1}:</strong> {comment['text']}
                            <br><small>{comment['author']} • {comment['created']} • Sentiment: {comment['score']}</small>
                        </div>""", unsafe_allow_html=True)
        else:
    # full agora: summary, reactions, reflection writing, sentiment field
            if not just_comments:
                with st.spinner("Gathering the field..."):
                    summary = generate_ai_summary(selected_headline, emotion_groups)
                    st.success(summary)

        for label in ["Positive", "Neutral", "Negative"]:
            group = emotion_groups[label]
            if group:
                # -- NEW HEADER --
                if label == "Positive":
                    dot_class = "positive-dot"
                elif label == "Neutral":
                    dot_class = "neutral-dot"
                else:
                    dot_class = "negative-dot"

                st.markdown(f"""
                <div class='emotion-header'>
                    <span class='emotion-dot {dot_class}'></span> {label} ({emotion_counts[label]})
                </div>
                """, unsafe_allow_html=True)

        # Then display comments for that group
        
            # (Display comment block, reactions, reflections...)
                for i, comment in enumerate(group[:10]):
    # 1. Display the comment block
                    st.markdown(f"""
                    <div class='comment-block'>
                        <strong>Comment {i+1}:</strong> {comment['text']}
                        <br><small>{comment['author']} • {comment['created']} • Sentiment: {comment['score']}</small>
                    </div>
                    """, unsafe_allow_html=True)

                    comment_id = str(hash(comment["text"]))[:8]  # unique per comment

                    # 2. Reaction Radio Buttons
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

                     # 3. Reflection Form
                    with st.form(key=f"form_reflection_{comment_id}"):
                        user_reflection = st.text_input("Your reflection on this comment:")
                        if st.form_submit_button("Submit Reflection") and user_reflection.strip():
                            comment_reflections_ws.append_row([
                                selected_headline,
                                comment["text"][:100],  # first 100 chars of the comment
                                user_reflection.strip(),
                                datetime.utcnow().isoformat()
                            ])
                            auto_trim_worksheet(comment_reflections_ws)
                            st.success("Reflection added!")

        

        # Reflections
        centered_header("Public Reflections", level="h2")
        all_reflections = load_reflections()
        all_replies = load_replies()
        matched = all_reflections[all_reflections["headline"] == selected_headline]
        if matched.empty:
            st.info("No reflections yet.")
        else:
            for _, row in matched.iterrows():
                st.markdown(f"**Emotions:** {row['emotions']}")
                st.markdown(f"**Trust:** {row['trust_level']}/5")
                st.markdown(f"**Reflection:** {row['reflection']}")
                st.caption(f"{row['timestamp']}")
                if "reflection_id" in all_replies.columns:
                    replies = all_replies[all_replies["reflection_id"] == row["reflection_id"]]
                    for _, reply in replies.iterrows():
                        st.markdown(f"↳ _{reply.get('reply', '')}_ — {reply.get('timestamp', '')}")
                with st.form(key=f"reply_form_{row['reflection_id']}"):
                    reply_text = st.text_input("Reply to this reflection:", key=f"r_{row['reflection_id']}")
                    if st.form_submit_button("Submit Reply") and reply_text.strip():
                        replies_ws.append_row([row["reflection_id"], reply_text.strip(), datetime.utcnow().isoformat()])
                        auto_trim_worksheet(replies_ws)
                        st.success("Reply added.")

        # Sentiment Field
        centered_header("Sentiment Field — Emotional Landscape", level="h2")
        reflection_data = load_reflections()
        if not reflection_data.empty:
            reflection_data["timestamp"] = pd.to_datetime(reflection_data["timestamp"], errors="coerce")
            reflection_data["primary_emotion"] = reflection_data["emotions"].apply(lambda x: x.split(",")[0].strip() if pd.notnull(x) else "Neutral")
            fig = px.scatter(
                reflection_data,
                x="trust_level",
                y="primary_emotion",
                color="primary_emotion",
                hover_data=["reflection", "timestamp"],
                size_max=60,
                title="Agora Sentiment Field",
                labels={"trust_level": "Trust (1 = Distrust, 5 = High Trust)", "primary_emotion": "Primary Emotion"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("The field is still. No voices today.")

elif view_mode == "Morning Digest":
    centered_header("Agora Daily — Morning Digest", level="h1")

    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    reflections_df = load_reflections()
    reflections_df["timestamp"] = pd.to_datetime(reflections_df["timestamp"], errors="coerce")
    reflections_df["date"] = reflections_df["timestamp"].dt.date
    yesterday_data = reflections_df[reflections_df["date"] == yesterday]

    if yesterday_data.empty:
        st.info("No reflections found for yesterday.")
    else:
        top_headlines = yesterday_data["headline"].value_counts().head(3).index.tolist()
        for headline in top_headlines:
            centered_header(f"📰 {headline}", level="h2")
            subset = yesterday_data[yesterday_data["headline"] == headline]
            grouped = {"Reflections": [{"text": r} for r in subset["reflection"].tolist()]}
            with st.spinner("Summarizing reflections..."):
                summary = generate_ai_summary(headline, grouped)
                st.success(summary)
            show_inspirational_whisper()
            st.markdown("---")
