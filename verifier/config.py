import os
from dataclasses import dataclass, field
from typing import Optional


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
        )
