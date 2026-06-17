from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from fpdf import FPDF


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    return output.getvalue()


def dataframe_to_pdf_bytes(df: pd.DataFrame) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Email Verification Results", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    cols = list(df.columns)
    col_width = max(25, int(180 / len(cols))) if cols else 180

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_fill_color(230, 230, 230)
    for col in cols:
        pdf.cell(col_width, 7, col[:20], border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 6)
    for _, row in df.iterrows():
        overall = str(row.get("Overall Status", ""))
        if overall == "VALID":
            pdf.set_fill_color(200, 255, 200)
        elif overall == "RISKY":
            pdf.set_fill_color(255, 255, 200)
        else:
            pdf.set_fill_color(255, 200, 200)

        y_before = pdf.get_y()
        if y_before > 265:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(230, 230, 230)
            for col in cols:
                pdf.cell(col_width, 7, col[:20], border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 6)

        for col in cols:
            val = str(row.get(col, ""))[:25]
            pdf.cell(col_width, 6, val, border=1, align="C", fill=True)
        pdf.ln()

    raw = pdf.output(dest="S")
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw.encode("latin-1", errors="replace")
