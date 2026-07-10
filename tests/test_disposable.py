import pytest
from verifier.disposable import is_disposable, load_disposable_domains

class TestDisposableDetection:
    def test_known_disposable(self):
        assert is_disposable("mailinator.com") is True
    
    def test_guerrilla_mail(self):
        assert is_disposable("guerrillamail.com") is True
    
    def test_temp_mail(self):
        assert is_disposable("temp-mail.org") is True
    
    def test_legitimate_domain(self):
        assert is_disposable("gmail.com") is False
    
    def test_legitimate_corporate(self):
        assert is_disposable("microsoft.com") is False
    
    def test_subdomain_disposable(self):
        assert is_disposable("sub.mailinator.com") is True
    
    def test_loads_builtins(self):
        domains = load_disposable_domains()
        assert len(domains) > 40
        assert "mailinator.com" in domains
