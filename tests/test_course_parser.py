import pathlib

import pytest

from src import course_parser
from src.course_parser import collect_source_files, load_course_content, parse_content_file, summarize_content_items


def test_collect_source_files(tmp_path):
    file1 = tmp_path / "lecture1.md"
    file1.write_text("# Intro\nFirst lecture.")
    file2 = tmp_path / "notes.txt"
    file2.write_text("Topic A\nDetails.")
    file3 = tmp_path / "slides.docx"
    file3.touch()
    file4 = tmp_path / "reading.pdf"
    file4.touch()

    files = collect_source_files(tmp_path)
    assert len(files) == 4
    assert sorted([f.name for f in files]) == ["lecture1.md", "notes.txt", "reading.pdf", "slides.docx"]


def test_load_and_summarize_content(tmp_path):
    file1 = tmp_path / "lecture1.md"
    file1.write_text("# Intro\nFirst lecture.")
    content_items = load_course_content(tmp_path)
    assert len(content_items) == 1
    assert content_items[0]["name"] == "lecture1"
    summaries = summarize_content_items(content_items)
    assert summaries[0].startswith("lecture1:")


def test_parse_docx_content_file_uses_docx_extractor(tmp_path, monkeypatch):
    docx_file = tmp_path / "lecture.docx"
    docx_file.touch()

    monkeypatch.setattr(course_parser, "_extract_docx_text", lambda _: "Docx lecture content")
    parsed = parse_content_file(docx_file)

    assert parsed == "Docx lecture content"


def test_parse_pdf_content_file_uses_pdf_extractor(tmp_path, monkeypatch):
    pdf_file = tmp_path / "lecture.pdf"
    pdf_file.touch()

    monkeypatch.setattr(course_parser, "_extract_pdf_text", lambda _: "Pdf lecture content")
    parsed = parse_content_file(pdf_file)

    assert parsed == "Pdf lecture content"


def test_parse_content_file_rejects_unsupported_extension(tmp_path):
    unsupported = tmp_path / "notes.csv"
    unsupported.write_text("a,b,c")

    with pytest.raises(ValueError):
        parse_content_file(unsupported)
