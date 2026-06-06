import os
import smtplib
import time
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_USER)

PREMIUM_DOMAINS = [
    "bloomberg.com", "wsj.com", "ft.com", "cnbc.com",
    "reuters.com", "economist.com", "barrons.com", "marketwatch.com",
]
TECH_DOMAINS = [
    "bloomberg.com", "wsj.com", "techcrunch.com", "cnbc.com",
    "theverge.com", "wired.com", "arstechnica.com",
]

# Each section: (header, why_it_matters_tag, search_query, domains)
# Queries are tuned for a Capgemini Sales/Account Rep whose client is Morgan Stanley.
SECTIONS = [
    (
        "1. MORGAN STANLEY",
        "Know what your client is thinking about before you walk in.",
        "Morgan Stanley technology strategy AI digital transformation investment today",
        PREMIUM_DOMAINS,
    ),
    (
        "2. MARKET & COMPETITORS",
        "Macro context that shapes MS priorities — and your pitch.",
        "Goldman Sachs JPMorgan Wall Street AI technology strategy deal news today",
        PREMIUM_DOMAINS,
    ),
    (
        "3. CAPGEMINI",
        "What your own firm is selling — use this in client conversations.",
        "Capgemini financial services AI digital transformation new deal partnership today",
        PREMIUM_DOMAINS,
    ),
    (
        "4. TECH TO WATCH",
        "AI moves MS will likely act on — potential Capgemini opportunity.",
        "AI automation financial services banking technology launch Microsoft Google today",
        TECH_DOMAINS,
    ),
    (
        "5. REGULATION & POLICY",
        "New compliance requirements = new consulting work at MS.",
        "US bank regulation compliance technology requirement Morgan Stanley Wall Street today",
        PREMIUM_DOMAINS,
    ),
    (
        "6. ICEBREAKER",
        "One thing to open a conversation with.",
        "surprising interesting fact sport news today",
        [],
    ),
]

MAX_ITEMS_PER_SECTION = 2
SNIPPET_MAX_CHARS = 130


def search_news(query: str, domains: list) -> list:
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "days": 3,
        "max_results": MAX_ITEMS_PER_SECTION + 1,
    }
    if domains:
        payload["include_domains"] = domains
    for attempt in range(3):
        try:
            response = requests.post("https://api.tavily.com/search", json=payload, timeout=20)
            response.raise_for_status()
            return response.json().get("results", [])[:MAX_ITEMS_PER_SECTION]
        except Exception as e:
            print(f"    Search attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(3)
    return []


def source_from_url(url: str) -> str:
    try:
        host = url.split("/")[2].replace("www.", "")
        return host.split(".")[0].capitalize()
    except Exception:
        return ""


def trim(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def format_section(header: str, tag: str, items: list) -> tuple:
    """Returns (skim_line, full_block)."""
    if not items:
        return (f"• {header}: Nothing notable today.", f"{header}\nNothing notable today.\n")

    first_title = items[0].get("title", "").strip()
    skim = f"• {first_title}"

    lines = [f"{header}  [{tag}]"]
    for item in items:
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        snippet = trim(item.get("content", ""), SNIPPET_MAX_CHARS)
        src = source_from_url(url)
        src_tag = f" ({src})" if src else ""
        lines.append(f"  - {title}{src_tag}")
        if snippet:
            lines.append(f"    {snippet}")
        lines.append(f"    → {url}")
    return (skim, "\n".join(lines))


def build_newsletter(date_str: str, all_results: list) -> str:
    skim_lines = ["YOUR 60-SECOND BRIEF\n"]
    section_blocks = []

    for (header, tag, _, _), items in zip(SECTIONS, all_results):
        skim, block = format_section(header, tag, items)
        skim_lines.append(skim)
        section_blocks.append(block)

    divider = "─" * 55
    parts = (
        [f"Daily Briefing for {date_str}", divider]
        + ["\n".join(skim_lines)]
        + [divider]
        + section_blocks
    )
    return "\n\n".join(parts)


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

    all_results = []
    for header, _, query, domains in SECTIONS:
        print(f"  Fetching: {header}...")
        all_results.append(search_news(query, domains))
        time.sleep(1)

    body = build_newsletter(date_str, all_results)
    subject = f"Your Daily Briefing — {date_str}"
    print("Sending email...")
    send_email(subject, body)
    print("Done.")


if __name__ == "__main__":
    main()
