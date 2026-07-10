import logging
from typing import List, Optional, Dict
from .models import PersonProfile, CompanyProfile
from .cache import EnrichmentCache

logger = logging.getLogger(__name__)


def match_profiles(
    email: str,
    candidates: List[PersonProfile],
    company_profile: Optional[CompanyProfile] = None,
) -> List[PersonProfile]:
    """Rank profile candidates by confidence. Returns sorted list (best first)."""
    if not candidates:
        return []
    
    domain = email.split("@")[1] if "@" in email else ""
    local_part = email.split("@")[0] if "@" in email else ""
    
    scored = []
    for candidate in candidates:
        score = _score_match(email, local_part, domain, candidate, company_profile)
        candidate.confidence = score
        if score >= 60:
            candidate.confidence_level = "High"
        elif score >= 35:
            candidate.confidence_level = "Medium"
        elif score > 0:
            candidate.confidence_level = "Low"
        else:
            candidate.confidence_level = "Unknown"
        scored.append(candidate)
    
    scored.sort(key=lambda p: p.confidence, reverse=True)
    return scored


def _score_match(
    email: str,
    local_part: str,
    domain: str,
    candidate: PersonProfile,
    company_profile: Optional[CompanyProfile],
) -> float:
    score = 0.0
    
    # Company domain match
    if company_profile and candidate.company_domain == domain:
        score += 30
    elif candidate.company_domain == domain:
        score += 20
    
    # Company name match
    if company_profile and candidate.company_name:
        if company_profile.name.lower() in candidate.company_name.lower():
            score += 15
    
    # Name from email matches
    if candidate.first_name and local_part:
        if candidate.first_name.lower() in local_part.lower():
            score += 20
        elif local_part.lower() in candidate.first_name.lower():
            score += 10
    
    # Has LinkedIn
    if candidate.linkedin_url:
        score += 15
    
    # Has job title
    if candidate.job_title:
        score += 10
    
    # Has full name
    if candidate.full_name and len(candidate.full_name) > 3:
        score += 10
    
    return min(score, 100.0)


def build_company_summary(
    company_profile: Optional[CompanyProfile],
    people: List[PersonProfile],
) -> Dict:
    """Build a company intelligence summary from multiple people."""
    if not company_profile:
        return {}
    
    employees = []
    for p in people:
        if p.company_name or p.company_domain == company_profile.domain:
            employees.append({
                "name": p.full_name or p.first_name,
                "email": p.email,
                "job_title": p.job_title,
                "confidence": p.confidence_level,
            })
    
    return {
        "company_name": company_profile.name,
        "domain": company_profile.domain,
        "website": company_profile.website or f"https://{company_profile.domain}",
        "description": company_profile.description,
        "industry": company_profile.industry,
        "linkedin": company_profile.linkedin_url,
        "logo": company_profile.logo_url,
        "country": company_profile.country,
        "city": company_profile.city,
        "phone": company_profile.phone,
        "email": company_profile.email,
        "domain_age": company_profile.domain_age,
        "registrar": company_profile.domain_registrar,
        "employee_count": len(employees),
        "employees": employees,
    }
