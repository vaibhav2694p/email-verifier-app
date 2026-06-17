from __future__ import annotations

from urllib.parse import quote_plus


def build_linkedin_search_query(
    name: str,
    company: str,
    scope: str = "profiles",
) -> str:
    site = "site:linkedin.com/in" if scope == "profiles" else "site:linkedin.com"
    quoted_terms = [f'"{term}"' for term in (name.strip(), company.strip()) if term]
    if not quoted_terms:
        return ""
    return " ".join([site, *quoted_terms])


def build_linkedin_search_url(
    name: str,
    company: str,
    scope: str = "profiles",
) -> str:
    query = build_linkedin_search_query(name, company, scope)
    if not query:
        return ""
    return f"https://www.google.com/search?q={quote_plus(query)}"
