"""
SuperKalam knowledge base — live-scraped from superkalam.com with a static fallback.
Same pattern as karta_knowledge.py.
"""
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SCRAPE_URLS = [
    "https://superkalam.com/",
    "https://superkalam.com/pricing",
    "https://superkalam.com/mains-evaluation",
    "https://superkalam.com/current-affairs",
]

# Static fallback if scraping fails (curated from superkalam.com)
SUPERKALAM_KNOWLEDGE = """
SuperKalam is a Personal AI Mentor for UPSC (Civil Services) exam preparation.

WHAT IT DOES:
- Acts as a 24x7 personal AI mentor that teaches concepts, resolves doubts instantly,
  and builds daily study discipline — positioned as better than generic ChatGPT or
  traditional coaching institutes because it creates accountability.
- Instant Mains Answer Evaluation: students upload handwritten Mains answers and get
  instant, detailed evaluation with scores and improvement suggestions.
- Full UPSC syllabus coverage: Prelims and Mains (GS papers), with structured notes.
- MCQ & PYQ practice: thousands of practice MCQs and previous-year questions with
  instant explanations.
- Daily Current Affairs: curated coverage linked to the UPSC syllabus.
- Personalised Revision Areas: tracks weak topics and schedules revision.
- Progress Analytics Dashboard: streaks, accuracy, coverage, and time analytics.

WHO IT'S FOR:
- UPSC CSE aspirants (freshers and repeaters), including working professionals
  preparing alongside jobs. Also useful for State PSC aspirants.

WHY SUPERKALAM VS COACHING/CHATGPT:
- Coaching institutes: expensive (often 1-2 lakh+), fixed schedules, no personal attention.
- ChatGPT: generic, no UPSC structure, no evaluation of handwritten answers, no accountability.
- SuperKalam: personal mentor experience at a fraction of coaching cost, instant
  evaluation, structured syllabus coverage, and daily discipline building.

TRACTION:
- Students practice lakhs of MCQs and evaluate thousands of Mains answers monthly.
- Backed by prominent investors (per website).

PLATFORMS: Web app (superkalam.com) and mobile app (Android/iOS).
PRICING: Freemium — free tier to start; paid plans for full mentor features
(see superkalam.com/pricing for current plans in INR).
"""


def get_superkalam_knowledge() -> str:
    """Scrape superkalam.com pages; fall back to the static knowledge if all fail."""
    sections = []
    for url in SCRAPE_URLS:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "noscript"]):
                tag.decompose()
            text = " ".join(soup.get_text(" ").split())
            if len(text) > 200:
                sections.append(f"=== FROM {url} ===\n{text}")
                logger.info(f"Scraped {url}: {len(text)} chars")
        except Exception as e:
            logger.warning(f"Scrape failed for {url}: {e}")

    if sections:
        combined = "\n\n".join(sections)
        logger.info(f"Total live knowledge: {len(combined)} chars from {len(sections)} pages")
        return combined

    logger.warning("All scrapes failed — using static SuperKalam knowledge")
    return SUPERKALAM_KNOWLEDGE
