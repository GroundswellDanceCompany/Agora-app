import praw
from textblob import TextBlob

# Replace with your actual Reddit app keys
reddit = praw.Reddit(
    client_id="MerkiHK2ZT5uN8Q2YllzmA",
    client_secret="8loi3D1as5ghnrLtblG55o7taKCZMQ",
    user_agent="agora-app by /u/Agreeable_Throat512"
)

import streamlit as st

# Predefined emotions
emotions = ["Angry", "Hopeful", "Skeptical", "Confused", "Inspired", "Indifferent"]

st.title("Agora — Public Sentiment on Headlines")

st.subheader("Top Headlines from Reddit")

subreddit = st.selectbox("Choose subreddit:", ["news", "worldnews", "politics"])
posts = reddit.subreddit(subreddit).hot(limit=10)

headline_options = []
for post in posts:
    if not post.stickied:
        headline_options.append(post.title)

selected_headline = st.selectbox("Select a headline to reflect on:", headline_options)
st.markdown(f"**Selected Headline:** {selected_headline}")

st.subheader("Analyzing Reddit Comments...")

# Search Reddit again to get the selected post's full object
posts = reddit.subreddit(subreddit).hot(limit=10)
submission = None

for post in posts:
    if post.title == selected_headline:
        submission = reddit.submission(id=post.id)
        break

if submission:
    submission.comments.replace_more(limit=0)
    comments = submission.comments[:30]

    # Sentiment analysis
    emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}

    for comment in comments:
        analysis = TextBlob(comment.body)
        polarity = analysis.sentiment.polarity

        if polarity > 0.1:
            emotion_counts["Positive"] += 1
        elif polarity < -0.1:
            emotion_counts["Negative"] += 1
        else:
            emotion_counts["Neutral"] += 1

    st.subheader("Public Sentiment Breakdown")
    st.write(emotion_counts)
    st.bar_chart(emotion_counts)
else:
    st.warning("Could not load comments for this post.")

# Optional: simple pie chart
st.subheader("Visual Breakdown")
st.bar_chart(emotion_counts)

# Example headline (replace with real data later)
headline = "Climate Crisis Accelerates: UN Warns of Irreversible Damage"
st.subheader(headline)

st.markdown("**How does this headline make you feel?**")
selected_emotions = st.multiselect("Select one or more emotions:", emotions)

trust_level = st.slider("How much do you trust this headline?", 1, 5, 3)
reflection = st.text_area("Your reflection (optional)", height=150)

if st.button("Submit Reflection"):
    st.success("Thanks for your input!")
    # This is where you'd send data to a backend, save to DB, etc.
    st.json({
        "headline": headline,
        "emotions": selected_emotions,
        "trust_level": trust_level,
        "reflection": reflection
    })
