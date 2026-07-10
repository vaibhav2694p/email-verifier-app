import pytest
from verifier.typo_detector import detect_typo, get_suggestion_confidence

class TestTypoDetector:
    def test_gmail_typo_gmial(self):
        result = detect_typo("gmial.com")
        assert result.is_possible_typo is True
        assert result.suggested_domain == "gmail.com"
    
    def test_gmail_typo_gmai(self):
        result = detect_typo("gmai.com")
        assert result.is_possible_typo is True
        assert result.suggested_domain == "gmail.com"
    
    def test_yahoo_typo_yaho(self):
        result = detect_typo("yaho.com")
        assert result.is_possible_typo is True
        assert result.suggested_domain == "yahoo.com"
    
    def test_outlook_typo(self):
        result = detect_typo("outlok.com")
        assert result.is_possible_typo is True
        assert result.suggested_domain == "outlook.com"
    
    def test_hotmail_typo(self):
        result = detect_typo("hotmial.com")
        assert result.is_possible_typo is True
        assert result.suggested_domain == "hotmail.com"
    
    def test_no_typo(self):
        result = detect_typo("gmail.com")
        assert result.is_possible_typo is False
    
    def test_unknown_domain(self):
        result = detect_typo("xyzzyunknown12345.com")
        assert result.is_possible_typo is False
    
    def test_confidence_high(self):
        conf = get_suggestion_confidence("gmial.com", "gmail.com")
        assert conf > 0.7
    
    def test_confidence_low(self):
        conf = get_suggestion_confidence("abc.com", "gmail.com")
        assert conf < 0.7
