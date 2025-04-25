# --- Imports ---
import streamlit as st
import praw
from textblob import TextBlob
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import uuid
from openai import OpenAI
from collections import defaultdict
import time
from PIL import Image
import plotly.express as px

# --- Banner Loader ---
placeholder = st.empty()
with placeholder.container():
    banner = Image.open("Agora-image.png")
    st.image(banner, use_container_width=True)
    st.markdown("<h4 style='text-align: center;'>Tuning into the collective field...</h4>", unsafe_allow_html=True)
    time.sleep(2)
placeholder.empty()

# --- Setup Connections ---
# OpenAI
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
                {"role": "system", "content": "You are a civic poet summarizing emotional public mood."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "**Summary unavailable — but the field is listening.**"

# Google Sheets
SCOPE = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)
sheet = client.open("AgoraData")
reflections_ws = sheet.worksheet("Reflections")
replies_ws = sheet.worksheet("Replies")
reaction_ws = sheet.worksheet("CommentReactions")

def load_reflections():
    return pd.DataFrame(reflections_ws.get_all_records())

def load_replies():
    return pd.DataFrame(replies_ws.get_all_records())

# Reddit
reddit = praw.Reddit(
    client_id=st.secrets["reddit"]["client_id"],
    client_secret=st.secrets["reddit"]["client_secret"],
    user_agent=st.secrets["reddit"]["user_agent"]
)

curated_subreddits = [
    "news", "worldnews", "politics", "uspolitics", "ukpolitics", "europe",
    "MiddleEastNews", "technology", "Futurology", "science", "space", "environment", "geopolitics"
]

# --- Public Comments Section ---
st.markdown("### Public Comments")
if comments:
    for comment in comments:
        text = comment.body.strip()
        if text and len(text) > 10:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            sentiment = "😊 Positive" if polarity > 0.1 else "😐 Neutral" if polarity > -0.1 else "😠 Negative"
            st.markdown(f"> {text}\n\n*Sentiment: {sentiment}*")
else:
    st.info("No readable comments found for this post.")

# --- Core Functions ---
def show_reflection_interface(selected_headline):
    st.subheader("Your Reflection")
    st.markdown("> Let the field hear your truth.")

    emotions = ["Angry", "Hopeful", "Skeptical", "Confused", "Inspired", "Indifferent"]
    emotion_choice = st.multiselect("Emotional waves you felt:", emotions, key="emotion_multiselect")
    trust_rating = st.slider("How much do you trust this headline?", 1, 5, 3, key="trust_slider")
    user_thoughts = st.text_area("If you could whisper one insight into the Agora, what would it be?", key="reflection_text")

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
        st.success("Your voice has joined the field.")

    st.markdown("---")
    show_public_reflections(selected_headline)

def show_public_reflections(selected_headline):
    st.subheader("Public Reflections")

    all_reflections = load_reflections()
    all_replies = load_replies()
    matched = all_reflections[all_reflections["headline"] == selected_headline]

    if matched.empty:
        st.info("No reflections yet. The field awaits.")
    else:
        for _, row in matched.iterrows():
            st.markdown(f"**Emotions:** {row['emotions']}")
            st.markdown(f"**Trust Level:** {row['trust_level']}/5")
            st.markdown(f"**Reflection:** {row['reflection']}")
            st.caption(f"{row['timestamp']}")
            with st.form(key=f"reply_form_{row['reflection_id']}"):
                reply_text = st.text_input("Reply to this reflection:", key=f"r_{row['reflection_id']}")
                if st.form_submit_button("Send Reply") and reply_text.strip():
                    replies_ws.append_row([row["reflection_id"], reply_text.strip(), datetime.utcnow().isoformat()])
                    st.success("Reply added.")
            st.markdown("---")

def show_sentiment_field():
    st.subheader("Sentiment Field — Collective Emotional Landscape")
    st.markdown("> Every point is a heartbeat. Every color a signal.")

    reflection_data = load_reflections()

    if not reflection_data.empty:
        reflection_data["timestamp"] = pd.to_datetime(reflection_data["timestamp"], errors="coerce")
        reflection_data["trust_level"] = pd.to_numeric(reflection_data["trust_level"], errors="coerce")
        reflection_data = reflection_data.dropna(subset=["trust_level", "emotions", "reflection"])
        reflection_data["primary_emotion"] = reflection_data["emotions"].apply(
            lambda x: x.split(",")[0].strip() if pd.notnull(x) else "Neutral"
        )

        fig = px.scatter(
            reflection_data,
            x="trust_level",
            y="primary_emotion",
            color="primary_emotion",
            hover_data=["reflection"],
            size_max=60,
            title="Agora Emotional Field",
            labels={"trust_level": "Trust Level (1–5)", "primary_emotion": "Emotion"}
        )
        fig.update_layout(
            height=600,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color="white"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No reflections yet. The field is waiting.")

def show_morning_digest():
    st.title("Agora Daily — Morning Digest")
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
            st.markdown(f"### 📰 {headline}")
            subset = yesterday_data[yesterday_data["headline"] == headline]
            grouped = {"Reflections": [{"text": r} for r in subset["reflection"].tolist()]}
            with st.spinner("Gathering yesterday’s pulse..."):
                summary = generate_ai_summary(headline, grouped)
                st.success(summary)
            st.markdown("---")

# --- Main App Layout ---
st.title("Agora — The Collective Pulse")
just_comments = st.toggle("I'm just here for the comments")

if "show_about" not in st.session_state:
    st.session_state.show_about = True

with st.expander("🌎 About Agora", expanded=st.session_state.show_about):
    st.session_state.show_about = False
    st.markdown("""
    **Agora** is an open space where public sentiment, reflection, and dialogue are woven into a living field.
    No manipulation. No clickbait. Just collective feeling and thought — emerging in real time.
    """)

view_mode = st.sidebar.radio("Choose View", ["Live Agora", "Morning Digest"])

if view_mode == "Live Agora":
    topic = st.text_input("Enter a topic to listen across curated subreddits")

    if topic:
        post_dict = {}
        headline_options = []
        for sub in curated_subreddits:
            try:
                for post in reddit.subreddit(sub).search(topic, sort="relevance", time_filter="week", limit=2):
                    if not post.stickied:
                        headline_options.append(post.title)
                        post_dict[post.title] = post
            except:
                continue

        if headline_options:
            selected_headline = st.radio("Select a headline to reflect on:", headline_options)

            if selected_headline:
                post = post_dict[selected_headline]
                st.markdown(f"## 📰 {selected_headline}")
                submission = reddit.submission(id=post.id)
                submission.comments.replace_more(limit=0)
                comments = submission.comments[:30]

                emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
                emotion_groups = defaultdict(list)

                for comment in comments:
                    text = comment.body.strip()
                    if text and len(text) > 10:
                        blob = TextBlob(text)
                        polarity = blob.sentiment.polarity
                        label = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"
                        emotion_counts[label] += 1
                        emotion_groups[label].append({
                            "text": text,
                            "score": round(polarity, 3)
                        })

                if not just_comments:
                    with st.spinner("Listening to the field..."):
                        summary = generate_ai_summary(selected_headline, emotion_groups)
                        st.success(summary)

                show_reflection_interface(selected_headline)
                show_sentiment_field()
        else:
            st.info("No posts found for this topic.")
else:
    show_morning_digest()
