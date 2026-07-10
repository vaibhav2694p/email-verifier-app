from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PersonProfile:
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    job_title: str = ""
    department: str = ""
    company_name: str = ""
    company_domain: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    twitter_url: str = ""
    facebook_url: str = ""
    instagram_url: str = ""
    country: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    confidence: float = 0.0
    confidence_level: str = "Unknown"  # High/Medium/Low/Unknown
    sources: List[str] = field(default_factory=list)
    notes: str = ""

@dataclass
class CompanyProfile:
    name: str = ""
    domain: str = ""
    website: str = ""
    description: str = ""
    industry: str = ""
    linkedin_url: str = ""
    crunchbase_url: str = ""
    logo_url: str = ""
    country: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    founded: str = ""
    employee_count: str = ""
    domain_age: str = ""
    domain_registrar: str = ""
    employees: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)

@dataclass
class EnrichmentResult:
    email: str = ""
    person: Optional[PersonProfile] = None
    company: Optional[CompanyProfile] = None
    ai_summary: str = ""
    processing_time_ms: float = 0.0
    enriched: bool = False
