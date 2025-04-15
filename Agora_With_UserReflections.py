import streamlit as st
import praw
from textblob import TextBlob
from collections import defaultdict
import pandas as pd
import os

# --- Configuration ---
# Replace with your actual Reddit app credentials
reddit = praw.Reddit(
    client_id="MerkiHK2ZT5uN8Q2YllzmA",
    client_secret="8loi3D1as5ghnrLtblG55o7taKCZMQ",
    user_agent="agora-app by /u/Agreeable_Throat512"
)

# --- App Setup ---
st.title("Agora — Public Sentiment on Headlines")
emotions = ["Angry", "Hopeful", "Skeptical", "Confused", "Inspired", "Indifferent"]

# --- Headline Selection ---
st.subheader("Top Headlines from Reddit")
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

    # --- Display headline clearly ---
    st.markdown("---")
    st.markdown("## 🗞️ " + selected_headline)

    # --- Comment Filtering and Sentiment Analysis ---
    emotion_counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    emotion_groups = defaultdict(list)

    for comment in comments:
        if not comment.body or comment.body in ["[deleted]", "[removed]"]:
            continue
        if len(comment.body.split()) < 5 or "http" in comment.body:
            continue

        analysis = TextBlob(comment.body)
        polarity = analysis.sentiment.polarity

        if polarity > 0.1:
            label = "Positive"
        elif polarity < -0.1:
            label = "Negative"
        else:
            label = "Neutral"

        emotion_counts[label] += 1
        emotion_groups[label].append(comment.body)

    # --- Display Results ---
    st.subheader("Public Sentiment Breakdown")
    st.bar_chart(emotion_counts)

    st.subheader("Sample Comments by Emotion")
    for label in ["Positive", "Neutral", "Negative"]:
        st.markdown(f"**{label} ({emotion_counts[label]})**")
        for comment_text in emotion_groups[label][:3]:
            st.markdown(f"- {comment_text}")

    # --- User Reflection ---
    st.markdown("---")
    st.subheader("Your Reflection")

    emotion_choice = st.multiselect(
        "What emotions do you feel reading this headline and the comments?",
        emotions,
        key="user_emotion"
    )

    trust_rating = st.slider("How much do you personally trust this headline?", 1, 5, 3, key="user_trust")
    user_thoughts = st.text_area("Write your reflection (optional)", height=150)

    if st.button("Submit Your Response"):
        st.success("Thanks for adding your voice.")
        st.write("### Your Response")
        st.write(f"**Emotions:** {', '.join(emotion_choice) if emotion_choice else '—'}")
        st.write(f"**Trust Level:** {trust_rating}/5")
        st.write(f"**Reflection:** {user_thoughts if user_thoughts else '—'}")

        # Save to CSV
        df_row = pd.DataFrame([{
            "headline": selected_headline,
            "emotions": ', '.join(emotion_choice),
            "trust": trust_rating,
            "reflection": user_thoughts
        }])

        if os.path.exists("reflections.csv"):
            df_row.to_csv("reflections.csv", mode='a', header=False, index=False)
        else:
            df_row.to_csv("reflections.csv", index=False)

    # --- Public Reflections ---
    if os.path.exists("reflections.csv"):
        all_reflections = pd.read_csv("reflections.csv")
        headline_reflections = all_reflections[all_reflections["headline"] == selected_headline]

        if not headline_reflections.empty:
            st.markdown("---")
            st.subheader("Public Reflections on This Headline")
            for idx, row in headline_reflections.iterrows():
                st.markdown(f"**Emotions:** {row['emotions']}")
                st.markdown(f"**Trust Level:** {row['trust']}/5")
                st.markdown(f"**Reflection:** {row['reflection'] if row['reflection'] else '—'}")
                st.markdown("---")
else:
    st.info("Select a headline from Reddit to begin.")
