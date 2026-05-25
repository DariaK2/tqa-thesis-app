import logging
import zipfile
import xml.etree.ElementTree as ET
import subprocess
import shutil
import sys
from io import BytesIO
from config import MIN_EXTRACTED_TEXT_LENGTH, AUTO_INSTALL_OCR_DEPS

logger = logging.getLogger(__name__)


class TextExtractionError(ValueError):
    pass


class OCRUnavailableError(TextExtractionError):
    pass


def _run_command(command):
    return subprocess.run(command, capture_output=True, text=True)


def _pip_install(packages):
    cmd = [sys.executable, "-m", "pip", "install", *packages]
    result = _run_command(cmd)
    if result.returncode != 0:
        raise OCRUnavailableError(
            f"Failed to auto-install Python OCR dependencies: {' '.join(packages)}. "
            f"stderr: {result.stderr[:500]}"
        )


def _try_install_system_package_macos():
    if shutil.which("brew"):
        if not shutil.which("tesseract"):
            result = _run_command(["brew", "install", "tesseract"])
            if result.returncode != 0:
                raise OCRUnavailableError(
                    f"Failed to auto-install tesseract via Homebrew. stderr: {result.stderr[:500]}"
                )
        if not shutil.which("pdftoppm"):
            result = _run_command(["brew", "install", "poppler"])
            if result.returncode != 0:
                raise OCRUnavailableError(
                    f"Failed to auto-install poppler via Homebrew. stderr: {result.stderr[:500]}"
                )
        return
    raise OCRUnavailableError("Homebrew not found. Install Homebrew or manually install tesseract and poppler.")


def _ensure_ocr_dependencies():
    missing_python = []
    try:
        import pdf2image  # noqa: F401
    except Exception:
        missing_python.append("pdf2image")
    try:
        import pytesseract  # noqa: F401
    except Exception:
        missing_python.append("pytesseract")
    try:
        from PIL import Image  # noqa: F401
    except Exception:
        missing_python.append("Pillow")

    if missing_python:
        if not AUTO_INSTALL_OCR_DEPS:
            raise OCRUnavailableError(f"Missing OCR Python dependencies: {', '.join(missing_python)}")
        _pip_install(missing_python)

    if not shutil.which("tesseract") or not shutil.which("pdftoppm"):
        if not AUTO_INSTALL_OCR_DEPS:
            raise OCRUnavailableError("Missing system OCR dependencies: tesseract and poppler (pdftoppm) required.")
        if sys.platform == "darwin":
            _try_install_system_package_macos()
        else:
            raise OCRUnavailableError(
                "Auto-installation of system OCR dependencies is currently only implemented for macOS with Homebrew. "
                "On Linux/Windows, install tesseract and poppler manually."
            )


def _validate_text(text, filetype):
    text = (text or "").strip()
    if len(text) < MIN_EXTRACTED_TEXT_LENGTH:
        raise TextExtractionError(f"Failed to extract sufficient text from {filetype} file.")
    return text


def extract_from_txt(file_storage):
    file_storage.stream.seek(0)
    raw = file_storage.read()
    text = raw.decode("utf-8", errors="ignore")
    return _validate_text(text, "TXT")


def extract_from_md(file_storage):
    file_storage.stream.seek(0)
    raw = file_storage.read()
    text = raw.decode("utf-8", errors="ignore")
    return _validate_text(text, "MD")


def _ocr_pdf(file_bytes):
    _ensure_ocr_dependencies()
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except Exception as e:
        raise OCRUnavailableError(f"OCR dependencies unavailable after install attempt: {e}")

    try:
        images = convert_from_bytes(file_bytes)
        parts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="rus+eng+deu")
            if text:
                parts.append(text)
        text = "\n".join(parts).strip()
        return _validate_text(text, "PDF-OCR")
    except Exception as e:
        raise TextExtractionError(f"Failed to perform OCR on PDF: {e}")


def extract_from_pdf(file_storage):
    try:
        from pypdf import PdfReader
        file_storage.stream.seek(0)
        file_bytes = file_storage.read()
        reader = PdfReader(BytesIO(file_bytes))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        if len(text) >= MIN_EXTRACTED_TEXT_LENGTH:
            return text
        return _ocr_pdf(file_bytes)
    except OCRUnavailableError:
        raise
    except Exception as e:
        raise TextExtractionError(f"Failed to read PDF: {e}")


def extract_from_docx(file_storage):
    try:
        file_storage.stream.seek(0)
        with zipfile.ZipFile(file_storage) as z:
            xml_content = z.read("word/document.xml")
        root = ET.fromstring(xml_content)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = [node.text for node in root.findall(".//w:t", ns) if node.text]
        text = "\n".join(texts).strip()
        return _validate_text(text, "DOCX")
    except Exception as e:
        raise TextExtractionError(f"Failed to read DOCX: {e}")


def extract_text_from_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return ""
    
    filename = file_storage.filename.lower()
    
    if filename.endswith(".txt"):
        return extract_from_txt(file_storage)
    if filename.endswith(".md"):
        return extract_from_md(file_storage)
    if filename.endswith(".pdf"):
        return extract_from_pdf(file_storage)
    if filename.endswith(".docx"):
        return extract_from_docx(file_storage)
    
    raise TextExtractionError("Only .txt, .md, .docx, .pdf files are supported.")
