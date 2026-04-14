import pathlib
from typing import List

from docx import Document
from pypdf import PdfReader

from .config import SUPPORTED_EXTENSIONS


def collect_source_files(source_dir: pathlib.Path) -> List[pathlib.Path]:
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    files = [p for p in sorted(source_dir.iterdir()) if p.suffix.lower() in SUPPORTED_EXTENSIONS and p.is_file()]
    return files


def parse_content_file(file_path: pathlib.Path) -> str:
    extension = file_path.suffix.lower()

    if extension in {".md", ".markdown", ".txt"}:
        text = file_path.read_text(encoding="utf-8")
    elif extension == ".docx":
        text = _extract_docx_text(file_path)
    elif extension == ".pdf":
        text = _extract_pdf_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    return text.strip()


def _extract_docx_text(file_path: pathlib.Path) -> str:
    document = Document(file_path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)


def _extract_pdf_text(file_path: pathlib.Path) -> str:
    reader = PdfReader(str(file_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(text for text in pages if text)


def load_course_content(source_dir: pathlib.Path) -> List[dict]:
    files = collect_source_files(source_dir)
    content_items = []
    for file_path in files:
        body = parse_content_file(file_path)
        content_items.append({
            "path": file_path,
            "name": file_path.stem,
            "body": body,
        })
    return content_items


def summarize_content_items(content_items: List[dict]) -> List[str]:
    summaries = []
    for item in content_items:
        lines = [line.strip() for line in item["body"].splitlines() if line.strip()]
        if lines:
            first_line = lines[0]
            summaries.append(f"{item['name']}: {first_line[:120]}")
        else:
            summaries.append(f"{item['name']}: (empty file)")
    return summaries
