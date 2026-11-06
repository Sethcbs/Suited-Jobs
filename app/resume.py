"""Read an uploaded PDF resume (FR-11). Works on bytes in memory, so nothing is stored (NFR-4)."""
import io
import logging

from pypdf import PdfReader

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 30000

logging.getLogger("pypdf").setLevel(logging.ERROR)  # bad PDFs are reported to the person instead


class ResumeError(ValueError):
    """The upload can't be used. The message is safe to show to the person."""


def extract_text(data):
    """Return the text of a PDF given its bytes, or raise ResumeError."""
    if not data.startswith(b"%PDF-"):
        raise ResumeError("That file isn't a PDF. Please upload a PDF resume.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ResumeError("That PDF is password protected. Please upload an unprotected copy.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except ResumeError:
        raise
    except Exception as exc:  # pypdf raises many types on damaged files
        raise ResumeError("That PDF couldn't be read. It may be damaged.") from exc
    if not text:
        raise ResumeError("No text found in that PDF. A scanned resume has no text layer to read.")
    if len(text) > MAX_CHARS:  # it goes to the model on every request, so this protects the budget
        raise ResumeError("That PDF has too much text for a resume. Please upload a shorter one.")
    return text
