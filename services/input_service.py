from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import BinaryIO

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt"}
FORMULA_PREFIXES = ("=", "+", "-", "@")


@dataclass
class ParsedInput:
    dataframe: pd.DataFrame
    file_name: str = ""
    upload_date: str = ""
    warnings: list[str] | None = None


def parse_manual_paste(text: str) -> pd.DataFrame:
    emails = _split_text_emails(text)
    return pd.DataFrame({"Email": emails})


def parse_upload(file_obj: BinaryIO, file_name: str, max_rows: int = 100000) -> ParsedInput:
    ext = _extension(file_name)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {ext}")

    warnings: list[str] = []
    try:
        if ext == ".csv":
            df = pd.read_csv(file_obj)
        elif ext in {".xlsx", ".xls"}:
            df = pd.read_excel(file_obj, engine="openpyxl" if ext == ".xlsx" else None)
        else:
            raw = file_obj.read()
            text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else str(raw)
            df = pd.DataFrame({"Email": _split_text_emails(text)})
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid file encoding; expected UTF-8 compatible text") from exc
    except Exception as exc:
        if ext in {".xlsx", ".xls"}:
            raise ValueError("Corrupted or unreadable Excel file") from exc
        raise

    validate_dataframe(df, max_rows=max_rows)
    formula_cols = _formula_columns(df)
    if formula_cols:
        warnings.append("Formula-like cells detected in columns: " + ", ".join(formula_cols))

    return ParsedInput(df, file_name=file_name, upload_date=datetime.now(timezone.utc).isoformat(), warnings=warnings)


def validate_dataframe(df: pd.DataFrame, max_rows: int = 100000) -> None:
    if df is None or df.empty:
        raise ValueError("Empty file")
    if len(df) > max_rows:
        raise ValueError(f"Too many rows: {len(df)} > {max_rows}")
    columns = [str(c) for c in df.columns]
    if len(columns) != len(set(columns)):
        raise ValueError("Duplicate column names are not allowed")
    if not columns:
        raise ValueError("Missing columns")


def detect_email_column(df: pd.DataFrame) -> str:
    for col in df.columns:
        if str(col).strip().lower() in {"email", "email address", "e-mail", "mail"}:
            return str(col)
    for col in df.columns:
        sample = df[col].dropna().astype(str).head(20)
        if sample.str.contains("@", regex=False).any():
            return str(col)
    raise ValueError("Missing email column")


def _split_text_emails(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    reader = csv.reader(io.StringIO(text), delimiter=",")
    tokens: list[str] = []
    for row in reader:
        for cell in row:
            tokens.extend(re.split(r"[;\t\r\n]+", cell))
    return [t.strip() for t in tokens if t.strip()]


def _extension(file_name: str) -> str:
    return "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""


def _formula_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for col in df.columns:
        values = df[col].dropna().astype(str).head(100)
        if values.map(lambda v: v.startswith(FORMULA_PREFIXES)).any():
            cols.append(str(col))
    return cols
