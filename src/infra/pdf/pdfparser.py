from io import BytesIO
import pdfplumber
import PyPDF2


class PDFParseException(Exception):
    pass


def parse_pdf(data: bytes) -> list[str]:
    """Tenta extrair texto com pdfplumber, se falhar usa PyPDF2 como fallback."""
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    except Exception:
        try:
            reader = PyPDF2.PdfReader(BytesIO(data))
            return [page.extract_text() or "" for page in reader.pages]
        except Exception as e:
            raise PDFParseException from e