"""Unit and integration tests for PDF and DOCX resume upload and text extraction."""

from pathlib import Path
import sys
import io
import docx
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

client = TestClient(app)


def make_sample_pdf(text: str = "Experienced Python Engineer with extensive knowledge of FastAPI and PostgreSQL.") -> bytes:
    """Generates a valid in-memory PDF byte string containing the given text."""
    stream_content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET"
    stream_len = len(stream_content)

    header = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >> endobj\n"
    )
    stream_obj = f"4 0 obj << /Length {stream_len} >> stream\n{stream_content}\nendstream endobj\n".encode("latin1")
    footer = (
        b"xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n"
        b"0000000117 00000 n \n0000000288 00000 n \n"
        b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n393\n%%EOF"
    )
    return header + stream_obj + footer


def make_sample_docx(text: str = "Experienced Full-Stack Developer proficient in React, Python, and SQL databases.") -> bytes:
    """Generates a valid in-memory DOCX byte string containing the given text."""
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_upload_valid_pdf():
    pdf_bytes = make_sample_pdf("Experienced Python Engineer with extensive knowledge of FastAPI.")
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("my_resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "my_resume.pdf"
    assert "Experienced Python Engineer" in data["extracted_text"]
    assert data["character_count"] >= 20


def test_upload_valid_docx():
    docx_bytes = make_sample_docx("Staff Backend Developer with 8 years of experience building distributed systems.")
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("candidate_profile.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "candidate_profile.docx"
    assert "Staff Backend Developer" in data["extracted_text"]
    assert data["character_count"] >= 20


def test_upload_invalid_file_extension():
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("notes.txt", b"Some raw plain text resume...", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_spoofed_pdf_magic_bytes():
    # File named .pdf but containing plain text instead of %PDF- header
    fake_pdf = b"This is just plain text masquerading as a PDF file."
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("spoofed.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    assert "Not a valid PDF" in response.json()["detail"]


def test_upload_spoofed_docx_magic_bytes():
    # File named .docx but not a zip file
    fake_docx = b"This is not a zip archive for docx."
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("spoofed.docx", fake_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400
    assert "Not a valid DOCX" in response.json()["detail"]


def test_upload_empty_file():
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_text_too_short():
    # Valid docx structure but content is under 20 chars
    short_docx = make_sample_docx("Too short")
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("short.docx", short_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400
    assert "too short" in response.json()["detail"].lower()


def test_upload_exceeds_5mb_limit():
    # 5.5 MB of dummy data
    large_data = b"%PDF-" + b"0" * (5500 * 1024)
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("huge.pdf", large_data, "application/pdf")},
    )
    assert response.status_code == 400
    assert "exceeds the 5 MB limit" in response.json()["detail"]


def test_upload_corrupted_docx_zip():
    # Starts with PK header but corrupted zip stream
    corrupt_docx = b"PK\x03\x04corrupted_data_that_fails_zip_decompression"
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("corrupt.docx", corrupt_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400
    assert "Corrupted or invalid DOCX" in response.json()["detail"]
