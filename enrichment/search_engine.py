import logging
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import requests

logger = logging.getLogger(__name__)

# Global cache for search results
_search_cache = {}

def generate_search_queries(
    email: str,
    local_part: str,
    domain: str,
    first_name: str = "",
    last_name: str = "",
    company_name: str = "",
) -> List[Dict[str, str]]:
    """Generate search queries for email intelligence."""
    queries = []

    # Email-based
    queries.append({"query": f'"{email}"', "purpose": "email_exact"})
    queries.append({"query": f'"{local_part} {domain}"', "purpose": "name_domain"})

    if first_name and last_name:
        queries.append({"query": f'"{first_name} {last_name} {domain}"', "purpose": "full_name_domain"})

    # Site-specific
    queries.append({"query": f'site:{domain} {local_part}', "purpose": "company_site"})
    queries.append({"query": f'site:linkedin.com "{first_name}" "{company_name or domain}"', "purpose": "linkedin"})
    queries.append({"query": f'site:github.com {local_part} {domain}', "purpose": "github"})
    queries.append({"query": f'site:x.com {local_part} {domain}', "purpose": "twitter"})
    queries.append({"query": f'site:facebook.com {local_part} {domain}', "purpose": "facebook"})
    queries.append({"query": f'site:instagram.com {local_part} {domain}', "purpose": "instagram"})

    return queries


def extract_name_from_email(local_part: str) -> tuple:
    """Try to extract first/last name from email local part."""
    # common patterns: firstname.lastname, firstname_lastname, firstnamelastname
    separators = [".", "_", "-"]
    for sep in separators:
        if sep in local_part:
            parts = local_part.split(sep)
            if len(parts) == 2 and all(p.isalpha() for p in parts):
                return parts[0].capitalize(), parts[1].capitalize()

    # Single word - might be first name only
    if local_part.isalpha() and len(local_part) > 2:
        return local_part.capitalize(), ""

    return "", ""


def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch a web page and return text content. Returns None on failure."""
    cache_key = f"page:{url}"
    if cache_key in _search_cache:
        return _search_cache[cache_key]

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; EmailVerifier/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        text = resp.text[:500000]  # limit to 500KB
        _search_cache[cache_key] = text
        return text
    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url, e)
        return None


def extract_text_from_html(html: str) -> str:
    """Basic HTML to text extraction."""
    # Remove scripts and styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_emails_from_text(text: str) -> List[str]:
    """Extract email addresses from text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text.lower())))


def extract_social_links(html: str) -> Dict[str, str]:
    """Extract social media links from HTML."""
    links = {}
    patterns = {
        "linkedin": r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_-]+/?',
        "github": r'https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?',
        "twitter": r'https?://(?:www\.)?(?:x\.com|twitter\.com)/[a-zA-Z0-9_-]+/?',
        "facebook": r'https?://(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+/?',
        "instagram": r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._-]+/?',
        "crunchbase": r'https?://(?:www\.)?crunchbase\.com/(?:organization|company)/[a-zA-Z0-9_-]+/?',
    }
    for platform, pattern in patterns.items():
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            links[platform] = matches[0]
    return links


def extract_phones_from_text(text: str) -> List[str]:
    """Extract phone numbers from text."""
    patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
    ]
    phones = []
    for p in patterns:
        phones.extend(re.findall(p, text))
    return list(set(phones))[:3]  # max 3


LOGO_CACHE = {}

def find_logo_url(domain: str, html: str = None) -> str:
    """Try to find company logo URL from HTML or common paths."""
    if domain in LOGO_CACHE:
        return LOGO_CACHE[domain]

    if html:
        # Look for og:image or common logo patterns
        og_match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_match:
            url = og_match.group(1)
            LOGO_CACHE[domain] = url
            return url

        logo_match = re.search(r'<img[^>]*(?:alt|title)=["\'][^"\']*(?:logo|brand)[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if logo_match:
            url = logo_match.group(1)
            if not url.startswith("http"):
                url = f"https://{domain}{url}"
            LOGO_CACHE[domain] = url
            return url

    # Try common paths
    for path in ["/logo.png", "/logo.svg", "/favicon.ico", "/assets/logo.png", "/images/logo.png"]:
        url = f"https://{domain}{path}"
        try:
            resp = requests.head(url, timeout=3, allow_redirects=True)
            if resp.status_code == 200:
                LOGO_CACHE[domain] = url
                return url
        except Exception:
            pass

    LOGO_CACHE[domain] = ""
    return ""
