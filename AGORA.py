# Agora — Live Public Sentiment App
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

# --- Display loading banner ---
placeholder = st.empty()
with placeholder.container():
    banner = Image.open("Agora-image.png")
    st.image(banner, use_container_width=True)
    st.markdown("<h4 style='text-align: center;'>Loading Agora...</h4>", unsafe_allow_html=True)
    time.sleep(2)
placeholder.empty()

# --- AI Summary using OpenAI ---
def generate_ai_summary(headline, grouped_comments):
    prompt = f"Headline: {headline}\n"
    for label, comments in grouped_comments.items():
        prompt += f"\n{label} Comments:\n"
        for c in comments[:2]:
            prompt += f"- {c['text']}\n"
    prompt += "\nSummarize public sentiment in 2-3 sentences. Capture emotional tone, major concerns, and common hopes. Be neutral and insightful."

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

# --- Google Sheets Auth ---
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

# --- More logic continues below...
# Due to token limits, this is the first part of the script.
# Let me know to continue writing the full application logic block-by-block.



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
just_comments = st.toggle("I'm just here for the comments")
if "show_about" not in st.session_state:
    st.session_state.show_about = True

with st.expander("🌎 What is Agora?", expanded=st.session_state.show_about):
    st.session_state.show_about = False  # Collapse on future interactions
    st.markdown("""
**Agora** is a space for exploring public sentiment on the news — powered by Reddit comments, AI summaries, and community reflections.

- Search any topic to see what people are feeling across curated subreddits.
- Analyze emotional sentiment (positive, neutral, negative).
- Read and react to real Reddit comments.
- Reflect and respond — or just observe the emotional pulse of the internet.

**Why Agora?**  
Named after the ancient Greek gathering space, Agora is a modern town square for civic awareness and global emotional insight

Welcome to the future of collective awareness.
    """)

view_mode = st.sidebar.radio("View Mode", ["Live View", "Morning Digest"])

# --- Topic Search Section ---
headline_options = []
post_dict = {}
search_results = []

if view_mode == "Live View":
    topic = st.text_input("Enter a topic to search across curated subreddits")

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
