from typing import Optional

from .models import CompanyProfile, PersonProfile


def generate_summary(
    person: Optional[PersonProfile],
    company: Optional[CompanyProfile],
) -> str:
    """Generate a concise text summary of the enriched data."""
    parts = []

    if person and person.full_name:
        name = person.full_name
        parts.append(f"{name} appears to be associated with {person.company_domain or 'this domain'}.")

        if person.job_title:
            parts.append(f"Public information suggests a {person.job_title.lower()} role.")

        if company and company.name:
            parts.append(f"The company is {company.name}.")
            if company.description:
                desc = company.description[:200]
                parts.append(f"They describe themselves as: \"{desc}\"")

        if person.linkedin_url:
            parts.append(f"A LinkedIn profile was found: {person.linkedin_url}.")

        if person.github_url:
            parts.append(f"A GitHub profile was found: {person.github_url}.")

        # Confidence assessment
        if person.confidence_level == "High":
            parts.append("Confidence: High. Multiple public sources are consistent.")
        elif person.confidence_level == "Medium":
            parts.append("Confidence: Medium. Some public information found, but not fully verified.")
        elif person.confidence_level == "Low":
            parts.append("Confidence: Low. Limited public information available.")
        else:
            parts.append("Confidence: Unknown. No reliable public information could be found.")
            parts.append("The email exists but the person's identity could not be confirmed from public sources.")

    elif company:
        parts.append(f"The domain {company.domain} belongs to {company.name or 'a company'}.")
        if company.description:
            parts.append(f"They describe themselves as: \"{company.description[:200]}\"")
        parts.append("No individual person could be identified from public sources.")

    else:
        parts.append("No reliable public information was found for this email address.")
        parts.append("This does not mean the email is invalid, only that public enrichment data is unavailable.")

    return " ".join(parts)
