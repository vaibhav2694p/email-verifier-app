from verifier.config import VerifierConfig
from verifier.models import VerificationResult
from verifier.pipeline import VerificationPipeline


class TestVerificationPipeline:
    def test_valid_corporate_email(self):
        config = VerifierConfig(enable_smtp_check=False)
        pipeline = VerificationPipeline(config)
        result = pipeline.verify("user@example.com")
        assert isinstance(result, VerificationResult)
        assert result.original_email == "user@example.com"
        assert result.syntax_valid is True
        assert result.domain == "example.com"

    def test_invalid_syntax(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("not-an-email")
        assert result.syntax_valid is False
        assert result.verification_score == 0

    def test_empty_email(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("")
        assert result.verification_score == 0

    def test_disposable_email(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("user@mailinator.com")
        assert result.disposable is True

    def test_public_email(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("user@gmail.com")
        assert result.free_public_email is True

    def test_role_email(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("info@example.com")
        assert result.role_based is True

    def test_with_company_domain_match(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("user@example.com", company_domain="example.com")
        assert result.company_domain_match is True

    def test_with_company_domain_mismatch(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("user@example.com", company_domain="other.com")
        assert result.company_domain_match is False

    def test_has_stage_results(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("user@example.com")
        assert len(result.stage_results) > 0

    def test_has_score_reasons(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("user@example.com")
        assert len(result.score_reasons) > 0

    def test_processing_time_recorded(self):
        pipeline = VerificationPipeline()
        result = pipeline.verify("user@example.com")
        assert result.processing_time_ms >= 0

    def test_smtp_disabled_by_default(self):
        config = VerifierConfig(enable_smtp_check=False)
        pipeline = VerificationPipeline(config)
        result = pipeline.verify("user@example.com")
        assert result.smtp_attempted is False
