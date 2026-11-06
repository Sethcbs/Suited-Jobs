import io
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app import app as webapp
from app import resume
from tests.helpers import make_pdf

DUMMY = str(Path(__file__).parent.parent / "app" / "dummy_jobs.csv")


@pytest.fixture
def client(monkeypatch):
    webapp._cache.update(source=None, rows=None, time=0.0)
    monkeypatch.setenv("JOBS_CSV", DUMMY)
    return webapp.app.test_client()


def upload(client, data, name="resume.pdf", **fields):
    form = {"resume": (io.BytesIO(data), name), **fields}
    return client.post("/match", data=form, content_type="multipart/form-data")


def test_extracts_text_from_pdf():
    assert "Python and SQL developer" in resume.extract_text(make_pdf("Python and SQL developer"))


@pytest.mark.parametrize("data,message", [
    (b"plain text, not a PDF", "isn't a PDF"),
    (b"%PDF-1.4 but the rest is garbage", "couldn't be read"),
    (make_pdf(""), "No text found"),
])
def test_bad_files_get_a_clear_message(data, message):
    with pytest.raises(resume.ResumeError, match=message):
        resume.extract_text(data)


def test_very_long_text_is_rejected(monkeypatch):
    monkeypatch.setattr(resume, "MAX_CHARS", 5)
    with pytest.raises(resume.ResumeError, match="too much text"):
        resume.extract_text(make_pdf("Python and SQL developer"))


def test_password_protected_pdf_is_rejected():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    out = io.BytesIO()
    writer.write(out)
    with pytest.raises(resume.ResumeError, match="password protected"):
        resume.extract_text(out.getvalue())


def test_match_page_shows_upload_form(client):
    page = client.get("/match").get_data(as_text=True)
    assert 'type="file"' in page and 'enctype="multipart/form-data"' in page


def test_upload_shows_text_and_keywords(client):
    page = upload(client, make_pdf("Python and SQL developer")).get_data(as_text=True)
    assert "Python and SQL developer" in page
    assert '<span class="skill">Python</span>' in page and '<span class="skill">SQL</span>' in page


def test_upload_rejects_non_pdf_with_message(client):
    response = upload(client, b"not a pdf", "resume.txt")
    assert response.status_code == 400 and "isn&#39;t a PDF" in response.get_data(as_text=True)


def test_upload_without_a_file_gets_a_message(client):
    response = client.post("/match", data={}, content_type="multipart/form-data")
    assert response.status_code == 400 and "Please choose a PDF" in response.get_data(as_text=True)


def test_upload_over_the_size_limit_gets_a_message(client):
    response = upload(client, b"%PDF-" + b"0" * resume.MAX_BYTES)
    assert response.status_code == 413 and "too large" in response.get_data(as_text=True)


def test_nothing_is_written_to_disk(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    upload(client, make_pdf("Python developer"))
    assert list(tmp_path.iterdir()) == []
