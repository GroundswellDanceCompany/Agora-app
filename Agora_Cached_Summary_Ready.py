
import streamlit as st
import praw
from textblob import TextBlob
from collections import defaultdict
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import openai

# --- AI Summary using OpenAI >=1.0.0 format ---
def generate_ai_summary(headline, grouped_comments):
    prompt = f"Headline: {headline}"
    for label, comments in grouped_comments.items():
        prompt += f"\n{label} Comments:\n"
        for c in comments[:2]:
            prompt += f"- {c['text']}\n"

    prompt += "\nSummarize public sentiment in 2-3 sentences. Capture emotional tone, major concerns, and common hopes. Be neutral and insightful."

    try:
        client = openai.OpenAI(api_key=st.secrets["openai"]["api_key"])

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

# --- Summary caching ---
def fetch_or_generate_summary(headline, grouped_comments, summary_ws):
    existing = summary_ws.get_all_records()
    for row in existing:
        if row["headline"] == headline:
            return row["summary_text"]

    summary = generate_ai_summary(headline, grouped_comments)
    summary_ws.append_row([
        headline,
        summary,
        datetime.utcnow().isoformat()
    ])
    return summary

# --- Google Sheets Auth ---
SCOPE = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"],
    scopes=SCOPE
)
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

# --- Curated Subreddits for Topic Search ---
curated_subreddits = [
    "news", "worldnews", "politics", "uspolitics", "ukpolitics",
    "europe", "MiddleEastNews", "IsraelPalestine", "china", "RussiaUkraineWar",
    "technology", "Futurology", "ArtificialInteligence", "science", "space", "energy",
    "TwoXChromosomes", "changemyview", "TrueAskReddit", "OffMyChest",
    "worldpolitics", "conspiracy", "CollapseSupport", "LateStageCapitalism",
    "environment", "climate", "climatechange", "ethicalAI",
    "economics", "CryptoCurrency", "WallStreetBets", "povertyfinance",
    "geopolitics", "neutralnews", "OutOfTheLoop", "AutoNews"
]

# --- UI Layout ---
st.title("Agora — Live Public Sentiment")

# --- Topic Search ---
topic = st.text_input("Enter a topic to search across curated subreddits")

headline_options = []
post_dict = {}
search_results = []

if topic:
    for sub in curated_subreddits:
        try:
            for post in reddit.subreddit(sub).search(topic, sort="relevance", time_filter="week", limit=2):
                if not post.stickied:
                    headline_options.append(post.title)
                    post_dict[post.title] = post
                    search_results.append(post)
        except Exception:
            continue

    page_size = 5
    total_pages = len(headline_options) // page_size + int(len(headline_options) % page_size > 0)

    if total_pages > 1:
        page = st.number_input("Page", min_value=1, max_value=total_pages, step=1)
    else:
        page = 1

    start = (page - 1) * page_size
    end = start + page_size
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

    def emotion_style(label):
        return {
            "Positive": ("😊", "green"),
            "Neutral": ("😐", "gray"),
            "Negative": ("😠", "red")
        }.get(label, ("❓", "blue"))

    for comment in comments:
        text = comment.body.strip()
        if not text or len(text) < 10:
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
        emotion_groups[label].append({
            "text": text,
            "score": round(polarity, 3),
            "author": str(comment.author),
            "created": datetime.utcfromtimestamp(comment.created_utc).strftime("%Y-%m-%d %H:%M")
        })

    if sum(emotion_counts.values()) == 0:
        st.warning("No comments passed the quality filter. Try another post or relax the filtering.")
    else:
        st.subheader("Reddit Sentiment Overview")
        st.bar_chart(emotion_counts)

        # --- AI Summary ---
        with st.spinner("Generating AI insight..."):
            summary = fetch_or_generate_summary(selected_headline, emotion_groups, summary_ws)
            st.markdown("### Agora AI Summary")
            st.info(summary)
            st.caption(f"Filtered out {filtered_out} low-signal comments.")
