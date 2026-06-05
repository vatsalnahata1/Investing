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
    "morgan_stanley": "Morgan Stanley news today site:bloomberg.com OR site:wsj.com OR site:ft.com OR site:cnbc.com OR site:reuters.com OR site:ft.com",
    "competitors": "Goldman Sachs JPMorgan Citigroup Wall Street US markets rates Fed geopolitics news today site:bloomberg.com OR site:wsj.com OR site:cnbc.com OR site:reuters.com",
    "capgemini": "Capgemini financial services consulting technology news today site:ft.com OR site:bloomberg.com OR site:reuters.com OR site:businesswire.com",
    "tech": "Google Meta Apple Microsoft Amazon Nvidia AI product launch announcement news today site:bloomberg.com OR site:wsj.com OR site:techcrunch.com OR site:cnbc.com OR site:theverge.com",
    "us_policy": "US banking regulation Federal Reserve OCC FDIC Wall Street policy Congress news today site:wsj.com OR site:bloomberg.com OR site:reuters.com OR site:ft.com",
    "quirky": "funny quirky unusual news sports fun fact today 2026",
}

NEWSLETTER_PROMPT = """You are a personal financial-services news analyst based in New York. Today is {date}.

Below are raw search results (title | source | URL | snippet) for six newsletter sections.
Write a concise email newsletter with these rules:

FORMATTING RULES:
- Add a "60-SECOND SKIM" block at the very top — one punchy bullet per section (no links needed there).
- Section headers in ALL CAPS.
- 3–5 bullet points per section, each starting with a dash.
- After each bullet, include the full article URL on its own line, indented two spaces, prefixed with "→ ".
  Example:
    - Goldman Sachs raises $5B in new credit fund amid tightening markets. (Bloomberg)
      → https://bloomberg.com/...
- Lead each bullet with the key fact; keep it to 1–2 sentences.
- US news takes priority; include international news only when it materially affects US markets or institutions.
- If a section has no real news, write "Nothing notable today."
- For Section 4 (TECH), cover each of the major companies (Google, Meta, Apple, Microsoft, Amazon, Nvidia)
  proportionally to what's actually newsworthy — do NOT default to Nvidia alone; give airtime to all.
- For Section 6 (OTHERS/FYI), write exactly two light items — something funny, a sports story, or a
  quirky historical/trivia fact (e.g. "10,000 steps/day was a 1960s Japanese marketing term, not science").

SEARCH RESULTS:

1. MORGAN STANLEY WATCH — news specifically about Morgan Stanley:
{morgan_stanley}

2. COMPETITOR & MARKET MOVES — US peers (Goldman Sachs, JPMorgan, etc.) and macro (rates, oil, geopolitics) that affect MS:
{competitors}

3. CAPGEMINI & FS-SECTOR PEERS — Capgemini plus competitor consulting/tech firms in financial services worldwide:
{capgemini}

4. TECH & NEW RELEASES — AI and big-tech (Google, Meta, Apple, Microsoft, Amazon, Nvidia) launches and news — balanced coverage:
{tech}

5. US POLICY — regulatory/policy news affecting large US banks and Wall Street:
{us_policy}

6. OTHERS (FYI) — exactly two light items:
{quirky}
"""


def search_news(query: str) -> str:
    url = "https://google.serper.dev/news"
    payload = json.dumps({"q": query, "num": 8, "tbs": "qdr:d", "gl": "us"})
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=payload, timeout=15)
    response.raise_for_status()
    items = response.json().get("news", [])
    lines = [
        f"- {item.get('title', '')} | {item.get('source', '')} | {item.get('link', '')} | {item.get('snippet', '')}"
        for item in items
    ]
    return "\n".join(lines) if lines else "No results found."


def generate_newsletter(date_str: str, search_results: dict) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = NEWSLETTER_PROMPT.format(date=date_str, **search_results)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3500,
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
