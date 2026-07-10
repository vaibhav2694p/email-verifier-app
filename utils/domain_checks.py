import dns.resolver
import dns.exception
import requests
from requests.exceptions import RequestException, Timeout, SSLError

_domain_cache = {}


def clean_domain(value):
    if not value or not isinstance(value, str):
        return ""
    value = value.strip().lower()
    if value.startswith("http://"):
        value = value[7:]
    elif value.startswith("https://"):
        value = value[8:]
    if value.startswith("www."):
        value = value[4:]
    if "@" in value:
        value = value.split("@")[-1]
    if "/" in value:
        value = value.split("/")[0]
    if ":" in value:
        value = value.split(":")[0]
    return value.strip()


def lookup_mx_records(domain):
    key = f"mx:{domain}"
    if key in _domain_cache:
        return _domain_cache[key]
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        mx_records = [str(r.exchange).rstrip(".") for r in answers]
        result = ", ".join(sorted(mx_records))
    except dns.resolver.NXDOMAIN:
        result = "No MX Found"
    except dns.resolver.NoAnswer:
        result = "No MX Found"
    except dns.resolver.NoNameservers:
        result = "No Nameservers"
    except dns.exception.Timeout:
        result = "Timeout"
    except Exception:
        result = "Error"
    _domain_cache[key] = result
    return result


def lookup_spf_record(domain):
    key = f"spf:{domain}"
    if key in _domain_cache:
        return _domain_cache[key]
    try:
        answers = dns.resolver.resolve(domain, "TXT", lifetime=5)
        for rdata in answers:
            txt = b"".join(rdata.strings).decode("utf-8", errors="ignore")
            if txt.lower().startswith("v=spf1"):
                _domain_cache[key] = txt
                return txt
        result = "Not Found"
    except dns.resolver.NXDOMAIN:
        result = "Not Found (NXDOMAIN)"
    except dns.resolver.NoAnswer:
        result = "Not Found (No TXT)"
    except dns.resolver.NoNameservers:
        result = "No Nameservers"
    except dns.exception.Timeout:
        result = "Timeout"
    except Exception:
        result = "Error"
    _domain_cache[key] = result
    return result


def lookup_dmarc_record(domain):
    key = f"dmarc:{domain}"
    if key in _domain_cache:
        return _domain_cache[key]
    dmarc_domain = f"_dmarc.{domain}"
    try:
        answers = dns.resolver.resolve(dmarc_domain, "TXT", lifetime=5)
        for rdata in answers:
            txt = b"".join(rdata.strings).decode("utf-8", errors="ignore")
            if txt.lower().startswith("v=dmarc1"):
                _domain_cache[key] = txt
                return txt
        result = "Not Found"
    except dns.resolver.NXDOMAIN:
        result = "Not Found (NXDOMAIN)"
    except dns.resolver.NoAnswer:
        result = "Not Found (No TXT)"
    except dns.resolver.NoNameservers:
        result = "No Nameservers"
    except dns.exception.Timeout:
        result = "Timeout"
    except Exception:
        result = "Error"
    _domain_cache[key] = result
    return result


def check_domain_website(domain):
    key = f"web:{domain}"
    if key in _domain_cache:
        cached = _domain_cache[key]
        return cached[0], cached[1], cached[2]
    urls_to_try = [f"https://{domain}", f"https://www.{domain}"]
    for url in urls_to_try:
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            if response.status_code < 400:
                _domain_cache[key] = (True, "Active", url)
                return True, "Active", url
            else:
                _domain_cache[key] = (False, f"HTTP {response.status_code}", url)
                return False, f"HTTP {response.status_code}", url
        except SSLError:
            _domain_cache[key] = (False, "SSL Error", url)
            return False, "SSL Error", url
        except Timeout:
            _domain_cache[key] = (False, "Timeout", url)
            return False, "Timeout", url
        except RequestException:
            continue
    _domain_cache[key] = (False, "Not Reachable", "")
    return False, "Not Reachable", ""
