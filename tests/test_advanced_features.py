import io

import pandas as pd

from services.bulk_processor import BulkProcessor
from services.email_finder import generate_email_patterns
from services.input_service import detect_email_column, parse_manual_paste, parse_upload, validate_dataframe
from services.webhook_service import sign_payload, verify_signature
from verifier.abuse_detector import detect_abuse_address
from verifier.classifier import classify_result
from verifier.config import VerifierConfig
from verifier.greylist_handler import apply_greylist_analysis
from verifier.models import VerificationResult
from verifier.spamtrap_risk import assess_spam_trap_risk
from verifier.toxic_risk import assess_toxic_risk


def test_abuse_detector_flags_abuse_mailbox():
    is_abuse, category, do_not_mail, reason = detect_abuse_address("abuse@example.com")
    assert is_abuse is True
    assert category == "Abuse Reporting"
    assert do_not_mail is True
    assert "abuse" in reason


def test_greylist_handler_marks_retry_required():
    result = VerificationResult(smtp_attempted=True, smtp_status="temporary_failure", smtp_code=450, smtp_message="Greylisted, try again later")
    apply_greylist_analysis(result)
    assert result.greylisting_detected is True
    assert result.retry_required is True
    assert result.temporary_failure is True


def test_spamtrap_risk_is_not_confirmed_without_dataset():
    result = VerificationResult(local_part="spamtrap", role_based=True, disposable=True)
    risk, signals, source, confidence, confirmed = assess_spam_trap_risk(result)
    assert risk in {"Medium", "High"}
    assert signals
    assert source == "heuristic"
    assert confidence in {"Low", "Medium"}
    assert confirmed is False


def test_toxic_risk_uses_observed_signals():
    result = VerificationResult(disposable=True, abuse_address=True, smtp_status="rejected", mailbox_rejected=True)
    risk, signals, source, confidence, fraud = assess_toxic_risk(result)
    assert risk == "High"
    assert "Disposable domain" in signals
    assert source == "heuristic"
    assert fraud == "Unknown"


def test_classifier_keeps_unknown_separate_from_invalid():
    result = VerificationResult(syntax_valid=True, domain="example.com", mx_records="[(\"mx.example.com\", 10)]", verification_score=45)
    classify_result(result)
    assert result.verification_status == "Unknown"
    assert result.recommended_action == "Manual Review"


def test_classifier_marks_disposable_do_not_send():
    result = VerificationResult(syntax_valid=True, domain="mailinator.com", mx_records="x", disposable=True, verification_score=10)
    classify_result(result)
    assert result.verification_status == "Disposable"
    assert result.recommended_action == "Do Not Send"
    assert result.do_not_mail is True


def test_txt_parsing_supports_multiple_delimiters():
    df = parse_manual_paste("a@example.com,b@example.com;c@example.com\td@example.com\n")
    assert df["Email"].tolist() == ["a@example.com", "b@example.com", "c@example.com", "d@example.com"]


def test_parse_upload_txt():
    parsed = parse_upload(io.BytesIO(b"a@example.com\nb@example.com"), "emails.txt")
    assert parsed.dataframe.shape[0] == 2


def test_validate_dataframe_duplicate_columns():
    df = pd.DataFrame([[1, 2]], columns=["Email", "Email"])
    try:
        validate_dataframe(df)
    except ValueError as exc:
        assert "Duplicate" in str(exc)
    else:
        raise AssertionError("Expected duplicate column validation error")


def test_detect_email_column_by_name_and_sample():
    assert detect_email_column(pd.DataFrame({"Email": ["a@example.com"]})) == "Email"
    assert detect_email_column(pd.DataFrame({"Contact": ["a@example.com"]})) == "Contact"


def test_webhook_signature_round_trip():
    payload = {"event": "verification.completed", "job_id": "job_123"}
    sig = sign_payload(payload, "secret")
    assert verify_signature(payload, "secret", sig)
    assert not verify_signature(payload, "wrong", sig)


def test_email_finder_patterns():
    patterns = generate_email_patterns("John", "Doe", "example.com")
    emails = {p["email"] for p in patterns}
    assert "john@example.com" in emails
    assert "john.doe@example.com" in emails
    assert "jdoe@example.com" in emails


def test_bulk_duplicate_status_preserved(monkeypatch):
    def fake_verify(email, company_domain=None):
        return VerificationResult(original_email=email, normalized_email=email.lower(), syntax_valid=True, verification_status="Likely Valid", verification_score=70)

    processor = BulkProcessor(config=VerifierConfig())
    monkeypatch.setattr(processor.pipeline, "verify", fake_verify)
    result = processor.process(pd.DataFrame({"Email": ["A@example.com", "a@example.com"]}), "Email")
    assert result.loc[1, "is_duplicate"] is True or result.loc[1, "is_duplicate"] == True
    assert result.loc[1, "verification_status"] == "Duplicate"
    assert result.loc[1, "duplicate_of"] == "A@example.com"
