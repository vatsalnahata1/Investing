import os
import smtplib
import json
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import anthropic

SERPER_API_KEY = os.environ["SERPER_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_USER)

SEARCH_QUERIES = {
    "morgan_stanley": "Morgan Stanley news today 2026",
    "competitors": "Goldman Sachs JPMorgan Citigroup macro markets rates geopolitics news today 2026",
    "capgemini": "Capgemini financial services consulting technology news today 2026",
    "tech": "AI Google Meta Apple Nvidia product launch announcement today 2026",
    "us_policy": "US banking regulation Federal Reserve Wall Street policy news today 2026",
    "quirky": "funny quirky unusual news sports fun fact today 2026",
}

NEWSLETTER_PROMPT = """You are a personal financial-services news analyst. Today is {date}.

Below are raw search results for six newsletter sections. Write a concise email newsletter.
Lead each item with the key fact, keep it skimmable, cite the source outlet in parentheses.
Add a "60-SECOND SKIM" block at the very top — one punchy bullet per section.

SEARCH RESULTS:

1. MORGAN STANLEY WATCH — news specifically about Morgan Stanley:
{morgan_stanley}

2. COMPETITOR & MARKET MOVES — peers (Goldman Sachs, JPMorgan, etc.) and macro (rates, oil, geopolitics):
{competitors}

3. CAPGEMINI & FS-SECTOR PEERS — Capgemini plus competitor consulting/tech firms in financial services:
{capgemini}

4. TECH & NEW RELEASES — AI and big-tech (Google, Meta, Apple, Nvidia) launches and announcements:
{tech}

5. US POLICY — regulatory/policy news affecting large banks and Wall Street:
{us_policy}

6. OTHERS (FYI) — exactly two light items: something that makes me smile, sports news, or a quirky FYI.
   Example style: "10,000 steps/day was a 1960s Japanese pedometer marketing campaign, not science."
{quirky}

Rules:
- If a section has no real news, write "Nothing notable today."
- Output clean plain text ready to paste into an email.
- Section headers in ALL CAPS.
- 3-5 bullet points per section, each starting with a dash.
- Keep it skimmable — one sentence per bullet where possible.
"""


def search_news(query: str) -> str:
    url = "https://google.serper.dev/news"
    payload = json.dumps({"q": query, "num": 6, "tbs": "qdr:d"})
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=payload, timeout=15)
    response.raise_for_status()
    items = response.json().get("news", [])
    lines = [
        f"- {item.get('title', '')} ({item.get('source', '')}) — {item.get('snippet', '')}"
        for item in items
    ]
    return "\n".join(lines) if lines else "No results found."


def generate_newsletter(date_str: str, search_results: dict) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = NEWSLETTER_PROMPT.format(date=date_str, **search_results)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def send_email(subject: str, body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())


def main():
    date_str = datetime.now().strftime("%B %d, %Y")
    print(f"Generating newsletter for {date_str}...")

    search_results = {}
    for key, query in SEARCH_QUERIES.items():
        print(f"  Fetching: {key}...")
        search_results[key] = search_news(query)

    print("Generating with Claude...")
    body = generate_newsletter(date_str, search_results)

    subject = f"Daily Financial Briefing — {date_str}"
    print("Sending email...")
    send_email(subject, body)
    print("Done. Newsletter sent.")


if __name__ == "__main__":
    main()
