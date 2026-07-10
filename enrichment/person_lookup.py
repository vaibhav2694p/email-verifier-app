import logging
import re
from typing import Optional

from .cache import EnrichmentCache
from .models import CompanyProfile, PersonProfile
from .search_engine import (
    extract_name_from_email,
    extract_phones_from_text,
    extract_social_links,
    extract_text_from_html,
    fetch_page,
)

logger = logging.getLogger(__name__)
_person_cache = EnrichmentCache(default_ttl=86400)


def lookup_person(
    email: str,
    company_profile: Optional[CompanyProfile] = None,
) -> Optional[PersonProfile]:
    """Look up person information from email and public sources."""
    cache_key = EnrichmentCache.make_key("person", email)
    cached = _person_cache.get(cache_key)
    if cached is not None:
        return cached

    local_part = email.split("@")[0] if "@" in email else ""
    domain = email.split("@")[1] if "@" in email else ""

    first_name, last_name = extract_name_from_email(local_part)

    profile = PersonProfile(
        email=email,
        first_name=first_name,
        last_name=last_name,
        full_name=f"{first_name} {last_name}".strip() if first_name else "",
        company_domain=domain,
    )

    if company_profile:
        profile.company_name = company_profile.name
        profile.company_domain = domain

    # Search company website for person
    _search_company_website(profile, domain)

    # Search social profiles
    _search_social_profiles(profile)

    # Calculate confidence
    _calculate_confidence(profile)

    _person_cache.set(cache_key, profile)
    return profile


def _search_company_website(profile: PersonProfile, domain: str):
    """Search company website pages for person info."""
    if not domain or not profile.first_name:
        return

    search_name = profile.first_name.lower()

    for page in ["team", "about", "about-us", "leadership", "staff", "contact"]:
        url = f"https://{domain}/{page}"
        html = fetch_page(url, timeout=8)
        if not html:
            continue

        text = extract_text_from_html(html)
        html_lower = html.lower()

        # Check if name appears on page
        if search_name in html_lower:
            # Try to find full name near the first name mention
            _extract_person_from_page(profile, html, text, domain, page)
            if profile.job_title:
                break  # Found enough info


def _extract_person_from_page(profile: PersonProfile, html: str, text: str, domain: str, page: str):
    """Extract person details from a company page."""
    # Look for name in heading followed by title
    patterns = [
        rf'{re.escape(profile.first_name)}\s+([A-Z][a-z]+)',
        rf'<(?:h[1-4]|strong|b|span)[^>]*>[^<]*{re.escape(profile.first_name)}[^<]*([A-Z][a-z]+)[^<]*</(?:h[1-4]|strong|b|span)>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            last = match.group(1)
            if last.lower() not in ('com', 'org', 'net', 'inc', 'llc', 'ltd', 'co'):
                profile.last_name = last
                profile.full_name = f"{profile.first_name} {last}"
                break

    # Extract job title
    title_patterns = [
        rf'{re.escape(profile.first_name)}[^<]*(?:<[^>]+>)*[^<]*(?:CEO|CTO|CFO|COO|Director|Manager|Engineer|Developer|Founder|President|VP|Lead|Head|Analyst|Designer|Architect|Consultant|Specialist|Coordinator|Officer|Advisor)',
        rf'(?:CEO|CTO|CFO|COO|Director|Manager|Engineer|Developer|Founder|President|VP|Lead|Head|Analyst|Designer|Architect|Consultant|Specialist|Coordinator|Officer|Advisor)[^<]*{re.escape(profile.first_name)}',
    ]
    for pattern in title_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            # Extract the title part
            snippet = match.group(0)
            title_match = re.search(r'(CEO|CTO|CFO|COO|Director|Manager|Engineer|Developer|Founder|President|VP|Lead|Head|Analyst|Designer|Architect|Consultant|Specialist|Coordinator|Officer|Advisor)', snippet, re.IGNORECASE)
            if title_match:
                profile.job_title = title_match.group(1)
                break

    # Social links on this page
    social = extract_social_links(html)
    if "linkedin" in social and not profile.linkedin_url:
        profile.linkedin_url = social["linkedin"]
    if "github" in social and not profile.github_url:
        profile.github_url = social["github"]
    if "twitter" in social and not profile.twitter_url:
        profile.twitter_url = social["twitter"]

    # Location
    phones = extract_phones_from_text(text)
    if phones:
        profile.phone = phones[0]


def _search_social_profiles(profile: PersonProfile):
    """Search for social profiles by name + company."""
    # This is a placeholder - real implementation would use search APIs
    # For now, construct likely profile URLs
    if profile.first_name:
        name_slug = profile.first_name.lower()
        if profile.last_name:
            name_slug = f"{profile.first_name.lower()}-{profile.last_name.lower()}"

        if not profile.linkedin_url and profile.company_name:
            profile.linkedin_url = f"https://linkedin.com/in/{name_slug}"

        if not profile.github_url:
            profile.github_url = f"https://github.com/{profile.first_name.lower()}"


def _calculate_confidence(profile: PersonProfile):
    """Calculate confidence score based on available data."""
    score = 0.0
    reasons = []

    if profile.first_name:
        score += 15
        reasons.append("name_extracted")
    if profile.last_name:
        score += 10
        reasons.append("full_name")
    if profile.job_title:
        score += 15
        reasons.append("job_title")
    if profile.company_name:
        score += 15
        reasons.append("company_match")
    if profile.linkedin_url:
        score += 20
        reasons.append("linkedin")
    if profile.github_url:
        score += 5
        reasons.append("github")
    if profile.twitter_url:
        score += 5
        reasons.append("twitter")
    if profile.phone:
        score += 5
        reasons.append("phone")
    if profile.country:
        score += 5
        reasons.append("location")

    profile.confidence = min(score, 100.0)

    if score >= 60:
        profile.confidence_level = "High"
    elif score >= 35:
        profile.confidence_level = "Medium"
    elif score > 0:
        profile.confidence_level = "Low"
    else:
        profile.confidence_level = "Unknown"
        profile.notes = "No public information found"
