"""In-memory resume parsing and validation service for PDF and DOCX uploads."""

import io
import re
import zipfile
from typing import Tuple
from fastapi import UploadFile
import pypdf
import docx

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE = 64 * 1024           # 64 KB
MIN_TEXT_LENGTH = 20
MAX_TEXT_LENGTH = 50000


class ResumeParseError(Exception):
    """Custom exception containing safe, user-friendly error messages."""
    pass


async def read_and_validate_upload(file: UploadFile) -> Tuple[bytes, str]:
    """
    Streams file bytes with strict 5MB chunked threshold enforcement and extension check.
    Aborts reading immediately if the 5MB threshold is exceeded.
    """
    filename = file.filename or "unknown"
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext not in ("pdf", "docx"):
        raise ResumeParseError("Unsupported file type. Only PDF and DOCX files are accepted.")

    buffer = bytearray()
    total_bytes = 0

    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > MAX_FILE_SIZE:
            raise ResumeParseError("File size exceeds the 5 MB limit.")
        buffer.extend(chunk)

    if total_bytes == 0:
        raise ResumeParseError("The uploaded file is empty.")

    return bytes(buffer), ext


def validate_magic_bytes(content: bytes, ext: str) -> None:
    """
    Validates actual file content signature (magic bytes) to prevent extension spoofing.
    PDF: Must start with b'%PDF-'
    DOCX: Must be a valid zip archive starting with b'PK\x03\x04' and containing word/document.xml
    """
    if ext == "pdf":
        if not content.startswith(b"%PDF-"):
            raise ResumeParseError("Invalid file content: Not a valid PDF document.")
    elif ext == "docx":
        if not content.startswith(b"PK\x03\x04"):
            raise ResumeParseError("Invalid file content: Not a valid DOCX document.")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                if "word/document.xml" not in zf.namelist():
                    raise ResumeParseError("Invalid DOCX format: missing Word document structure.")
        except zipfile.BadZipFile:
            raise ResumeParseError("Corrupted or invalid DOCX document.")


def extract_text_from_pdf(content: bytes) -> str:
    """Extracts text from PDF bytes safely."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")
                if decrypted == 0:
                    raise ResumeParseError("Cannot read encrypted or password-protected PDF.")
            except Exception:
                raise ResumeParseError("Cannot read encrypted or password-protected PDF.")

        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except ResumeParseError:
        raise
    except Exception:
        raise ResumeParseError("Failed to extract text from PDF. The file may be corrupted or unreadable.")


def extract_text_from_docx(content: bytes) -> str:
    """Extracts text from DOCX paragraphs and tables safely."""
    try:
        doc = docx.Document(io.BytesIO(content))
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text:
                text_parts.append(paragraph.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        text_parts.append(cell.text)
        return "\n".join(text_parts)
    except ResumeParseError:
        raise
    except Exception:
        raise ResumeParseError("Failed to extract text from DOCX. The file may be corrupted or unreadable.")


def clean_and_validate_extracted_text(raw_text: str) -> str:
    """Cleans extracted text and enforces analysis character length limits (20 - 50,000)."""
    cleaned = re.sub(r"[ \t]+", " ", raw_text)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned).strip()

    char_count = len(cleaned)
    if char_count < MIN_TEXT_LENGTH:
        raise ResumeParseError(
            f"Extracted resume text is too short ({char_count} characters). Minimum {MIN_TEXT_LENGTH} characters required."
        )
    if char_count > MAX_TEXT_LENGTH:
        raise ResumeParseError(
            f"Extracted resume text exceeds limit ({char_count} characters). Maximum {MAX_TEXT_LENGTH} characters allowed."
        )

    return cleaned


async def parse_resume_upload(file: UploadFile) -> Tuple[str, int]:
    """
    Orchestrates upload validation and extraction pipeline:
    1. Chunk-reads up to 5 MB.
    2. Validates extension and magic bytes.
    3. Extracts text in-memory.
    4. Validates text character bounds [20, 50000].
    """
    content, ext = await read_and_validate_upload(file)
    validate_magic_bytes(content, ext)

    if ext == "pdf":
        raw_text = extract_text_from_pdf(content)
    else:
        raw_text = extract_text_from_docx(content)

    clean_text = clean_and_validate_extracted_text(raw_text)
    return clean_text, len(clean_text)
