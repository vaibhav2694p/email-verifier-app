from pathlib import Path

from email_validator import validate_email, EmailNotValidError


def validate_and_normalize_email(email):
    try:
        validation = validate_email(email, check_deliverability=False)
        return validation.email
    except EmailNotValidError as e:
        raise ValueError(str(e))


def extract_email_domain(email):
    return email.split("@")[1].lower() if "@" in email else ""


def is_public_email_domain(domain):
    public_domains = {
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
        "aol.com", "icloud.com", "proton.me", "protonmail.com",
        "live.com", "msn.com", "yahoo.co.uk", "yahoo.ca",
        "ymail.com", "rocketmail.com",
    }
    return domain in public_domains


def is_disposable_domain(domain):
    disposable_file = Path("disposable_domains.txt")
    built_in = {
        "mailinator.com", "10minutemail.com", "guerrillamail.com",
        "temp-mail.org", "yopmail.com", "tempmail.com",
        "throwawaymail.com", "getnada.com", "maildrop.cc",
    }
    if disposable_file.exists():
        try:
            with open(disposable_file, "r") as f:
                file_domains = {line.strip().lower() for line in f if line.strip()}
                return domain in file_domains
        except Exception:
            pass
    return domain in built_in


def is_role_based_email(email):
    role_prefixes = {
        "info", "sales", "support", "admin", "contact", "hello",
        "marketing", "hr", "careers", "billing", "accounting",
        "finance", "service", "help", "enquiry",
    }
    local_part = email.split("@")[0].lower()
    return any(local_part.startswith(prefix) for prefix in role_prefixes)


def detect_email_provider(mx_records):
    mx_lower = mx_records.lower()
    providers = {
        "Google Workspace": ["google.com", "googlemail.com", "aspmx.l.google.com"],
        "Microsoft 365": ["outlook.com", "protection.outlook.com", "office365.com", "microsoft.com"],
        "Zoho Mail": ["zoho.com", "zohomail.com"],
        "Yahoo/AOL": ["yahoo.com", "yahoodns.net", "aol.com"],
        "Fastmail": ["fastmail.com", "messagingengine.com"],
        "Proton Mail": ["protonmail.ch", "protonmail.com", "proton.me"],
        "GoDaddy": ["secureserver.net", "godaddy.com"],
        "Namecheap": ["privateemail.com", "namecheap.com"],
        "Rackspace": ["emailsrvr.com", "rackspace.com"],
    }
    for provider, patterns in providers.items():
        if any(pattern in mx_lower for pattern in patterns):
            return provider
    return "Unknown/Other"
