import streamlit as st

# Predefined emotions
emotions = ["Angry", "Hopeful", "Skeptical", "Confused", "Inspired", "Indifferent"]

st.title("Agora — Public Sentiment on Headlines")

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
