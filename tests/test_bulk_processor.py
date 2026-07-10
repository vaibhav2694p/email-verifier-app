import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from services.bulk_processor import BulkProcessor
from verifier.config import VerifierConfig

class TestBulkProcessor:
    def test_duplicate_detection(self):
        df = pd.DataFrame({
            "email": ["user@a.com", "user@b.com", "user@a.com", "test@c.com"],
            "name": ["A", "B", "C", "D"]
        })
        processor = BulkProcessor(config=VerifierConfig())
        dup_df, dup_map = processor._detect_duplicates(df, "email")
        assert dup_df["is_duplicate"].sum() == 1  # One duplicate
    
    def test_empty_dataframe(self):
        df = pd.DataFrame({"email": []})
        processor = BulkProcessor(config=VerifierConfig())
        unique = processor._get_unique_emails(df, "email")
        assert len(unique) == 0
    
    def test_whitespace_emails(self):
        df = pd.DataFrame({
            "email": [" user@a.com ", "user@a.com", "USER@A.COM"]
        })
        processor = BulkProcessor(config=VerifierConfig())
        dup_df, dup_map = processor._detect_duplicates(df, "email")
        assert dup_df["is_duplicate"].sum() == 2  # Two are duplicates
    
    def test_preserves_original_columns(self):
        df = pd.DataFrame({
            "email": ["user@a.com", "user@b.com"],
            "name": ["A", "B"],
            "company": ["Co1", "Co2"]
        })
        processor = BulkProcessor(config=VerifierConfig())
        dup_df, _ = processor._detect_duplicates(df, "email")
        assert "name" in dup_df.columns
        assert "company" in dup_df.columns
