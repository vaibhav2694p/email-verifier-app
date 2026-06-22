import dns.resolver
import dns.exception
import requests
from requests.exceptions import RequestException, Timeout, SSLError


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
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        mx_records = [str(r.exchange).rstrip(".") for r in answers]
        return ", ".join(sorted(mx_records))
    except dns.resolver.NXDOMAIN:
        return "No MX Found"
    except dns.resolver.NoAnswer:
        return "No MX Found"
    except dns.resolver.NoNameservers:
        return "No Nameservers"
    except dns.exception.Timeout:
        return "Timeout"
    except Exception:
        return "Error"


def check_domain_website(domain):
    urls_to_try = [f"https://{domain}", f"https://www.{domain}"]
    for url in urls_to_try:
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            if response.status_code < 400:
                return True, "Active", url
            else:
                return False, f"HTTP {response.status_code}", url
        except SSLError:
            return False, "SSL Error", url
        except Timeout:
            return False, "Timeout", url
        except RequestException:
            continue
    return False, "Not Reachable", ""
