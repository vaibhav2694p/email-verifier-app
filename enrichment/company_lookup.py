import logging
import re
from typing import Dict, List, Optional

from .cache import EnrichmentCache
from .models import CompanyProfile
from .search_engine import extract_social_links, extract_text_from_html, fetch_page, find_logo_url

logger = logging.getLogger(__name__)
_company_cache = EnrichmentCache(default_ttl=86400)

COMPANY_PAGES = [
    "", "about", "about-us", "team", "leadership", "staff",
    "contact", "contact-us", "blog", "careers", "jobs", "news",
]


def lookup_company(domain: str, company_name: str = "") -> Optional[CompanyProfile]:
    """Look up company information from their website."""
    cache_key = EnrichmentCache.make_key("company", domain)
    cached = _company_cache.get(cache_key)
    if cached is not None:
        return cached

    profile = CompanyProfile(domain=domain, name=company_name)

    # Fetch homepage
    home_html = _fetch_page_safe(f"https://{domain}")
    if not home_html:
        home_html = _fetch_page_safe(f"http://{domain}")

    if home_html:
        _extract_homepage_info(profile, home_html, domain)

        # Find logo
        profile.logo_url = find_logo_url(domain, home_html)

        # Get social links from homepage
        social = extract_social_links(home_html)
        if "linkedin" in social:
            profile.linkedin_url = social["linkedin"]
        if "crunchbase" in social:
            profile.crunchbase_url = social["crunchbase"]

    # Scan about/team/contact pages
    _scan_company_pages(profile, domain)

    # Look up WHOIS
    try:
        from .whois_lookup import lookup_whois
        whois = lookup_whois(domain)
        if whois:
            profile.domain_age = whois.get("age", "")
            profile.domain_registrar = whois.get("registrar", "")
    except Exception:
        pass

    _company_cache.set(cache_key, profile)
    return profile


def _fetch_page_safe(url: str) -> Optional[str]:
    try:
        return fetch_page(url, timeout=8)
    except Exception:
        return None


def _extract_homepage_info(profile: CompanyProfile, html: str, domain: str):
    text = extract_text_from_html(html)

    # Description from meta
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if desc_match:
        profile.description = desc_match.group(1)[:500]

    # OG description fallback
    if not profile.description:
        og_match = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_match:
            profile.description = og_match.group(1)[:500]

    # Title for company name
    if not profile.name:
        title_match = re.search(r'<title>([^<|>-]+)', html, re.IGNORECASE)
        if title_match:
            profile.name = title_match.group(1).strip()[:100]

    # Phone
    phones = re.findall(r'\+?\d[\d\s\-().]{7,}\d', text)
    if phones:
        profile.phone = phones[0].strip()[:30]

    # Email
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    # Filter out common non-company emails
    company_emails = [e for e in emails if not any(x in e.lower() for x in ['noreply', 'no-reply', 'example.com', 'test.'])]
    if company_emails:
        profile.email = company_emails[0]

    # Country/city from text patterns
    _extract_location(profile, text)


def _extract_location(profile: CompanyProfile, text: str):
    """Try to extract location from page text."""
    # Look for common patterns
    location_patterns = [
        r'(?:located in|headquarters|based in|office in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*([A-Z][a-z]+)',
        r'(?:address|location)[:\s]+([^,\n]+,\s*[A-Z][a-z]+)',
    ]
    for pattern in location_patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                profile.city = groups[0].strip()
                profile.country = groups[1].strip()
            elif len(groups) == 1:
                parts = groups[0].split(",")
                if len(parts) >= 2:
                    profile.city = parts[0].strip()
                    profile.country = parts[1].strip()
            break


def _scan_company_pages(profile: CompanyProfile, domain: str):
    """Scan common company pages for additional info."""
    for page in ["about", "about-us", "team", "contact"]:
        url = f"https://{domain}/{page}"
        html = _fetch_page_safe(url)
        if not html:
            continue

        text = extract_text_from_html(html)
        social = extract_social_links(html)

        if "linkedin" in social and not profile.linkedin_url:
            profile.linkedin_url = social["linkedin"]
        if "crunchbase" in social and not profile.crunchbase_url:
            profile.crunchbase_url = social["crunchbase"]

        # Extract employee names from team pages
        if page in ("team", "leadership", "about", "about-us"):
            _extract_employee_names(profile, text, html)

        # Better location from contact page
        if page == "contact" and not profile.city:
            _extract_location(profile, text)


def _extract_employee_names(profile: CompanyProfile, text: str, html: str):
    """Extract likely employee names from team/about pages."""
    # Look for names near job titles
    name_patterns = [
        r'<h[23][^>]*>([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)</h[23]>',
        r'class="[^"]*(?:name|team-member|person)[^"]*"[^>]*>([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    for pattern in name_patterns:
        matches = re.findall(pattern, html)
        for name in matches:
            name = name.strip()
            if len(name) > 4 and len(name) < 60 and name not in profile.employees:
                profile.employees.append(name)

    profile.employees = profile.employees[:50]  # limit


def batch_lookup_companies(domains: List[str]) -> Dict[str, CompanyProfile]:
    """Look up multiple companies, deduplicating by domain."""
    results = {}
    for domain in set(domains):
        if domain:
            results[domain] = lookup_company(domain)
    return results
