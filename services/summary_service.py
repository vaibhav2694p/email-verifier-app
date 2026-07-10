import pandas as pd
from typing import Dict, Any, List, Optional


class SummaryService:
    @staticmethod
    def compute_summary(df: pd.DataFrame) -> Dict[str, Any]:
        summary = {}

        summary["total_uploaded"] = len(df)

        if "normalized_email" in df.columns:
            unique = df["normalized_email"].nunique()
        elif "original_email" in df.columns:
            unique = df["original_email"].nunique()
        elif "Email" in df.columns:
            unique = df["Email"].nunique()
        else:
            unique = len(df)
        summary["total_unique"] = unique

        if "verification_status" in df.columns:
            status_counts = df["verification_status"].value_counts()
        else:
            status_counts = pd.Series()

        summary["valid_count"] = int(status_counts.get("Valid", 0))
        summary["likely_valid_count"] = int(status_counts.get("Likely Valid", 0))
        summary["risky_count"] = int(status_counts.get("Risky", 0))
        summary["invalid_count"] = int(status_counts.get("Invalid", 0))
        summary["unknown_count"] = int(status_counts.get("Unknown", 0))

        if "disposable" in df.columns:
            summary["disposable_count"] = int(df["disposable"].sum())
        else:
            summary["disposable_count"] = 0

        if "catch_all" in df.columns:
            catch_all_count = int((df["catch_all"] == "Catch-All").sum())
        else:
            catch_all_count = 0
        summary["catch_all_count"] = catch_all_count

        if "role_based" in df.columns:
            summary["role_based_count"] = int(df["role_based"].sum())
        else:
            summary["role_based_count"] = 0

        if "is_duplicate" in df.columns:
            summary["duplicate_count"] = int(df["is_duplicate"].sum())
        else:
            summary["duplicate_count"] = 0

        if "no_mx_count" not in df.columns and "mx_status" in df.columns:
            summary["no_mx_count"] = int((df["mx_status"] == "No MX Found").sum())
        elif "no_mx_count" in df.columns:
            summary["no_mx_count"] = int(df["no_mx_count"].sum())
        else:
            summary["no_mx_count"] = 0

        if "smtp_blocked_count" not in df.columns and "smtp_status" in df.columns:
            summary["smtp_blocked_count"] = int(
                (df["smtp_status"].isin(["rejected", "connection_blocked"])).sum()
            )
        elif "smtp_blocked_count" in df.columns:
            summary["smtp_blocked_count"] = int(df["smtp_blocked_count"].sum())
        else:
            summary["smtp_blocked_count"] = 0

        if "verification_score" in df.columns:
            summary["average_verification_score"] = round(float(df["verification_score"].mean()), 1)
        else:
            summary["average_verification_score"] = 0.0

        if "confidence_level" in df.columns:
            conf_map = {"High": 3, "Medium": 2, "Low": 1, "Very Low": 0}
            mapped = df["confidence_level"].map(conf_map)
            avg_conf = mapped.mean() if not mapped.isna().all() else 0.0
            reverse_map = {3: "High", 2: "Medium", 1: "Low", 0: "Very Low"}
            summary["average_confidence"] = reverse_map.get(round(avg_conf), "Low")
        else:
            summary["average_confidence"] = "Low"

        if "domain" in df.columns:
            summary["top_domains"] = (
                df["domain"].value_counts().head(10).to_dict()
            )
        else:
            summary["top_domains"] = {}

        if "mx_provider" in df.columns:
            summary["top_providers"] = (
                df["mx_provider"].value_counts().head(10).to_dict()
            )
        else:
            summary["top_providers"] = {}

        return summary

    @staticmethod
    def compute_domain_summary(df: pd.DataFrame) -> pd.DataFrame:
        if "domain" not in df.columns:
            return pd.DataFrame()

        group = df.groupby("domain")
        summary = group.size().reset_index(name="total")

        if "verification_status" in df.columns:
            status_pivot = df.groupby(["domain", "verification_status"]).size().unstack(fill_value=0)
            for col in status_pivot.columns:
                summary[col] = summary["domain"].map(status_pivot[col]).fillna(0).astype(int)

        if "verification_score" in df.columns:
            score_agg = df.groupby("domain")["verification_score"].agg(["mean", "min", "max"]).reset_index()
            score_agg.columns = ["domain", "avg_score", "min_score", "max_score"]
            summary = summary.merge(score_agg, on="domain", how="left")
            summary["avg_score"] = summary["avg_score"].round(1)

        if "mx_provider" in df.columns:
            provider = df.groupby("domain")["mx_provider"].first().reset_index()
            summary = summary.merge(provider, on="domain", how="left")

        if "is_duplicate" in df.columns:
            dup_count = df.groupby("domain")["is_duplicate"].sum().reset_index(name="duplicates")
            summary = summary.merge(dup_count, on="domain", how="left")

        if "disposable" in df.columns:
            disposable_count = df.groupby("domain")["disposable"].sum().reset_index(name="disposable_count")
            summary = summary.merge(disposable_count, on="domain", how="left")

        if "catch_all" in df.columns:
            catch_all_count = df[df["catch_all"] == "Catch-All"].groupby("domain").size().reset_index(name="catch_all_count")
            summary = summary.merge(catch_all_count, on="domain", how="left")
            summary["catch_all_count"] = summary["catch_all_count"].fillna(0).astype(int)

        summary = summary.sort_values("total", ascending=False).reset_index(drop=True)
        return summary

    @staticmethod
    def get_filter_options(df: pd.DataFrame) -> Dict[str, List[str]]:
        options = {}

        if "verification_status" in df.columns:
            options["status"] = sorted(df["verification_status"].dropna().unique().tolist())

        if "domain" in df.columns:
            options["domain"] = sorted(df["domain"].dropna().unique().tolist())

        if "mx_provider" in df.columns:
            options["provider"] = sorted(df["mx_provider"].dropna().unique().tolist())

        if "confidence_level" in df.columns:
            order = ["High", "Medium", "Low", "Very Low"]
            values = df["confidence_level"].dropna().unique().tolist()
            options["confidence"] = [v for v in order if v in values]

        if "risk_level" in df.columns:
            order = ["Low", "Medium", "High", "Critical"]
            values = df["risk_level"].dropna().unique().tolist()
            options["risk"] = [v for v in order if v in values]

        return options

    @staticmethod
    def apply_filters(
        df: pd.DataFrame,
        status_filter: Optional[List[str]] = None,
        score_range: Optional[tuple] = None,
        domain_filter: Optional[List[str]] = None,
        provider_filter: Optional[List[str]] = None,
        disposable_filter: Optional[bool] = None,
        free_filter: Optional[bool] = None,
        role_filter: Optional[bool] = None,
        catch_all_filter: Optional[bool] = None,
        company_match_filter: Optional[bool] = None,
        smtp_filter: Optional[List[str]] = None,
        duplicate_filter: Optional[bool] = None,
    ) -> pd.DataFrame:
        result = df.copy()

        if status_filter and "verification_status" in result.columns:
            result = result[result["verification_status"].isin(status_filter)]

        if score_range is not None and "verification_score" in result.columns:
            lo, hi = score_range
            result = result[(result["verification_score"] >= lo) & (result["verification_score"] <= hi)]

        if domain_filter and "domain" in result.columns:
            result = result[result["domain"].isin(domain_filter)]

        if provider_filter and "mx_provider" in result.columns:
            result = result[result["mx_provider"].isin(provider_filter)]

        if disposable_filter is not None and "disposable" in result.columns:
            result = result[result["disposable"] == disposable_filter]

        if free_filter is not None and "free_public_email" in result.columns:
            result = result[result["free_public_email"] == free_filter]

        if role_filter is not None and "role_based" in result.columns:
            result = result[result["role_based"] == role_filter]

        if catch_all_filter is not None and "catch_all" in result.columns:
            if catch_all_filter:
                result = result[result["catch_all"] == "Catch-All"]
            else:
                result = result[result["catch_all"] != "Catch-All"]

        if company_match_filter is not None and "company_domain_match" in result.columns:
            result = result[result["company_domain_match"] == company_match_filter]

        if smtp_filter and "smtp_status" in result.columns:
            result = result[result["smtp_status"].isin(smtp_filter)]

        if duplicate_filter is not None and "is_duplicate" in result.columns:
            result = result[result["is_duplicate"] == duplicate_filter]

        return result
