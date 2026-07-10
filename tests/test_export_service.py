import pandas as pd

from services.export_service import ExportService


class TestExportService:
    def _make_df(self):
        return pd.DataFrame({
            "email": ["a@test.com", "b@test.com", "c@test.com"],
            "domain": ["test.com", "test.com", "test.com"],
            "verification_status": ["Valid", "Invalid", "Risky"],
            "verification_score": [85, 10, 55],
            "mx_status": ["Found", "No MX Found", "Found"],
            "spf_record": ["v=spf1 ...", "Not Found", "v=spf1 ..."],
            "dmarc_record": ["v=dmarc1 ...", "Not Found", "Not Found"],
            "website_status": ["Active", "Not Active", "Active"],
            "notes": ["OK", "No MX", "Risky"],
        })

    def test_csv_export(self):
        df = self._make_df()
        csv = ExportService.to_csv(df)
        assert isinstance(csv, bytes)
        assert len(csv) > 0

    def test_excel_export(self):
        df = self._make_df()
        xlsx = ExportService.to_excel(df)
        assert isinstance(xlsx, bytes)
        assert len(xlsx) > 0

    def test_domain_summary(self):
        df = self._make_df()
        summary = ExportService.to_domain_summary(df)
        assert "test.com" in summary["domain"].values

class TestSummaryService:
    def _make_df(self):
        return pd.DataFrame({
            "original_email": ["a@test.com", "b@test.com"],
            "domain": ["test.com", "test.com"],
            "verification_status": ["Valid", "Invalid"],
            "verification_score": [85, 10],
            "disposable": [False, False],
            "catch_all": ["Not Tested", "Not Tested"],
            "role_based": [False, False],
            "is_duplicate": [False, False],
            "mx_status": ["Found", "No MX Found"],
            "smtp_status": ["Not Attempted", "Not Attempted"],
            "mx_provider": ["Unknown", "Unknown"],
            "free_public_email": [False, False],
        })

    def test_compute_summary(self):
        from services.summary_service import SummaryService
        df = self._make_df()
        summary = SummaryService.compute_summary(df)
        assert summary["total_uploaded"] == 2
        assert summary["valid_count"] == 1
        assert summary["invalid_count"] == 1

    def test_apply_filters(self):
        from services.summary_service import SummaryService
        df = self._make_df()
        filtered = SummaryService.apply_filters(df, status_filter=["Valid"])
        assert len(filtered) == 1
