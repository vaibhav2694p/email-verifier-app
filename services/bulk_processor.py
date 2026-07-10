import pandas as pd
import logging
from typing import List, Dict, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from verifier.pipeline import VerificationPipeline
from verifier.config import VerifierConfig
from verifier.models import VerificationResult
from verifier.normalizer import normalize_email
from enrichment.company_lookup import lookup_company
from enrichment.person_lookup import lookup_person
from enrichment.summary import generate_summary as generate_enrichment_summary

logger = logging.getLogger(__name__)

class BulkProcessor:
    def __init__(
        self,
        config: Optional[VerifierConfig] = None,
        progress_callback: Optional[Callable[[int, int, dict], None]] = None,
        enrichment_enabled: bool = False,
    ):
        self.config = config or VerifierConfig()
        self.pipeline = VerificationPipeline(self.config)
        self.progress_callback = progress_callback
        self.enrichment_enabled = enrichment_enabled
        self._cancelled = False

    def process(
        self,
        df: pd.DataFrame,
        email_column: str,
        company_domain_column: Optional[str] = None,
    ) -> pd.DataFrame:
        df = df.copy()
        df, duplicate_map = self._detect_duplicates(df, email_column)

        unique_emails = self._get_unique_emails(df, email_column)

        company_domain_map: Dict[str, Optional[str]] = {}
        if company_domain_column and company_domain_column in df.columns:
            for idx in df.index:
                raw = str(df.at[idx, email_column]).strip() if pd.notna(df.at[idx, email_column]) else ""
                if raw:
                    try:
                        norm = normalize_email(raw)
                    except Exception:
                        norm = raw.lower()
                    raw_domain = str(df.at[idx, company_domain_column]).strip() if pd.notna(df.at[idx, company_domain_column]) else ""
                    company_domain_map[norm] = raw_domain if raw_domain else None

        results_dict = {}
        if unique_emails:
            email_domain_pairs = []
            for e in unique_emails:
                try:
                    norm_e = normalize_email(e)
                except Exception:
                    norm_e = e.lower()
                email_domain_pairs.append((e, company_domain_map.get(norm_e)))
            column_results = self._process_batch(email_domain_pairs)
            for result in column_results:
                results_dict[result.normalized_email or result.original_email] = result

        result_df = self._map_results_back(df, results_dict, email_column, duplicate_map)

        if self.enrichment_enabled:
            result_df = self._enrich_results(result_df, email_column)

        return result_df

    def _detect_duplicates(
        self, df: pd.DataFrame, email_column: str
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        df = df.copy()
        df["is_duplicate"] = False
        df["duplicate_of"] = ""

        seen_normalized = {}
        duplicate_map = {}

        for idx in df.index:
            raw = str(df.at[idx, email_column]).strip() if pd.notna(df.at[idx, email_column]) else ""
            if not raw:
                continue
            try:
                normalized = normalize_email(raw)
            except Exception:
                normalized = raw.lower()

            if normalized in seen_normalized:
                first_idx = seen_normalized[normalized]
                df.at[idx, "is_duplicate"] = True
                df.at[idx, "duplicate_of"] = str(df.at[first_idx, email_column])
                duplicate_map[str(idx)] = str(df.at[first_idx, email_column])
            else:
                seen_normalized[normalized] = idx

        return df, duplicate_map

    def _get_unique_emails(
        self, df: pd.DataFrame, email_column: str
    ) -> List[str]:
        if "is_duplicate" in df.columns:
            unique_df = df[df["is_duplicate"] == False].copy()
        else:
            unique_df = df.copy()

        seen = set()
        emails = []
        for raw in unique_df[email_column]:
            val = str(raw).strip() if pd.notna(raw) else ""
            if not val:
                continue
            try:
                normalized = normalize_email(val)
            except Exception:
                normalized = val.lower()
            if normalized not in seen:
                seen.add(normalized)
                emails.append(val)
        return emails

    def _process_batch(
        self,
        email_domain_pairs: List[Tuple[str, Optional[str]]],
    ) -> List[VerificationResult]:
        results = []
        total = len(email_domain_pairs)
        batch_size = self.config.batch_size
        max_workers = self.config.max_workers

        for batch_start in range(0, total, batch_size):
            if self._cancelled:
                logger.info("Processing cancelled by user")
                break

            batch = email_domain_pairs[batch_start:batch_start + batch_size]
            batch_results = [None] * len(batch)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {}
                for i, (email, company_domain) in enumerate(batch):
                    future = executor.submit(self._process_single, email, company_domain)
                    future_map[future] = i

                for future in as_completed(future_map):
                    idx = future_map[future]
                    try:
                        batch_results[idx] = future.result()
                    except Exception as e:
                        logger.error(f"Error processing email in batch: {e}")
                        err_result = VerificationResult(original_email=batch[idx][0], notes=f"Error: {e}")
                        batch_results[idx] = err_result

            for result in batch_results:
                if result is not None:
                    results.append(result)

            if self.progress_callback:
                processed = len(results)
                self.progress_callback(processed, total, {})

        return results

    def _process_single(
        self,
        email: str,
        company_domain: Optional[str],
    ) -> VerificationResult:
        try:
            result = self.pipeline.verify(email, company_domain=company_domain)
            return result
        except Exception as e:
            logger.error(f"Error processing {email}: {e}")
            return VerificationResult(
                original_email=email,
                verification_status="Error",
                notes=str(e),
            )

    def _map_results_back(
        self,
        df: pd.DataFrame,
        results: Dict[str, VerificationResult],
        email_column: str,
        duplicate_map: Dict[str, str],
    ) -> pd.DataFrame:
        result_rows = []
        for idx in df.index:
            row = df.loc[idx].to_dict()
            raw = str(row.get(email_column, "")).strip() if pd.notna(row.get(email_column, "")) else ""

            if not raw:
                result_rows.append(row)
                continue

            try:
                normalized = normalize_email(raw)
            except Exception:
                normalized = raw.lower()

            result = results.get(normalized)
            if result is not None:
                result_dict = result.to_dict()
                row.update(result_dict)
                row["original_email"] = result.original_email
            else:
                row["original_email"] = raw

            result_rows.append(row)

        result_df = pd.DataFrame(result_rows)

        if result_df.index.name == "index":
            result_df = result_df.reset_index(drop=True)

        return result_df

    def _enrich_results(self, df: pd.DataFrame, email_column: str) -> pd.DataFrame:
        """Enrich results with public profile data. Deduplicates by domain."""
        if df.empty:
            return df

        enrichment_cols = [
            "first_name", "last_name", "full_name", "company_name", "company_website",
            "company_description", "department", "job_title", "linkedin_url", "company_linkedin",
            "github_url", "twitter_url", "facebook_url", "instagram_url",
            "country", "city", "phone", "domain_age", "domain_registrar",
            "enrichment_confidence", "public_sources", "ai_summary",
        ]
        for col in enrichment_cols:
            if col not in df.columns:
                df[col] = ""

        # Deduplicate by domain for company lookups
        domain_cache = {}
        email_col = "original_email" if "original_email" in df.columns else email_column

        for idx in df.index:
            raw = str(df.at[idx, email_col]).strip() if pd.notna(df.at[idx, email_col]) else ""
            if not raw or "@" not in raw:
                continue

            domain = raw.split("@")[1].lower()
            local_part = raw.split("@")[0]

            # Company lookup (cached per domain)
            company = None
            if domain not in domain_cache:
                try:
                    company = lookup_company(domain)
                    domain_cache[domain] = company
                except Exception:
                    domain_cache[domain] = None
            company = domain_cache.get(domain)

            # Person lookup
            person = None
            try:
                person = lookup_person(raw, company_profile=company)
            except Exception:
                pass

            # Map results back
            if person:
                df.at[idx, "first_name"] = person.first_name
                df.at[idx, "last_name"] = person.last_name
                df.at[idx, "full_name"] = person.full_name
                df.at[idx, "job_title"] = person.job_title
                df.at[idx, "department"] = person.department
                df.at[idx, "linkedin_url"] = person.linkedin_url
                df.at[idx, "github_url"] = person.github_url
                df.at[idx, "twitter_url"] = person.twitter_url
                df.at[idx, "facebook_url"] = person.facebook_url
                df.at[idx, "instagram_url"] = person.instagram_url
                df.at[idx, "country"] = person.country
                df.at[idx, "city"] = person.city
                df.at[idx, "phone"] = person.phone
                df.at[idx, "enrichment_confidence"] = person.confidence_level
                df.at[idx, "public_sources"] = "; ".join(person.sources[:5])

            if company:
                df.at[idx, "company_name"] = company.name
                df.at[idx, "company_website"] = f"https://{company.domain}"
                df.at[idx, "company_description"] = company.description[:200] if company.description else ""
                df.at[idx, "company_linkedin"] = company.linkedin_url
                df.at[idx, "domain_age"] = company.domain_age
                df.at[idx, "domain_registrar"] = company.domain_registrar

            # AI summary
            try:
                df.at[idx, "ai_summary"] = generate_enrichment_summary(person, company)
            except Exception:
                pass

            if self.progress_callback:
                self.progress_callback(idx + 1, len(df), {"phase": "enrichment"})

        return df

    def cancel(self):
        self._cancelled = True
