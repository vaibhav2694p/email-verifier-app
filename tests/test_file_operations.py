from io import BytesIO, StringIO

import pandas as pd
import pytest
from pandas.errors import EmptyDataError


class TestFileOperations:
    def test_csv_read(self):
        csv_data = "email,name\nuser@test.com,John\nuser2@test.com,Jane"
        df = pd.read_csv(StringIO(csv_data))
        assert len(df) == 2
        assert "email" in df.columns

    def test_xlsx_read(self):
        df = pd.DataFrame({"email": ["a@test.com", "b@test.com"], "name": ["A", "B"]})
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False)
        buf.seek(0)
        df2 = pd.read_excel(buf)
        assert len(df2) == 2

    def test_empty_csv(self):
        with pytest.raises(EmptyDataError):
            pd.read_csv(StringIO(""))

    def test_missing_email_column(self):
        df = pd.DataFrame({"name": ["John", "Jane"], "phone": ["123", "456"]})
        email_cols = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower() or "mail" in c.lower()]
        assert len(email_cols) == 0

    def test_null_values_in_email_column(self):
        df = pd.DataFrame({"email": ["a@test.com", None, "", "b@test.com"]})
        non_null = df["email"].dropna()
        assert len(non_null) == 3

    def test_large_dataset(self):
        n = 1000
        df = pd.DataFrame({
            "email": [f"user{i}@test.com" for i in range(n)],
            "name": [f"User {i}" for i in range(n)]
        })
        assert len(df) == n
