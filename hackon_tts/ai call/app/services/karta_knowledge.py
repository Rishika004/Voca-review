import requests
import re
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

KARTA_KNOWLEDGE = """
=== ABOUT KARTA ===
Karta builds reliable, self-learning AI Agents for complex customer support.
Their agentic AI system automates tasks, delivers human-like results, and continuously
learns to enhance efficiency while reducing costs.

=== WHAT KARTA DOES ===
- Full-Stack AI for Customer Support
- Automates inbound and outbound voice calls, WhatsApp, Chat, and Email
- Supports 30+ languages with cultural context understanding
- 40+ easy integrations with existing tools and workflows
- Multimodal: understands images, documents, and contextual information
- Self-learning: remembers and learns from past conversations

=== KEY RESULTS / METRICS ===
- 80%+ automation even in complex workflows
- 4.5+ CSAT (Customer Satisfaction Score)
- 60%+ Cost Reduction
- 50%+ resolution from day one
- 24/7 operations with human-like intelligence

=== CHANNELS SUPPORTED ===
Voice, WhatsApp, Chat, Email

=== ENTERPRISE FEATURES ===
- SOC 2 Compliant — independently audited for data security
- ISO 27001 Certified — international security standards
- Built-in guardrails that ensure the agent doesn't hallucinate
- Complete visibility inside agent's thoughts, actions, and tool calls
- Auto Quality Assurance — continuously self-tests for accuracy
- Data Encryption, Secure Backup, Access Control, Data Monitoring

=== INTEGRATIONS ===
40+ prebuilt integrations across enterprise systems including tools like
Document Parser, SOP Generator, and more.

=== TRUSTED BY ===
Leading brands including Zomato (automates support for Zomato ground Ops via Smartstaff)

=== CONTACT / DEMO ===
To book a demo or learn more, visit https://www.getkarta.ai or email the team.
Interested candidates or enterprise customers can request a demo directly on the website.
"""


SCRAPE_URLS = [
    "https://www.getkarta.ai/",
    "https://www.getkarta.ai/product",
    "https://www.getkarta.ai/product/agentic-ai-assistance",
    "https://www.getkarta.ai/blog",
]


def _scrape_page(url: str, headers: dict) -> str:
    try:
        r = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "head"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        text = text.encode("ascii", errors="ignore").decode("ascii")
        return text if len(text) > 200 else ""
    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return ""


def get_karta_knowledge() -> str:
    """Returns Karta knowledge base. Scrapes multiple pages, falls back to cached."""
    headers = {"User-Agent": "Mozilla/5.0"}
    parts = []
    for url in SCRAPE_URLS:
        text = _scrape_page(url, headers)
        if text:
            parts.append(f"=== FROM {url} ===\n{text}")
            logger.info(f"Scraped {url}: {len(text)} chars")

    if parts:
        combined = "\n\n".join(parts)
        logger.info(f"Total live knowledge: {len(combined)} chars from {len(parts)} pages")
        return combined

    logger.warning("All scrapes failed, using cached knowledge")
    return KARTA_KNOWLEDGE
