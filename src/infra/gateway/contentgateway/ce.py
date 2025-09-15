from typing import Any

from ...pdf.pdfparser import parse_pdf


def parse_ce_content(content: bytes) -> dict[str, Any]:

    pdf_file = parse_pdf(content)

    return {"pdf": pdf_file}
