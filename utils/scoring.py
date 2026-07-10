def calculate_verification_score(
    normalized_email,
    domain,
    has_mx,
    website_active,
    email_provider,
    company_match,
    is_role_based,
    is_disposable=False,
    is_public_email=False,
    has_spf=False,
    has_dmarc=False,
):
    score = 0
    score += 10  # Valid syntax
    if has_mx:
        score += 20  # MX found
    if has_spf:
        score += 10  # SPF found
    if has_dmarc:
        score += 10  # DMARC found
    if website_active:
        score += 15  # Website accessible
    if email_provider != "Unknown/Other":
        score += 10  # Known provider
    if company_match is True:
        score += 30  # Company domain match
    if not is_public_email:
        score += 10  # Not public/free
    if not is_disposable:
        score += 10  # Not disposable
    if is_role_based:
        score -= 10  # Role-based penalty

    return max(0, min(100, score))


def score_to_status(score):
    if score <= 50:
        return "Invalid"
    elif score <= 65:
        return "Risky"
    elif score <= 84:
        return "Average"
    else:
        return "Verified"
