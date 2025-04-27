
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

# --- Page Config ---
st.set_page_config(
    page_title="Agora — Public Sentiment Field",
    page_icon=":crystal_ball:",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
.fade-in {
  opacity: 0;
  animation: fadeInAnimation ease 1s;
  animation-fill-mode: forwards;
  animation-delay: 0.2s;
}
.fade-button button {
  opacity: 0;
  animation: fadeInAnimation ease 1.5s;
  animation-fill-mode: forwards;
  animation-delay: 1.2s;
}
@keyframes fadeInAnimation {
  0% { opacity: 0; }
  100% { opacity: 1; }
}
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

@keyframes glowPulse {
    0% { filter: drop-shadow(0 0 5px gold); }
    100% { filter: drop-shadow(0 0 20px gold); }
}
.fade-button button:hover {
    background-color: #444;
    box-shadow: 0 0 15px gold;
}

# --- Helper Functions ---
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
comment_reflections_ws = get_or_create_worksheet(sheet, "CommentReflections", ["headline", "comment_snippet", "reflection", "timestamp"])

# --- Reddit Setup ---
reddit = praw.Reddit(
    client_id=st.secrets["reddit"]["client_id"],
    client_secret=st.secrets["reddit"]["client_secret"],
    user_agent=st.secrets["reddit"]["user_agent"]
)

curated_subreddits = ["news", "worldnews", "politics", "uspolitics", "technology", "science", "geopolitics"]

# --- Welcome Screen Logic ---
if "entered_field" not in st.session_state:
    st.session_state.entered_field = False

if not st.session_state.entered_field:
    # Sacred Portal Page

    st.markdown("""
    <div style="text-align:center; margin-top:80px;">
        <img src="https://yourdomain.com/flower_portal.png" style="width:180px; animation:glowPulse 3s infinite alternate;">
        <div style="margin-top:30px; font-size:26px; color:#ccc; font-style:italic;">
            The Field awaits your reflection.
        </div>
        <br>
        <div class="fade-button">
            <form action="">
                <button style="margin-top:30px; font-size:20px; padding:10px 30px; border:none; border-radius:20px; background-color:#333; color:#ccc; cursor:pointer; animation:glowPulse 2s infinite alternate;">
                    Step Into the Field
                </button>
            </form>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # When user clicks, set session state manually
    if st.button("I am ready"):
        st.session_state.entered_field = True
        st.rerun()

else:
    # --- Main Agora ---
    st.title("Agora — Public Sentiment Field")

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

            with st.container():
                st.markdown(f"""
                <div class='fade-in'>
                    <div style='text-align: center; font-size: 26px; font-weight: 400; color: #ccc; margin-top: 20px; margin-bottom: 30px;'>
                        📰 {selected_headline}
                    </div>
                    <div style='text-align: center; margin-bottom: 40px;'>
                        <h3 style='color: #aaa;'>Your Immediate Reflection</h3>
                    </div>
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
                    st.success("Reflection submitted!")
                    st.session_state["emotion_choice"] = []
                    st.session_state["trust_rating"] = 3
                    st.session_state["user_thoughts"] = ""

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

                for comment in comments:
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
                                    if st.form_submit_button("Submit Reflection") and user_reflection.strip():
                                        comment_reflections_ws.append_row([
                                            selected_headline,
                                            comment["text"][:100],
                                            user_reflection.strip(),
                                            datetime.utcnow().isoformat()
                                        ])
                                        auto_trim_worksheet(comment_reflections_ws)
                                        st.success("Reflection added!")

            # --- Public Reflections Section ---
            st.subheader("Public Reflections")
            all_reflections = pd.DataFrame(reflections_ws.get_all_records())
            if not all_reflections.empty:
                matched = all_reflections[all_reflections["headline"] == selected_headline]
                for _, row in matched.iterrows():
                    st.markdown(f"**Emotions:** {row['emotions']}")
                    st.markdown(f"**Trust:** {row['trust_level']}/5")
                    st.markdown(f"**Reflection:** {row['reflection']}")
                    st.caption(f"{row['timestamp']}")
                    st.markdown("---")
            else:
                st.info("No reflections found yet.")

            # --- Sentiment Field Visualization ---
            st.subheader("Sentiment Field — Emotional Landscape")
            if not all_reflections.empty:
                all_reflections["timestamp"] = pd.to_datetime(all_reflections["timestamp"], errors="coerce")
                all_reflections["primary_emotion"] = all_reflections["emotions"].apply(lambda x: x.split(",")[0].strip() if pd.notnull(x) else "Neutral")
                fig = px.scatter(
                    all_reflections,
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

        else:
            st.warning("Please select a headline to continue.")

    # --- Morning Digest Mode ---
    elif view_mode == "Morning Digest":
        st.title("Agora Morning Digest — Yesterday's Top Reflections")

        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        reflections_df = pd.DataFrame(reflections_ws.get_all_records())
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
