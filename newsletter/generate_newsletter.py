import os
import smtplib
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

SECTIONS = [
    ("1. MORGAN STANLEY WATCH",
     "Morgan Stanley news today",
     PREMIUM_DOMAINS),
    ("2. COMPETITOR & MARKET MOVES",
     "Goldman Sachs JPMorgan Citigroup Wall Street US markets rates Fed geopolitics news today",
     PREMIUM_DOMAINS),
    ("3. CAPGEMINI & FS-SECTOR PEERS",
     "Capgemini financial services consulting technology news today",
     PREMIUM_DOMAINS),
    ("4. TECH & NEW RELEASES",
     "Google Meta Apple Microsoft Amazon Nvidia AI product launch announcement news today",
     TECH_DOMAINS),
    ("5. US POLICY",
     "US banking regulation Federal Reserve OCC FDIC Wall Street policy Congress news today",
     PREMIUM_DOMAINS),
    ("6. OTHERS (FYI)",
     "funny quirky unusual news sports interesting fact today",
     []),
]


def search_news(query: str, domains: list) -> list:
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "days": 1,
        "max_results": 5,
    }
    if domains:
        payload["include_domains"] = domains
    response = requests.post("https://api.tavily.com/search", json=payload, timeout=20)
    response.raise_for_status()
    return response.json().get("results", [])


def source_from_url(url: str) -> str:
    try:
        host = url.split("/")[2].replace("www.", "")
        return host.split(".")[0].capitalize()
    except Exception:
        return ""


def format_section(header: str, items: list) -> tuple:
    """Returns (skim_line, full_section_text)."""
    if not items:
        return (f"- {header}: Nothing notable today.", f"{header}\nNothing notable today.\n")

    skim = f"- {items[0].get('title', '').strip()}"

    lines = [header]
    for item in items:
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        snippet = item.get("content", "").strip()
        if len(snippet) > 200:
            snippet = snippet[:200].rsplit(" ", 1)[0] + "..."
        src = source_from_url(url)
        src_tag = f" ({src})" if src else ""
        lines.append(f"- {title}{src_tag}")
        lines.append(f"  → {url}")
        if snippet:
            lines.append(f"  {snippet}")
    lines.append("")
    return (skim, "\n".join(lines))


def build_newsletter(date_str: str, all_results: list) -> str:
    skim_lines = []
    section_blocks = []

    for (header, _, _), items in zip(SECTIONS, all_results):
        skim, block = format_section(header, items)
        skim_lines.append(skim)
        section_blocks.append(block)

    skim_block = "60-SECOND SKIM\n" + "\n".join(skim_lines)
    divider = "-" * 60

    parts = [
        f"Daily Financial Briefing — {date_str}",
        divider,
        skim_block,
        divider,
    ] + section_blocks

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
    for header, query, domains in SECTIONS:
        print(f"  Fetching: {header}...")
        all_results.append(search_news(query, domains))

    body = build_newsletter(date_str, all_results)

    subject = f"Daily Financial Briefing — {date_str}"
    print("Sending email...")
    send_email(subject, body)
    print("Done. Newsletter sent.")


if __name__ == "__main__":
    main()
