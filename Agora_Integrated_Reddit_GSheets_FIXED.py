import streamlit as st
import praw
from textblob import TextBlob
from collections import defaultdict
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

# --- Google Sheets Auth with Correct Scopes ---
SCOPE = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"],
    scopes=SCOPE
)
client = gspread.authorize(creds)
sheet = client.open("AgoraData")
reflections_ws = sheet.worksheet("Reflections")
replies_ws = sheet.worksheet("Replies")

def load_reflections():
    data = reflections_ws.get_all_records()
    return pd.DataFrame(data)

def load_replies():
    data = replies_ws.get_all_records()
    return pd.DataFrame(data)

# --- Reddit Setup ---
reddit = praw.Reddit(
    client_id=st.secrets["reddit"]["client_id"],
    client_secret=st.secrets["reddit"]["client_secret"],
    user_agent=st.secrets["reddit"]["user_agent"]
)

# --- UI Layout ---
st.title("Agora — Live Public Sentiment")
emotions = ["Angry", "Hopeful", "Skeptical", "Confused", "Inspired", "Indifferent"]

subreddit = st.selectbox("Choose subreddit:", ["news", "worldnews", "politics"])
posts = reddit.subreddit(subreddit).hot(limit=15)

headline_options = []
post_dict = {}

for post in posts:
    if not post.stickied:
        headline_options.append(post.title)
        post_dict[post.title] = post

selected_headline = st.selectbox("Select a headline to reflect on:", headline_options)

if selected_headline:
    post = post_dict[selected_headline]
    submission = reddit.submission(id=post.id)
    submission.comments.replace_more(limit=0)
    comments = submission.comments[:30]

    st.markdown("## 📰 " + selected_headline)

    # --- Reddit Comment Analysis ---
    emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    emotion_groups = defaultdict(list)

    filtered_out = 0  # Track how many were filtered

    for comment in comments:
        text = comment.body.strip()
        if not text or text in ["[deleted]", "[removed]"]:
            filtered_out += 1
            continue
        if len(text.split()) < 3 or "http" in text or "bot" in text.lower():
            filtered_out += 1
            continue

        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            label = "Positive"
        elif polarity < -0.1:
            label = "Negative"
        else:
            label = "Neutral"

        emotion_counts[label] += 1
        emotion_groups[label].append(text)

    st.subheader("Reddit Sentiment Overview")
    st.bar_chart(emotion_counts)

    st.caption(f"Filtered out {filtered_out} low-signal comments. Showing top 6 total.")

    # --- User Reflection Input ---
    st.markdown("---")
    st.subheader("Your Reflection")

    emotion_choice = st.multiselect("What emotions do you feel?", emotions)
    trust_rating = st.slider("How much do you trust this headline?", 1, 5, 3)
    user_thoughts = st.text_area("Write your reflection")

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
        st.success("Reflection submitted!")

    # --- Show Reflections & Replies ---
    st.markdown("---")
    st.subheader("Public Reflections")

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
            else:
                st.warning("No replies found or missing 'reflection_id' column.")

            with st.form(key=f"reply_form_{row['reflection_id']}"):
                reply_text = st.text_input("Reply to this reflection:", key=f"r_{row['reflection_id']}")
                submit = st.form_submit_button("Submit Reply")
                if submit and reply_text.strip():
                    replies_ws.append_row([
                        row["reflection_id"],
                        reply_text.strip(),
                        datetime.utcnow().isoformat()
                    ])
                    st.success("Reply added.")
            st.markdown("---")
