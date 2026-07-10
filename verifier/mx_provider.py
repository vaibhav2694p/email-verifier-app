import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from .models import ProviderType

_PROVIDER_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "public_domains.json"

_free_domains: List[str] = []
_workspace_providers: Dict[str, Any] = {}


def _load_provider_data():
    global _free_domains, _workspace_providers
    if _free_domains or _workspace_providers:
        return
    try:
        with open(_PROVIDER_DATA_PATH, "r") as f:
            data = json.load(f)
        _free_domains = data.get("free_domains", [])
        _workspace_providers = data.get("workspace_providers", {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        _free_domains = []
        _workspace_providers = {}


def classify_provider(mx_records: List[Dict[str, Any]], domain: str) -> ProviderType:
    _load_provider_data()

    if is_free_provider(domain):
        return ProviderType.FREE_PUBLIC

    if isinstance(mx_records, list) and len(mx_records) > 0:
        if is_google_workspace(mx_records):
            return ProviderType.GOOGLE_WORKSPACE
        if is_microsoft_365(mx_records):
            return ProviderType.MICROSOFT_365
        if is_zoho(mx_records):
            return ProviderType.ZOHO
        if _match_provider(mx_records, "fastmail"):
            return ProviderType.FASTMAIL
        if _match_provider(mx_records, "yandex"):
            return ProviderType.YANDEX

    workspace_type = is_workspace_domain(domain, mx_records)
    if workspace_type:
        return workspace_type

    if isinstance(mx_records, list) and len(mx_records) > 0:
        return ProviderType.CORPORATE_OTHER

    return ProviderType.UNKNOWN


def get_provider_name(provider_type: ProviderType) -> str:
    mapping = {
        ProviderType.FREE_PUBLIC: "Free/Public Email Provider",
        ProviderType.GOOGLE_WORKSPACE: "Google Workspace",
        ProviderType.MICROSOFT_365: "Microsoft 365",
        ProviderType.ZOHO: "Zoho",
        ProviderType.FASTMAIL: "Fastmail",
        ProviderType.YANDEX: "Yandex",
        ProviderType.CORPORATE_OTHER: "Corporate/Other",
        ProviderType.UNKNOWN: "Unknown",
    }
    return mapping.get(provider_type, "Unknown")


def is_google_workspace(mx_records: List[Dict[str, Any]]) -> bool:
    return _match_provider(mx_records, "google")


def is_microsoft_365(mx_records: List[Dict[str, Any]]) -> bool:
    return _match_provider(mx_records, "microsoft")


def is_zoho(mx_records: List[Dict[str, Any]]) -> bool:
    return _match_provider(mx_records, "zoho")


def _match_provider(mx_records: List[Dict[str, Any]], provider_key: str) -> bool:
    _load_provider_data()
    provider_config = _workspace_providers.get(provider_key)
    if not provider_config:
        return False

    patterns = provider_config.get("mx_patterns", [])
    if not isinstance(mx_records, list):
        return False

    all_hosts = " ".join(
        r.get("host", "").lower() for r in mx_records if isinstance(r, dict)
    )

    return any(pattern.lower() in all_hosts for pattern in patterns)


def is_free_provider(domain: str) -> bool:
    _load_provider_data()
    domain_lower = domain.lower().strip()
    if domain_lower in _free_domains:
        return True
    parts = domain_lower.split(".")
    if len(parts) >= 2:
        for free_domain in _free_domains:
            if domain_lower.endswith("." + free_domain):
                return True
    return False


def is_workspace_domain(domain: str, mx_records: List[Dict[str, Any]]) -> Optional[ProviderType]:
    _load_provider_data()
    if not isinstance(mx_records, list) or len(mx_records) == 0:
        return None

    all_hosts = " ".join(
        r.get("host", "").lower() for r in mx_records if isinstance(r, dict)
    )

    for provider_key, provider_config in _workspace_providers.items():
        workspace_mx = provider_config.get("workspace_mx", [])
        match = all(
            any(wc.replace("*.", "") in all_hosts for wc in workspace_mx)
            if isinstance(workspace_mx, list) and len(workspace_mx) > 0
            else False
        )
        if match:
            mapping = {
                "google": ProviderType.GOOGLE_WORKSPACE,
                "microsoft": ProviderType.MICROSOFT_365,
                "zoho": ProviderType.ZOHO,
                "fastmail": ProviderType.FASTMAIL,
                "yandex": ProviderType.YANDEX,
            }
            return mapping.get(provider_key)

    return None
