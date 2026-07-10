class VerifierError(Exception):
    def __init__(self, message: str = "A verifier error occurred", detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail

    def __str__(self):
        if self.detail:
            return f"{self.message}: {self.detail}"
        return self.message


class SyntaxError(VerifierError):
    def __init__(self, message: str = "Email syntax is invalid", detail: str = ""):
        super().__init__(message, detail)


class DomainError(VerifierError):
    def __init__(self, message: str = "Domain extraction or validation failed", detail: str = ""):
        super().__init__(message, detail)


class DNSError(VerifierError):
    def __init__(self, message: str = "DNS resolution failed", detail: str = ""):
        super().__init__(message, detail)


class SMTPError(VerifierError):
    def __init__(self, message: str = "SMTP probe failed", detail: str = ""):
        super().__init__(message, detail)


class ValidationError(VerifierError):
    def __init__(self, message: str = "General validation error", detail: str = ""):
        super().__init__(message, detail)


class ConfigurationError(VerifierError):
    def __init__(self, message: str = "Bad configuration", detail: str = ""):
        super().__init__(message, detail)


class CacheError(VerifierError):
    def __init__(self, message: str = "Cache operation failed", detail: str = ""):
        super().__init__(message, detail)
