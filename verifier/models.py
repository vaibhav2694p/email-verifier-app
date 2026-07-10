from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import time


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

    # Syntax
    syntax_valid: bool = False
    syntax_error: str = ""
    idn_domain: bool = False
    domain_typo: bool = False
    suggested_email: str = ""
    suggested_domain: str = ""

    # DNS/MX
    dns_status: str = "Not Checked"
    mx_status: str = "Not Checked"
    mx_records: str = ""
    primary_mx: str = ""
    mx_provider: str = ""
    null_mx: bool = False
    domain_active: bool = False
    website_status: str = "Not Checked"

    # SMTP
    smtp_attempted: bool = False
    smtp_status: str = "Not Attempted"
    smtp_code: int = 0
    smtp_message: str = ""

    # Classification
    catch_all: str = "Not Tested"
    disposable: bool = False
    free_public_email: bool = False
    role_based: bool = False
    role_category: str = ""
    company_domain_match: Optional[bool] = None

    # Final
    verification_status: str = "Invalid"
    verification_score: int = 0
    confidence_level: str = "Low"
    risk_level: str = "High"
    is_duplicate: bool = False
    duplicate_of: str = ""

    # Meta
    processing_time_ms: float = 0.0
    notes: str = ""
    score_reasons: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    inconclusive_checks: List[str] = field(default_factory=list)

    # Original data preservation
    original_data: Dict[str, Any] = field(default_factory=dict)
    stage_results: List[PipelineStage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != "stage_results" and k != "original_data"}
