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
):
    score = 0
    score += 10  # Valid syntax
    if has_mx:
        score += 20
    if website_active:
        score += 15
    if email_provider != "Unknown/Other":
        score += 10
    if company_match is True:
        score += 30
    if not is_public_email:
        score += 10
    if not is_disposable:
        score += 10
    if is_role_based:
        score -= 10

    if is_disposable:
        score = min(score, 10)
    elif not has_mx:
        score = min(score, 20)
    elif is_public_email:
        score = min(score, 45)
    elif company_match is False and company_match is not None:
        score = min(score, 50)

    return max(0, min(100, score))
