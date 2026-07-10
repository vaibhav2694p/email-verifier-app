import logging
import socket
import time
from typing import Any, Dict, List, Optional, Tuple

import dns.exception
import dns.name
import dns.resolver

from .cache import TTLCache
from .config import VerifierConfig
from .models import DnsResult, DnsStatus

logger = logging.getLogger(__name__)

_dns_cache = TTLCache(default_ttl=3600)

MX_PROVIDER_KEYWORDS: Dict[str, List[str]] = {
    "Google Workspace": ["google.com", "googlemail.com", "aspmx.l.google.com"],
    "Microsoft 365": ["outlook.com", "protection.outlook.com", "office365.com", "microsoft.com"],
    "Zoho": ["zoho.com", "zohomail.com"],
    "Fastmail": ["fastmail.com", "messagingengine.com"],
    "Yandex": ["yandex.net", "yandex.ru", "ya.ru"],
    "Apple iCloud": ["icloud.com", "mail.me.com"],
    "ProtonMail": ["protonmail.ch", "protonmail.com"],
}


def _get_resolver(config: Optional[VerifierConfig] = None) -> dns.resolver.Resolver:
    resolver = dns.resolver.Resolver()
    resolver.timeout = (config or VerifierConfig()).dns_timeout
    resolver.lifetime = (config or VerifierConfig()).dns_timeout * 2
    if config and config.custom_dns_server:
        resolver.nameservers = [config.custom_dns_server]
    return resolver


def validate_dns(domain: str, config: Optional[VerifierConfig] = None) -> DnsResult:
    cache_key = f"dns:{domain}"
    cached = _dns_cache.get(cache_key)
    if cached is not None:
        return cached

    start = time.time()
    result = DnsResult()
    resolver = _get_resolver(config)
    result.resolver_used = ",".join(resolver.nameservers)

    try:
        result.a_records = lookup_record_values(domain, "A", config)
        result.aaaa_records = lookup_record_values(domain, "AAAA", config)
        result.cname_records = lookup_record_values(domain, "CNAME", config)
        mx_records = lookup_mx_records(domain, config)
        result.mx_records = mx_records
        result.has_mx = len(mx_records) > 0
        result.null_mx = detect_null_mx(mx_records)

        if result.has_mx and not result.null_mx:
            sorted_records = sorted(mx_records, key=lambda r: r.get("priority", 0))
            result.primary_mx = sorted_records[0].get("host", "")
            result.mx_provider = classify_mx_provider(mx_records)
            result.status = DnsStatus.RESOLVED
        elif result.null_mx:
            result.status = DnsStatus.RESOLVED
            result.primary_mx = ""
            result.mx_provider = "Null MX (No Email)"
        else:
            if result.a_records or result.aaaa_records:
                result.primary_mx = (result.a_records or result.aaaa_records)[0]
                result.status = DnsStatus.RESOLVED
                result.mx_provider = "A/AAAA Fallback"
            else:
                result.status = DnsStatus.NO_ANSWER
                result.dns_error = "No MX or A records found"

    except dns.resolver.NXDOMAIN:
        result.status = DnsStatus.NXDOMAIN
        result.dns_error = f"Domain {domain} does not exist (NXDOMAIN)"
    except dns.resolver.NoAnswer:
        result.status = DnsStatus.NO_ANSWER
        result.dns_error = f"No DNS answer for {domain}"
    except dns.resolver.NoNameservers:
        result.status = DnsStatus.NO_NAMESERVERS
        result.dns_error = f"No nameservers could be reached for {domain}"
    except dns.exception.Timeout:
        result.status = DnsStatus.TIMEOUT
        result.dns_error = f"DNS query timed out for {domain}"
    except Exception as e:
        result.status = DnsStatus.ERROR
        result.dns_error = f"DNS error: {str(e)}"
        logger.warning(f"Unexpected DNS error for {domain}: {e}")

    result.dns_response_time_ms = round((time.time() - start) * 1000, 2)
    _dns_cache.set(cache_key, result)
    return result


def lookup_mx_records(domain: str, config: Optional[VerifierConfig] = None) -> List[Dict[str, Any]]:
    resolver = _get_resolver(config)
    max_retries = (config or VerifierConfig()).max_retries
    last_exc = None

    for attempt in range(max_retries + 1):
        try:
            answers = resolver.resolve(domain, "MX")
            records = []
            for rdata in answers:
                mx_host = str(rdata.exchange).rstrip(".")
                records.append({
                    "host": mx_host,
                    "priority": rdata.preference,
                    "ips": _resolve_a_records(mx_host, config),
                })
            return records
        except (dns.exception.Timeout, dns.resolver.NoNameservers) as e:
            last_exc = e
            if attempt < max_retries:
                wait = 0.5 * (attempt + 1)
                logger.debug(f"Retry {attempt + 1}/{max_retries} for MX lookup of {domain} after {wait}s")
                time.sleep(wait)
            else:
                raise
        except Exception:
            raise

    raise last_exc


def _resolve_a_records(hostname: str, config: Optional[VerifierConfig] = None) -> List[str]:
    try:
        resolver = _get_resolver(config)
        answers = resolver.resolve(hostname, "A")
        return [str(r) for r in answers]
    except Exception:
        return []


def detect_null_mx(mx_records: List[Dict[str, Any]]) -> bool:
    return any(
        r.get("priority") == 0 and r.get("host", "").strip() == ""
        for r in mx_records
    )


def classify_mx_provider(mx_records: List[Dict[str, Any]]) -> str:
    if not mx_records:
        return ""

    all_hosts = " ".join(r.get("host", "") for r in mx_records).lower()

    for provider, keywords in MX_PROVIDER_KEYWORDS.items():
        if any(keyword.lower() in all_hosts for keyword in keywords):
            return provider

    return "Unknown"


def lookup_a_record(domain: str, config: Optional[VerifierConfig] = None) -> Optional[str]:
    resolver = _get_resolver(config)
    try:
        answers = resolver.resolve(domain, "A")
        return str(answers[0])
    except Exception:
        pass

    try:
        answers = resolver.resolve(domain, "AAAA")
        return str(answers[0])
    except Exception:
        return None


def lookup_record_values(domain: str, record_type: str, config: Optional[VerifierConfig] = None) -> List[str]:
    resolver = _get_resolver(config)
    try:
        answers = resolver.resolve(domain, record_type)
        values = []
        for answer in answers:
            value = str(answer).rstrip(".")
            values.append(value)
        return values
    except Exception:
        return []


def check_domain_reachable(domain: str) -> Tuple[bool, str, str]:
    for scheme, port in [("https", 443), ("http", 80)]:
        try:
            socket.setdefaulttimeout(5)
            socket.gethostbyname(domain)
            return True, "reachable", f"{scheme}://{domain}"
        except socket.gaierror:
            continue
        except Exception as e:
            return False, "unreachable", str(e)
        finally:
            socket.setdefaulttimeout(None)
    return False, "unreachable", "Could not resolve domain via socket"
