from verifier.role_detector import detect_role_account


class TestRoleDetection:
    def test_info_is_role(self):
        is_role, category, adjustment = detect_role_account("info@company.com")
        assert is_role is True
        assert "general" in category.lower()

    def test_support_is_role(self):
        is_role, category, adjustment = detect_role_account("support@company.com")
        assert is_role is True

    def test_sales_is_role(self):
        is_role, category, adjustment = detect_role_account("sales@company.com")
        assert is_role is True

    def test_admin_is_role(self):
        is_role, category, adjustment = detect_role_account("admin@company.com")
        assert is_role is True

    def test_noreply_is_role(self):
        is_role, category, adjustment = detect_role_account("noreply@company.com")
        assert is_role is True

    def test_user_not_role(self):
        is_role, category, adjustment = detect_role_account("john@company.com")
        assert is_role is False

    def test_random_not_role(self):
        is_role, category, adjustment = detect_role_account("abc123@company.com")
        assert is_role is False
