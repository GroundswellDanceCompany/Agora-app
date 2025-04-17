
import streamlit as st
import praw
from textblob import TextBlob
from collections import defaultdict
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

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
else:
    subreddit = st.selectbox("Choose subreddit:", ["news", "worldnews", "politics"])
    posts = reddit.subreddit(subreddit).hot(limit=15)
    for post in posts:
        if not post.stickied:
            headline_options.append(post.title)
            post_dict[post.title] = post

selected_headline = st.selectbox("Select a headline to reflect on:", headline_options)

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

    emotion_icons = {
        "Positive": "🟢 😊",
        "Neutral": "⚪️ 😐",
        "Negative": "🔴 😠"
    }

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
        st.caption(f"Filtered out {filtered_out} low-signal comments.")

        st.subheader("Sentiment Threads")

        for label in ["Positive", "Neutral", "Negative"]:
            emoji, color = emotion_style(label)
            icon = emotion_icons.get(label, "")
            st.markdown(f"<h3 style='color:{color}'>{icon} {label.upper()} ({emotion_counts[label]})</h3>", unsafe_allow_html=True)

            comments = emotion_groups[label]
            if comments:
                highlight = max(comments, key=lambda c: abs(c["score"]))
                st.markdown(f"""
<div style="border-left: 4px solid {color}; padding: 0.5em 1em; background-color: #222; color: white; margin-bottom: 10px;">
    <strong>⭐ Highlight:</strong> {highlight['text']}
    <br><span style='color:#ccc; font-size:0.8em'><i>{highlight['author']} • {highlight['created']} • Sentiment: {highlight['score']}</i></span>
</div>
""", unsafe_allow_html=True)

                extras = [c for c in comments if c != highlight][:2]
                for c in extras:
                    st.markdown(f"""
<div style="margin-bottom: 8px;">
    <blockquote style="margin: 0; padding-left: 10px; border-left: 2px solid #444;">{c['text']}</blockquote>
    <span style='color:gray; font-size:0.75em'><i>{c['author']} • {c['created']} • Sentiment: {c['score']}</i></span>
</div>
""", unsafe_allow_html=True)
            else:
                st.markdown("<i>No comments found for this emotion.</i>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Your Reflection")
    emotions = ["Angry", "Hopeful", "Skeptical", "Confused", "Inspired", "Indifferent"]
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
