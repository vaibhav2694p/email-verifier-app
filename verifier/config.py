import os
from dataclasses import dataclass


@dataclass
class VerifierConfig:
    verifier_email: str = ""
    verifier_domain: str = ""
    enable_smtp_check: bool = False
    smtp_port: int = 25
    smtp_connection_timeout: int = 5
    smtp_response_timeout: int = 5
    smtp_max_attempts: int = 2
    max_workers: int = 10
    batch_size: int = 100
    dns_timeout: int = 5
    dns_cache_ttl: int = 3600
    smtp_cache_ttl: int = 1800
    catch_all_cache_ttl: int = 86400
    custom_dns_server: str = ""
    log_level: str = "INFO"
    max_upload_size_mb: int = 50
    max_rows: int = 100000
    max_concurrent_smtp: int = 5
    per_domain_smtp_rate_limit: int = 10
    max_retries: int = 2
    request_timeout: int = 30

    # Test mode / local SMTP server
    smtp_test_mode: bool = False
    test_smtp_host: str = "localhost"
    test_smtp_port: int = 1025
    test_smtp_use_tls: bool = False
    test_smtp_username: str = ""
    test_smtp_password: str = ""
    smtp_verification_mode: str = "disabled"  # disabled | test | real
    domain_rate_limit: int = 2

    # Notification SMTP
    notification_smtp_enabled: bool = False
    notification_smtp_host: str = ""
    notification_smtp_port: int = 587
    notification_smtp_username: str = ""
    notification_smtp_password: str = ""
    notification_smtp_use_tls: bool = True
    notification_from_email: str = ""
    notification_to_email: str = ""
    mailpit_web_url: str = "http://localhost:8025"

    # Domain health / reputation
    enable_blacklist_check: bool = False
    enable_domain_monitoring: bool = False
    enable_ai_scoring: bool = False
    blacklist_dnsbl_providers: str = "zen.spamhaus.org,bl.spamcop.net"
    dkim_selectors: str = "default,selector1,selector2,google,k1"

    # API / persistence / privacy
    api_enabled: bool = True
    api_key: str = ""
    webhook_secret: str = ""
    database_url: str = "sqlite:///email_verifier.db"
    data_retention_days: int = 30

    @classmethod
    def from_env(cls) -> "VerifierConfig":
        return cls(
            verifier_email=os.getenv("VERIFIER_EMAIL", ""),
            verifier_domain=os.getenv("VERIFIER_DOMAIN", ""),
            enable_smtp_check=os.getenv("ENABLE_SMTP_CHECK", "false").lower() == "true",
            smtp_port=int(os.getenv("SMTP_PORT", "25")),
            smtp_connection_timeout=int(os.getenv("SMTP_CONNECTION_TIMEOUT", "5")),
            smtp_response_timeout=int(os.getenv("SMTP_RESPONSE_TIMEOUT", "5")),
            smtp_max_attempts=int(os.getenv("SMTP_MAX_ATTEMPTS", "2")),
            max_workers=int(os.getenv("MAX_WORKERS", "10")),
            batch_size=int(os.getenv("BATCH_SIZE", "100")),
            dns_timeout=int(os.getenv("DNS_TIMEOUT", "5")),
            dns_cache_ttl=int(os.getenv("DNS_CACHE_TTL", "3600")),
            smtp_cache_ttl=int(os.getenv("SMTP_CACHE_TTL", "1800")),
            catch_all_cache_ttl=int(os.getenv("CATCH_ALL_CACHE_TTL", "86400")),
            custom_dns_server=os.getenv("CUSTOM_DNS_SERVER", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            smtp_test_mode=os.getenv("SMTP_TEST_MODE", "false").lower() == "true",
            test_smtp_host=os.getenv("TEST_SMTP_HOST", "localhost"),
            test_smtp_port=int(os.getenv("TEST_SMTP_PORT", "1025")),
            test_smtp_use_tls=os.getenv("TEST_SMTP_USE_TLS", "false").lower() == "true",
            test_smtp_username=os.getenv("TEST_SMTP_USERNAME", ""),
            test_smtp_password=os.getenv("TEST_SMTP_PASSWORD", ""),
            smtp_verification_mode=os.getenv("SMTP_VERIFICATION_MODE", "disabled"),
            domain_rate_limit=int(os.getenv("SMTP_DOMAIN_RATE_LIMIT", "2")),
            notification_smtp_enabled=os.getenv("NOTIFICATION_SMTP_ENABLED", "false").lower() == "true",
            notification_smtp_host=os.getenv("NOTIFICATION_SMTP_HOST", ""),
            notification_smtp_port=int(os.getenv("NOTIFICATION_SMTP_PORT", "587")),
            notification_smtp_username=os.getenv("NOTIFICATION_SMTP_USERNAME", ""),
            notification_smtp_password=os.getenv("NOTIFICATION_SMTP_PASSWORD", ""),
            notification_smtp_use_tls=os.getenv("NOTIFICATION_SMTP_USE_TLS", "true").lower() == "true",
            notification_from_email=os.getenv("NOTIFICATION_FROM_EMAIL", ""),
            notification_to_email=os.getenv("NOTIFICATION_TO_EMAIL", ""),
            mailpit_web_url=os.getenv("MAILPIT_WEB_URL", "http://localhost:8025"),
            enable_blacklist_check=os.getenv("ENABLE_BLACKLIST_CHECK", "false").lower() == "true",
            enable_domain_monitoring=os.getenv("ENABLE_DOMAIN_MONITORING", "false").lower() == "true",
            enable_ai_scoring=os.getenv("ENABLE_AI_SCORING", "false").lower() == "true",
            blacklist_dnsbl_providers=os.getenv("BLACKLIST_DNSBL_PROVIDERS", "zen.spamhaus.org,bl.spamcop.net"),
            dkim_selectors=os.getenv("DKIM_SELECTORS", "default,selector1,selector2,google,k1"),
            api_enabled=os.getenv("API_ENABLED", "true").lower() == "true",
            api_key=os.getenv("API_KEY", ""),
            webhook_secret=os.getenv("WEBHOOK_SECRET", ""),
            database_url=os.getenv("DATABASE_URL", "sqlite:///email_verifier.db"),
            data_retention_days=int(os.getenv("DATA_RETENTION_DAYS", "30")),
            max_upload_size_mb=int(os.getenv("MAX_UPLOAD_MB", "50")),
            max_rows=int(os.getenv("MAX_ROWS", "100000")),
        )
