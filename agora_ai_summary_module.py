# --- Optional: AI Summary of Consensus ---
import openai

def generate_ai_summary(headline, grouped_comments):
    prompt = f"Headline: {headline}\n"
    for label, comments in grouped_comments.items():
        prompt += f"\n{label} Comments:\n"
        for c in comments[:2]:
            prompt += f"- {c['text']}\n"

    prompt += "\nSummarize public sentiment in 2-3 sentences. Capture emotional tone, major concerns, and common hopes. Be neutral and insightful."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a news analyst summarizing public emotional sentiment."},
                      {"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.7,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Could not generate summary: {str(e)}"
