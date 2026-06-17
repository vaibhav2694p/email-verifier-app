from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import dns.exception
import dns.resolver


@dataclass(frozen=True)
class DnsQueryResult:
    state: str
    records: tuple[str, ...] = ()
    error: str = ""


@dataclass(frozen=True)
class RecordStatus:
    status: str
    found: bool
    details: str = ""


@dataclass(frozen=True)
class DomainVerification:
    domain: str
    exists: bool
    existence_status: str
    mx: RecordStatus
    spf: RecordStatus
    dmarc: RecordStatus


def empty_domain_verification(domain: str = "") -> DomainVerification:
    return DomainVerification(
        domain=domain,
        exists=False,
        existence_status="Missing Domain",
        mx=RecordStatus("Missing Domain", False),
        spf=RecordStatus("Missing Domain", False),
        dmarc=RecordStatus("Missing Domain", False),
    )


class DnsVerifier:
    """Performs cached DNS verification for unique domains."""

    def __init__(self, timeout: float = 3.0) -> None:
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = timeout
        self.resolver.lifetime = max(timeout, timeout * 2)
        self._query_cache: dict[tuple[str, str], DnsQueryResult] = {}
        self._domain_cache: dict[str, DomainVerification] = {}

    def verify_domain(self, domain: str) -> DomainVerification:
        normalized_domain = normalize_domain(domain)
        if not normalized_domain:
            return empty_domain_verification()

        if normalized_domain in self._domain_cache:
            return self._domain_cache[normalized_domain]

        mx_query = self._resolve(normalized_domain, "MX")
        txt_query = self._resolve(normalized_domain, "TXT")
        a_query = self._resolve(normalized_domain, "A")
        aaaa_query = self._resolve(normalized_domain, "AAAA")
        ns_query = self._resolve(normalized_domain, "NS")

        main_queries = (mx_query, txt_query, a_query, aaaa_query, ns_query)
        exists, existence_status = determine_domain_existence(main_queries)

        verification = DomainVerification(
            domain=normalized_domain,
            exists=exists,
            existence_status=existence_status,
            mx=build_mx_status(mx_query),
            spf=build_spf_status(txt_query),
            dmarc=self._build_dmarc_status(normalized_domain, exists, existence_status),
        )
        self._domain_cache[normalized_domain] = verification
        return verification

    def _build_dmarc_status(
        self,
        domain: str,
        domain_exists: bool,
        existence_status: str,
    ) -> RecordStatus:
        if not domain_exists and existence_status in {"Invalid Domain", "Invalid DNS Name"}:
            return RecordStatus("Invalid Domain", False)
        if not domain_exists and existence_status == "DNS Timeout":
            return RecordStatus("DNS Timeout", False)

        dmarc_query = self._resolve(f"_dmarc.{domain}", "TXT")
        return build_dmarc_status(dmarc_query)

    def _resolve(self, name: str, rdtype: str) -> DnsQueryResult:
        cache_key = (name, rdtype)
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        try:
            answers = self.resolver.resolve(name, rdtype, raise_on_no_answer=True)
            records = tuple(format_dns_record(answer, rdtype) for answer in answers)
            result = DnsQueryResult("found", records=records)
        except dns.resolver.NXDOMAIN:
            result = DnsQueryResult("nxdomain", error="Domain does not exist")
        except dns.resolver.NoAnswer:
            result = DnsQueryResult("no_answer", error=f"No {rdtype} record")
        except dns.resolver.NoNameservers as exc:
            result = DnsQueryResult("error", error=f"No nameservers responded: {exc}")
        except dns.exception.Timeout:
            result = DnsQueryResult("timeout", error="DNS lookup timed out")
        except dns.exception.DNSException as exc:
            result = DnsQueryResult("error", error=str(exc))

        self._query_cache[cache_key] = result
        return result


def normalize_domain(domain: str) -> str:
    normalized = str(domain or "").strip().strip(".").lower()
    if not normalized:
        return ""
    try:
        ascii_domain = normalized.encode("idna").decode("ascii")
    except UnicodeError:
        return ""
    return ascii_domain


def format_dns_record(answer: object, rdtype: str) -> str:
    if rdtype == "TXT":
        strings = getattr(answer, "strings", None)
        if strings:
            return b"".join(strings).decode("utf-8", errors="replace")
    if rdtype == "MX":
        exchange = getattr(answer, "exchange", None)
        preference = getattr(answer, "preference", None)
        if exchange is not None and preference is not None:
            exchange_text = str(exchange).rstrip(".") or "."
            return f"{preference} {exchange_text}"
    return str(answer).rstrip(".")


def determine_domain_existence(
    results: Iterable[DnsQueryResult],
) -> tuple[bool, str]:
    states = [result.state for result in results]
    if "found" in states:
        return True, "Exists"
    if "no_answer" in states:
        return True, "Exists"
    if states and all(state == "nxdomain" for state in states):
        return False, "Invalid Domain"
    if "timeout" in states:
        return False, "DNS Timeout"
    if "error" in states:
        return False, "DNS Error"
    return False, "Unknown"


def build_mx_status(query: DnsQueryResult) -> RecordStatus:
    if query.state == "found" and query.records:
        non_null_records = tuple(
            record for record in query.records if not record.endswith(" .")
        )
        if not non_null_records:
            return RecordStatus("Null MX", False, ", ".join(query.records))
        return RecordStatus("Valid", True, ", ".join(query.records))
    if query.state == "no_answer":
        return RecordStatus("Missing", False)
    if query.state == "nxdomain":
        return RecordStatus("Invalid Domain", False)
    if query.state == "timeout":
        return RecordStatus("DNS Timeout", False)
    return RecordStatus("DNS Error", False, query.error)


def build_spf_status(query: DnsQueryResult) -> RecordStatus:
    if query.state == "found":
        spf_records = tuple(
            record for record in query.records if record.lower().startswith("v=spf1")
        )
        if spf_records:
            return RecordStatus("Present", True, " | ".join(spf_records))
        return RecordStatus("Missing", False)
    if query.state == "no_answer":
        return RecordStatus("Missing", False)
    if query.state == "nxdomain":
        return RecordStatus("Invalid Domain", False)
    if query.state == "timeout":
        return RecordStatus("DNS Timeout", False)
    return RecordStatus("DNS Error", False, query.error)


def build_dmarc_status(query: DnsQueryResult) -> RecordStatus:
    if query.state == "found":
        dmarc_records = tuple(
            record for record in query.records if record.lower().startswith("v=dmarc1")
        )
        if dmarc_records:
            return RecordStatus("Present", True, " | ".join(dmarc_records))
        return RecordStatus("Missing", False)
    if query.state in {"no_answer", "nxdomain"}:
        return RecordStatus("Missing", False)
    if query.state == "timeout":
        return RecordStatus("DNS Timeout", False)
    return RecordStatus("DNS Error", False, query.error)
