
import streamlit as st
import praw
from textblob import TextBlob
from collections import defaultdict
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import uuid
from openai import OpenAI
import time
from PIL import Image

# --- Banner Loader ---
placeholder = st.empty()
with placeholder.container():
    banner = Image.open("Agora-image.png")
    st.image(banner, use_container_width=True)
    st.markdown("<h4 style='text-align: center;'>Loading Agora...</h4>", unsafe_allow_html=True)
    time.sleep(2)
placeholder.empty()

# --- OpenAI Summary ---
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
                {"role": "system", "content": "You are a news analyst summarizing public emotional sentiment."},
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
reflections_ws = sheet.worksheet("Reflections")
replies_ws = sheet.worksheet("Replies")
reaction_ws = sheet.worksheet("CommentReactions")
summary_ws = sheet.worksheet("Summaries")

def load_reflections():
    return pd.DataFrame(reflections_ws.get_all_records())

def load_replies():
    return pd.DataFrame(replies_ws.get_all_records())

# --- Reddit Setup ---
reddit = praw.Reddit(
    client_id=st.secrets["reddit"]["client_id"],
    client_secret=st.secrets["reddit"]["client_secret"],
    user_agent=st.secrets["reddit"]["user_agent"]
)

# --- Subreddits ---
curated_subreddits = [
    "news", "worldnews", "politics", "uspolitics", "ukpolitics", "europe",
    "MiddleEastNews", "technology", "Futurology", "science", "space", "environment",
    "geopolitics", "AutoNews"
]

# --- UI Layout ---
st.title("Agora — Live Public Sentiment")
just_comments = st.toggle("I'm just here for the comments")

if "show_about" not in st.session_state:
    st.session_state.show_about = True

with st.expander("🌎 What is Agora?", expanded=st.session_state.show_about):
    st.session_state.show_about = False
    st.markdown("""
    Agora is a space for exploring public sentiment on the news — powered by Reddit comments, AI summaries, and community reflections.
    """)

view_mode = st.sidebar.radio("View Mode", ["Live View", "Morning Digest"])

if view_mode == "Live View":
    topic = st.text_input("Enter a topic to search across curated subreddits")
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
        st.caption(f"Showing {start+1} to {min(end, len(headline_options))} of {len(headline_options)} results")
        selected_headline = st.radio("Select a headline to reflect on:", paged_headlines)
    else:
        subreddit = st.selectbox("Choose subreddit:", ["news", "worldnews", "politics"])
        posts = reddit.subreddit(subreddit).hot(limit=15)
        for post in posts:
            if not post.stickied:
                headline_options.append(post.title)
                post_dict[post.title] = post
        selected_headline = st.radio("Select a headline to reflect on:", headline_options)

    if selected_headline:
        post = post_dict[selected_headline]
        st.markdown(f"## 📰 {selected_headline}")
        submission = reddit.submission(id=post.id)
        submission.comments.replace_more(limit=0)
        comments = submission.comments[:30]
        st.write(f"Total comments pulled from Reddit: {len(comments)}")

        emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
        emotion_groups = defaultdict(list)
        filtered_out = 0

        for comment in comments:
            text = comment.body.strip()
            if not text or len(text) < 10:
                filtered_out += 1
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

        if sum(emotion_counts.values()) == 0:
            st.warning("No comments passed the quality filter.")
        else:
            if just_comments:
                st.subheader("Reddit Comments by Sentiment")

                def emotion_style(label):
                    return {
                        "Positive": ("😊", "green"),
                        "Neutral": ("😐", "gray"),
                        "Negative": ("😠", "red")
                    }.get(label, ("❓", "blue"))

                for label in ["Positive", "Neutral", "Negative"]:
                    emoji, color = emotion_style(label)
                    st.markdown(f"<h3 style='color:{color}'>{emoji} {label}</h3>", unsafe_allow_html=True)
                    group = emotion_groups[label]
                    if group:
                        for c in group[:3]:
                            st.markdown(f"- {c['text']}")
                    else:
                        st.markdown(f"_No {label.lower()} comments._")
            else:
                with st.spinner("Generating AI insight..."):
                    summary = generate_ai_summary(selected_headline, emotion_groups)
                    st.markdown("### Agora AI Summary")
                    st.info(summary)

elif view_mode == "Morning Digest":
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
            with st.spinner("Summarizing reflections..."):
                summary = generate_ai_summary(headline, grouped)
                st.success(summary)
                st.markdown("---")
