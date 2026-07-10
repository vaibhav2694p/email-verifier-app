from verifier.models import ConfidenceLevel, RiskLevel, VerificationResult, VerificationStatus
from verifier.scoring import calculate_verification_score


class TestScoring:
    def _make_result(self, **kwargs):
        defaults = {
            "original_email": "user@example.com",
            "normalized_email": "user@example.com",
            "local_part": "user",
            "domain": "example.com",
            "syntax_valid": True,
            "dns_status": "Resolved",
            "mx_status": "Resolved",
            "mx_records": "mx.test.com",
            "disposable": False,
            "free_public_email": False,
            "role_based": False,
            "company_domain_match": None,
            "smtp_attempted": False,
            "catch_all": "Not Tested",
            "domain_active": True,
            "website_status": "Active",
        }
        defaults.update(kwargs)
        return VerificationResult(**defaults)

    def test_high_score_valid_corporate(self):
        result = self._make_result(
            company_domain_match=True,
            smtp_attempted=True,
            smtp_status="accepted",
        )
        result = calculate_verification_score(result)
        assert result.verification_score >= 70
        assert result.verification_status in [VerificationStatus.VALID.value, VerificationStatus.LIKELY_VALID.value]

    def test_disposable_capped(self):
        result = self._make_result(disposable=True)
        result = calculate_verification_score(result)
        assert result.verification_score <= 15

    def test_syntax_invalid_max_zero(self):
        result = self._make_result(syntax_valid=False, domain="")
        result = calculate_verification_score(result)
        assert result.verification_score == 0

    def test_no_mx_capped(self):
        result = self._make_result(
            mx_status="No MX Found", dns_status="NXDomain"
        )
        result = calculate_verification_score(result)
        assert result.verification_score <= 20

    def test_role_based_penalty(self):
        result1 = self._make_result(role_based=False)
        result1 = calculate_verification_score(result1)
        result2 = self._make_result(role_based=True, role_category="contact")
        result2 = calculate_verification_score(result2)
        assert result2.verification_score < result1.verification_score

    def test_score_has_reasons(self):
        result = self._make_result()
        result = calculate_verification_score(result)
        assert len(result.score_reasons) > 0

    def test_score_has_confidence(self):
        result = self._make_result()
        result = calculate_verification_score(result)
        assert result.confidence_level in [c.value for c in ConfidenceLevel]

    def test_score_has_risk(self):
        result = self._make_result()
        result = calculate_verification_score(result)
        assert result.risk_level in [r.value for r in RiskLevel]

    def test_smtp_accepted_increases_score(self):
        r1 = self._make_result(smtp_attempted=False)
        r1 = calculate_verification_score(r1)
        r2 = self._make_result(smtp_attempted=True, smtp_status="accepted")
        r2 = calculate_verification_score(r2)
        assert r2.verification_score > r1.verification_score

    def test_company_mismatch_penalty(self):
        r1 = self._make_result(company_domain_match=None)
        r1 = calculate_verification_score(r1)
        r2 = self._make_result(company_domain_match=False)
        r2 = calculate_verification_score(r2)
        assert r2.verification_score < r1.verification_score
