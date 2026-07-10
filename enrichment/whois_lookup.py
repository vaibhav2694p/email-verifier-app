import logging
import re
import socket
from typing import Optional, Dict
from .cache import EnrichmentCache

logger = logging.getLogger(__name__)
_whois_cache = EnrichmentCache(default_ttl=86400)


def lookup_whois(domain: str) -> Optional[Dict]:
    """Look up WHOIS info for a domain. Uses socket-based fallback."""
    cache_key = EnrichmentCache.make_key("whois", domain)
    cached = _whois_cache.get(cache_key)
    if cached is not None:
        return cached

    result = {"domain": domain}
    
    try:
        # Try python-whois if available
        import whois
        w = whois.whois(domain)
        
        if w.creation_date:
            if isinstance(w.creation_date, list):
                creation = w.creation_date[0]
            else:
                creation = w.creation_date
            if hasattr(creation, 'strftime'):
                result["creation_date"] = creation.strftime("%Y-%m-%d")
                result["age"] = _calculate_age(creation)
        
        if w.registrar:
            result["registrar"] = str(w.registrar)
        
        if w.org:
            result["organization"] = str(w.org) if not isinstance(w.org, list) else str(w.org[0])
        
        if w.country:
            result["country"] = str(w.country) if not isinstance(w.country, list) else str(w.country[0])
        
        if w.name_servers:
            ns = w.name_servers if isinstance(w.name_servers, list) else [w.name_servers]
            result["name_servers"] = ns[:5]
        
    except ImportError:
        # python-whois not available, try basic DNS
        logger.debug("python-whois not installed, using DNS fallback")
        _dns_fallback(domain, result)
    except Exception as e:
        logger.debug("WHOIS lookup failed for %s: %s", domain, e)
        _dns_fallback(domain, result)
    
    _whois_cache.set(cache_key, result)
    return result


def _dns_fallback(domain: str, result: Dict):
    """Basic DNS info when WHOIS is unavailable."""
    try:
        ips = socket.getaddrinfo(domain, None)
        if ips:
            result["ip_addresses"] = list(set(addr[4][0] for addr in ips))[:5]
    except Exception:
        pass


def _calculate_age(creation_date) -> str:
    """Calculate domain age from creation date."""
    from datetime import datetime
    try:
        if isinstance(creation_date, str):
            creation_date = datetime.strptime(creation_date, "%Y-%m-%d")
        now = datetime.now()
        delta = now - creation_date
        years = delta.days // 365
        months = (delta.days % 365) // 30
        if years > 0:
            return f"{years}y {months}m"
        return f"{months}m"
    except Exception:
        return ""
