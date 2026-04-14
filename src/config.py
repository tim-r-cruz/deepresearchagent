import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = ROOT.parent / "content"
DEFAULT_OUTPUT_DIR = ROOT.parent / "output"
SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".docx", ".pdf"}
SLIDE_TITLE_STYLE = {
    "font_name": "Calibri",
    "font_size": 40,
    "bold": True,
}
SLIDE_BODY_STYLE = {
    "font_name": "Calibri",
    "font_size": 24,
}
