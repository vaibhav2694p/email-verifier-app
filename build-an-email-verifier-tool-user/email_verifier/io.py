from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd


ColumnRole = Literal["email", "name", "company"]


@dataclass(frozen=True)
class ColumnMapping:
    email: str
    name: str | None = None
    company: str | None = None


COLUMN_ALIASES: dict[ColumnRole, tuple[str, ...]] = {
    "email": (
        "email",
        "emailaddress",
        "workemail",
        "businessemail",
        "primaryemail",
        "contactemail",
    ),
    "name": (
        "name",
        "fullname",
        "contactname",
        "person",
        "prospect",
        "leadname",
    ),
    "company": (
        "company",
        "companyname",
        "organization",
        "organisation",
        "account",
        "employer",
    ),
}


def read_uploaded_table(uploaded_file: object) -> pd.DataFrame:
    filename = getattr(uploaded_file, "name", "")
    extension = Path(filename).suffix.lower()

    try:
        if extension == ".csv":
            dataframe = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
        elif extension == ".xlsx":
            dataframe = pd.read_excel(uploaded_file, dtype=str, keep_default_na=False)
        else:
            raise ValueError("Upload a CSV or XLSX file.")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read {filename or 'uploaded file'}: {exc}") from exc

    dataframe.columns = deduplicate_columns(
        [str(column).strip() for column in dataframe.columns]
    )
    dataframe = dataframe.fillna("")

    if dataframe.empty:
        raise ValueError("The uploaded file has no rows.")
    if not dataframe.columns.any():
        raise ValueError("The uploaded file has no columns.")

    return dataframe


def infer_column(columns: list[str], role: ColumnRole) -> str | None:
    aliases = COLUMN_ALIASES[role]
    normalized_columns = {normalize_column_name(column): column for column in columns}

    for alias in aliases:
        if alias in normalized_columns:
            return normalized_columns[alias]

    for normalized, original in normalized_columns.items():
        if any(alias in normalized for alias in aliases):
            return original

    return None


def get_default_column_index(columns: list[str], guessed_column: str | None) -> int:
    if guessed_column and guessed_column in columns:
        return columns.index(guessed_column) + 1
    return 0


def normalize_column_name(column_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(column_name).strip().lower())


def clean_cell(value: object) -> str:
    return str(value or "").strip()


def deduplicate_columns(columns: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    deduplicated: list[str] = []

    for index, column in enumerate(columns, start=1):
        base_name = column or f"Column {index}"
        seen_count = counts.get(base_name, 0) + 1
        counts[base_name] = seen_count
        deduplicated.append(base_name if seen_count == 1 else f"{base_name} ({seen_count})")

    return deduplicated
