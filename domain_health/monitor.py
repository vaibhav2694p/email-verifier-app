from __future__ import annotations

from .bimi_checker import check_bimi
from .blacklist_checker import check_blacklists
from .dkim_checker import check_dkim
from .dmarc_checker import check_dmarc
from .spf_checker import check_spf


def check_domain_health(domain: str, config=None) -> dict:
    dns_timeout = getattr(config, "dns_timeout", 5)
    enable_blacklist_check = getattr(config, "enable_blacklist_check", False)
    dkim_selectors = getattr(config, "dkim_selectors", "default,selector1,selector2,google,k1")
    dnsbl_providers = getattr(config, "blacklist_dnsbl_providers", "zen.spamhaus.org,bl.spamcop.net")
    selectors = [s.strip() for s in dkim_selectors.split(",") if s.strip()]
    providers = [p.strip() for p in dnsbl_providers.split(",") if p.strip()]

    spf = check_spf(domain, dns_timeout)
    dmarc = check_dmarc(domain, dns_timeout)
    dkim = check_dkim(domain, selectors, dns_timeout)
    blacklist = check_blacklists(domain, providers, enable_blacklist_check, dns_timeout)
    bimi = check_bimi(domain, dns_timeout)

    return {
        "spf_record": spf.record,
        "spf_status": spf.status,
        "spf_issues": "; ".join(spf.issues or []),
        "dmarc_record": dmarc.record,
        "dmarc_policy": dmarc.policy,
        "dmarc_status": dmarc.status,
        "dmarc_reporting_addresses": "; ".join(dmarc.reporting_addresses or []),
        "dkim_status": dkim.status,
        "dkim_selector": dkim.selector,
        "bimi_status": bimi,
        "blacklist_checked": blacklist.checked,
        "blacklist_status": blacklist.status,
        "domain_blacklisted": bool(blacklist.listed_on),
        "listed_on": "; ".join(blacklist.listed_on or []),
        "blacklist_lookup_errors": "; ".join(blacklist.lookup_errors or []),
        "blacklist_last_checked": blacklist.last_checked,
    }
