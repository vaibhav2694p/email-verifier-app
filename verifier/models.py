from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VerificationStatus(Enum):
    VALID = "Valid"
    LIKELY_VALID = "Likely Valid"
    RISKY = "Risky"
    INVALID = "Invalid"
    UNKNOWN = "Unknown"
    TEMPORARY_FAILURE = "Temporary Failure"
    CATCH_ALL = "Catch-All"
    DISPOSABLE = "Disposable"
    ROLE_BASED = "Role-Based"
    ABUSE = "Abuse"
    SPAM_TRAP_RISK = "Spam Trap Risk"
    TOXIC_RISK = "Toxic Risk"
    DO_NOT_MAIL = "Do Not Mail"
    NO_DOMAIN = "No Domain"
    NO_MX = "No MX"
    MAILBOX_FULL = "Mailbox Full"
    SMTP_BLOCKED = "SMTP Blocked"
    GREYLISTED = "Greylisted"
    DUPLICATE = "Duplicate"
    SYNTAX_ERROR = "Syntax Error"
    NO_MAIL_SERVER = "No Mail Server"


class ConfidenceLevel(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    VERY_LOW = "Very Low"


class RiskLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class DnsStatus(Enum):
    RESOLVED = "Resolved"
    NXDOMAIN = "NXDomain"
    NO_ANSWER = "NoAnswer"
    NO_NAMESERVERS = "NoNameservers"
    TIMEOUT = "Timeout"
    ERROR = "Error"
    NOT_CHECKED = "Not Checked"


class SmtpStatus(Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TEMPORARY_FAILURE = "temporary_failure"
    GREYLISTED = "greylisted"
    CATCH_ALL = "catch_all"
    UNKNOWN = "unknown"
    CONNECTION_BLOCKED = "connection_blocked"
    TIMEOUT = "timeout"
    SMTP_DISABLED = "smtp_disabled"
    NOT_ATTEMPTED = "not_attempted"


class CatchAllStatus(Enum):
    CATCH_ALL = "Catch-All"
    NOT_CATCH_ALL = "Not Catch-All"
    UNKNOWN = "Unknown"
    NOT_TESTED = "Not Tested"


class ProviderType(Enum):
    FREE_PUBLIC = "Free/Public"
    GOOGLE_WORKSPACE = "Google Workspace"
    MICROSOFT_365 = "Microsoft 365"
    ZOHO = "Zoho"
    FASTMAIL = "Fastmail"
    YANDEX = "Yandex"
    CORPORATE_OTHER = "Corporate/Other"
    UNKNOWN = "Unknown"


@dataclass
class SyntaxResult:
    is_valid: bool
    error: str = ""
    local_part: str = ""
    domain: str = ""
    normalized_email: str = ""
    idn_domain: bool = False
    punycode_domain: str = ""


@dataclass
class TypoResult:
    is_possible_typo: bool = False
    suggested_email: str = ""
    suggested_domain: str = ""
    original_domain: str = ""
    suggestion_confidence: float = 0.0


@dataclass
class DnsResult:
    status: DnsStatus = DnsStatus.NOT_CHECKED
    mx_records: List[Dict[str, Any]] = field(default_factory=list)
    primary_mx: str = ""
    mx_provider: str = ""
    null_mx: bool = False
    dns_error: str = ""
    dns_response_time_ms: float = 0.0
    has_mx: bool = False
    a_records: List[str] = field(default_factory=list)
    aaaa_records: List[str] = field(default_factory=list)
    cname_records: List[str] = field(default_factory=list)
    resolver_used: str = ""


@dataclass
class SmtpResult:
    attempted: bool = False
    status: SmtpStatus = SmtpStatus.NOT_ATTEMPTED
    code: int = 0
    message: str = ""
    mx_host: str = ""
    port: int = 25
    response_time_ms: float = 0.0
    error: str = ""


@dataclass
class CatchAllResult:
    status: CatchAllStatus = CatchAllStatus.NOT_TESTED
    confidence: float = 0.0
    tested: bool = False
    random_email_accepted: bool = False
    test_domain: str = ""


@dataclass
class PipelineStage:
    name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class VerificationResult:
    # Input
    original_email: str = ""
    normalized_email: str = ""
    local_part: str = ""
    domain: str = ""
    cleaned_email: str = ""
    root_domain: str = ""
    idn_domain_text: str = ""
    punycode_domain: str = ""

    # Syntax
    syntax_valid: bool = False
    syntax_error: str = ""
    syntax_error_code: str = ""
    normalization_notes: str = ""
    idn_domain: bool = False
    domain_typo: bool = False
    suggested_email: str = ""
    suggested_domain: str = ""

    # DNS/MX
    dns_status: str = "Not Checked"
    mx_status: str = "Not Checked"
    mx_records: str = ""
    mx_priorities: str = ""
    primary_mx: str = ""
    mx_provider: str = ""
    a_records: str = ""
    aaaa_records: str = ""
    cname_records: str = ""
    null_mx: bool = False
    dns_error: str = ""
    dns_response_time_ms: float = 0.0
    dns_resolver_used: str = ""
    domain_active: bool = False
    website_status: str = "Not Checked"

    # SMTP
    smtp_attempted: bool = False
    smtp_connected: bool = False
    smtp_status: str = "Not Attempted"
    smtp_code: int = 0
    smtp_message: str = ""
    smtp_mx_host: str = ""
    smtp_response_time_ms: float = 0.0
    smtp_tls_supported: bool = False
    smtp_greylisted: bool = False
    smtp_rate_limited: bool = False
    smtp_policy_block: bool = False
    smtp_port_blocked: bool = False
    smtp_blocked: bool = False
    mailbox_accepted: bool = False
    mailbox_rejected: bool = False
    mailbox_full: bool = False
    temporary_failure: bool = False
    smtp_inconclusive: bool = False
    mailbox_evidence: str = "Unknown"

    # Classification
    catch_all: str = "Not Tested"
    catch_all_tested: bool = False
    catch_all_confidence: float = 0.0
    catch_all_smtp_codes: str = ""
    catch_all_notes: str = ""
    disposable: bool = False
    disposable_provider: str = ""
    disposable_category: str = ""
    disposable_dataset_match: str = ""
    disposable_risk: str = ""
    free_public_email: bool = False
    corporate_email: bool = False
    email_provider: str = ""
    mail_hosting_provider: str = ""
    provider_category: str = ""
    provider_confidence: float = 0.0
    role_based: bool = False
    role_category: str = ""
    role_prefix: str = ""
    role_risk: str = ""
    engagement_risk: str = ""
    abuse_address: bool = False
    abuse_category: str = ""
    do_not_mail: bool = False
    abuse_reason: str = ""
    company_domain_match: Optional[bool] = None

    # Risk and reputation
    spam_trap_risk: str = "Unknown"
    spam_trap_signals: List[str] = field(default_factory=list)
    spam_trap_data_source: str = "heuristic"
    spam_trap_confidence: str = "Low"
    confirmed_trap: bool = False
    toxic_risk: str = "Unknown"
    toxic_signals: List[str] = field(default_factory=list)
    complaint_history: str = "Not Provided"
    bounce_history: str = "Not Provided"
    fraud_risk: str = "Unknown"
    toxic_risk_source: str = "heuristic"
    toxic_confidence: str = "Low"

    # Greylisting and retry
    greylisting_detected: bool = False
    retry_required: bool = False
    retry_count: int = 0
    retry_result: str = ""
    final_smtp_status: str = ""
    timeout_stage: str = ""
    timeout_duration: float = 0.0
    connection_error: str = ""
    retry_attempted: bool = False

    # Domain health
    spf_record: str = ""
    spf_status: str = "Not Checked"
    spf_issues: str = ""
    dmarc_record: str = ""
    dmarc_policy: str = ""
    dmarc_status: str = "Not Checked"
    dmarc_reporting_addresses: str = ""
    dkim_status: str = "Not Checked"
    dkim_selector: str = ""
    bimi_status: str = "Not Checked"
    domain_blacklisted: bool = False
    blacklist_checked: bool = False
    blacklist_status: str = "Not Checked"
    listed_on: str = ""
    blacklist_lookup_errors: str = ""
    blacklist_last_checked: str = ""
    domain_age: str = ""
    domain_registrar: str = ""

    # Final
    verification_status: str = "Invalid"
    verification_score: int = 0
    deliverability_score: int = 0
    ai_quality_score: int = 0
    confidence_level: str = "Low"
    risk_level: str = "High"
    recommended_action: str = "Manual Review"
    reason: str = ""
    is_duplicate: bool = False
    duplicate_of: str = ""
    duplicate_group: str = ""
    first_occurrence_row: int = 0

    # Meta
    processing_time_ms: float = 0.0
    verification_run_id: str = ""
    upload_date: str = ""
    original_file_name: str = ""
    notes: str = ""
    score_reasons: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    inconclusive_checks: List[str] = field(default_factory=list)

    # Original data preservation
    original_data: Dict[str, Any] = field(default_factory=dict)
    stage_results: List[PipelineStage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != "stage_results" and k != "original_data"}
