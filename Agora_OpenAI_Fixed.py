
import streamlit as st
import praw
from textblob import TextBlob
from collections import defaultdict
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
from openai import OpenAI

# --- AI Summary using OpenAI >=1.0.0 format ---
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
            model="gpt-4",  # or "gpt-4-turbo"
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
