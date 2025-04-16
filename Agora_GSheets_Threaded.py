import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid

# --- Google Sheets Auth ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(
    "disco-approach-457007-e1-41db5c8143d8.json",
    scopes=SCOPE
)
client = gspread.authorize(creds)

# --- Load Google Sheet ---
SHEET_NAME = "AgoraData"
sheet = client.open(SHEET_NAME)

reflections_ws = sheet.worksheet("Reflections")
replies_ws = sheet.worksheet("Replies")

# --- Helper: Load worksheets into DataFrames ---
def load_reflections():
    data = reflections_ws.get_all_records()
    return pd.DataFrame(data)

def load_replies():
    data = replies_ws.get_all_records()
    return pd.DataFrame(data)

# --- UI: Headline Entry (temporary input, later to link to Reddit) ---
st.title("Agora: Public Sentiment and Reflection")

headline = st.text_input("Enter or paste a headline to reflect on:")

if headline:
    st.markdown(f"## 📰 {headline}")

    st.subheader("Your Reflection")
    emotion = st.multiselect("What do you feel?", ["Angry", "Hopeful", "Skeptical", "Inspired", "Confused", "Indifferent"])
    trust = st.slider("How much do you trust this headline?", 1, 5, 3)
    reflection_text = st.text_area("Write your reflection")

    if st.button("Submit Reflection"):
        new_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        reflections_ws.append_row([
            new_id,
            headline,
            ", ".join(emotion),
            trust,
            reflection_text,
            timestamp
        ])
        st.success("Reflection submitted!")

    # --- Load & Display Reflections ---
    st.markdown("---")
    st.subheader("Public Reflections on This Headline")

    all_reflections = load_reflections()
    all_replies = load_replies()

    related = all_reflections[all_reflections["headline"] == headline]

    if related.empty:
        st.info("No reflections yet.")
    else:
        for _, row in related.iterrows():
            st.markdown(f"**Emotions:** {row['emotions']}")
            st.markdown(f"**Trust:** {row['trust_level']}/5")
            st.markdown(f"**Reflection:** {row['reflection']}")
            st.caption(f"{row['timestamp']}")

            # --- Replies ---
            this_replies = all_replies[all_replies["reflection_id"] == row["reflection_id"]]
            for _, rep in this_replies.iterrows():
                st.markdown(f"↳ _{rep['reply']}_ — {rep['timestamp']}")

            # --- Reply Form ---
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
