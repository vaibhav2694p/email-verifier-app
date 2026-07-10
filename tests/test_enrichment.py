from unittest.mock import patch

from enrichment.cache import EnrichmentCache
from enrichment.company_lookup import lookup_company
from enrichment.models import CompanyProfile, EnrichmentResult, PersonProfile
from enrichment.person_lookup import lookup_person
from enrichment.profile_matcher import build_company_summary, match_profiles
from enrichment.search_engine import (
    extract_emails_from_text,
    extract_name_from_email,
    extract_phones_from_text,
    extract_social_links,
    extract_text_from_html,
    generate_search_queries,
)
from enrichment.summary import generate_summary


class TestEnrichmentModels:
    def test_person_profile_defaults(self):
        p = PersonProfile()
        assert p.first_name == ""
        assert p.confidence == 0.0
        assert p.confidence_level == "Unknown"
        assert p.sources == []

    def test_company_profile_defaults(self):
        c = CompanyProfile()
        assert c.name == ""
        assert c.employees == []

    def test_enrichment_result_defaults(self):
        r = EnrichmentResult()
        assert r.enriched is False
        assert r.person is None
        assert r.company is None


class TestEnrichmentCache:
    def test_set_and_get(self):
        cache = EnrichmentCache(default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = EnrichmentCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        cache = EnrichmentCache()
        cache.set("key", "val", ttl=-1)
        assert cache.get("key") is None

    def test_get_or_set(self):
        cache = EnrichmentCache()
        val = cache.get_or_set("k", lambda: "computed")
        assert val == "computed"
        assert cache.get("k") == "computed"

    def test_make_key(self):
        k1 = EnrichmentCache.make_key("a", "b")
        k2 = EnrichmentCache.make_key("a", "b")
        k3 = EnrichmentCache.make_key("a", "c")
        assert k1 == k2
        assert k1 != k3

    def test_stats(self):
        cache = EnrichmentCache()
        cache.set("a", 1)
        stats = cache.stats()
        assert stats["total"] == 1
        assert stats["valid"] == 1

    def test_clear(self):
        cache = EnrichmentCache()
        cache.set("a", 1)
        cache.clear()
        assert cache.get("a") is None

    def test_max_size_eviction(self):
        cache = EnrichmentCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)
        assert cache.stats()["total"] <= 3


class TestSearchEngine:
    def test_extract_name_firstname_lastname(self):
        first, last = extract_name_from_email("john.smith")
        assert first == "John"
        assert last == "Smith"

    def test_extract_name_underscore(self):
        first, last = extract_name_from_email("john_smith")
        assert first == "John"
        assert last == "Smith"

    def test_extract_name_single_word(self):
        first, last = extract_name_from_email("vaibhav")
        assert first == "Vaibhav"
        assert last == ""

    def test_extract_name_numeric(self):
        first, last = extract_name_from_email("user123")
        assert first == ""
        assert last == ""

    def test_generate_search_queries(self):
        queries = generate_search_queries(
            "john@acme.com", "john", "acme.com", "John", "Doe", "Acme Corp"
        )
        assert len(queries) >= 5
        purposes = [q["purpose"] for q in queries]
        assert "email_exact" in purposes
        assert "linkedin" in purposes

    def test_extract_social_links(self):
        html = '<a href="https://linkedin.com/in/john-doe">LinkedIn</a><a href="https://github.com/john">GH</a>'
        links = extract_social_links(html)
        assert "linkedin" in links
        assert "github" in links

    def test_extract_phones(self):
        text = "Call us at +1-555-123-4567 or (555) 987-6543"
        phones = extract_phones_from_text(text)
        assert len(phones) >= 1

    def test_extract_emails_from_text(self):
        text = "Contact admin@example.com or support@test.org"
        emails = extract_emails_from_text(text)
        assert "admin@example.com" in emails
        assert "support@test.org" in emails

    def test_extract_text_from_html(self):
        html = "<html><body><p>Hello World</p></body></html>"
        text = extract_text_from_html(html)
        assert "Hello World" in text
        assert "<" not in text


class TestSummary:
    def test_summary_with_person(self):
        person = PersonProfile(
            first_name="John", last_name="Doe", full_name="John Doe",
            job_title="CEO", company_name="Acme", company_domain="acme.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            confidence_level="High", confidence=85,
        )
        company = CompanyProfile(name="Acme Corp", domain="acme.com")
        summary = generate_summary(person, company)
        assert "John Doe" in summary
        assert "Acme" in summary
        assert "High" in summary

    def test_summary_no_info(self):
        summary = generate_summary(None, None)
        assert "No reliable" in summary

    def test_summary_company_only(self):
        company = CompanyProfile(name="Acme", domain="acme.com", description="Tech company")
        summary = generate_summary(None, company)
        assert "Acme" in summary


class TestProfileMatcher:
    def test_match_profiles_ranks_by_confidence(self):
        p1 = PersonProfile(full_name="John Doe", linkedin_url="https://linkedin.com/in/john",
                          company_domain="acme.com", confidence=80)
        p2 = PersonProfile(full_name="Jane Smith", confidence=20)
        ranked = match_profiles("john@acme.com", [p2, p1])
        assert ranked[0].confidence >= ranked[1].confidence

    def test_build_company_summary(self):
        company = CompanyProfile(name="Acme", domain="acme.com", description="Tech")
        people = [
            PersonProfile(full_name="John", email="john@acme.com", company_domain="acme.com"),
            PersonProfile(full_name="Jane", email="jane@acme.com", company_domain="acme.com"),
        ]
        summary = build_company_summary(company, people)
        assert summary["company_name"] == "Acme"
        assert summary["employee_count"] == 2

    def test_build_company_summary_empty(self):
        assert build_company_summary(None, []) == {}


class TestCompanyLookup:
    @patch('enrichment.company_lookup.fetch_page')
    def test_lookup_company_returns_profile(self, mock_fetch):
        mock_fetch.return_value = '<html><head><meta name="description" content="Acme Corp - Tech company"></head><body></body></html>'
        profile = lookup_company("acme.com")
        assert profile is not None
        assert profile.domain == "acme.com"

    @patch('enrichment.company_lookup.fetch_page')
    def test_lookup_company_no_website(self, mock_fetch):
        mock_fetch.return_value = None
        profile = lookup_company("nonexistent12345.com")
        assert profile is not None
        assert profile.domain == "nonexistent12345.com"


class TestPersonLookup:
    @patch('enrichment.person_lookup.fetch_page')
    def test_lookup_person_from_email(self, mock_fetch):
        mock_fetch.return_value = None
        person = lookup_person("john.smith@example.com")
        assert person is not None
        assert person.first_name == "John"
        assert person.last_name == "Smith"

    @patch('enrichment.person_lookup.fetch_page')
    def test_lookup_person_unknown_domain(self, mock_fetch):
        mock_fetch.return_value = None
        person = lookup_person("test@unknown12345.com")
        assert person is not None
        assert person.confidence_level in ("Low", "Unknown")
