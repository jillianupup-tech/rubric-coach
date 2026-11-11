# Read uploaded Word, PDF, and text files — NO API.
import os
from pypdf import PdfReader
import docx

SUPPORTED_TYPES = [".docx", ".pdf", ".txt", ".md"]
MAX_FILE_MB = 10


def read_document(path):
    """Return {"name", "text", "error"} for one uploaded file. Never raises."""
    name = os.path.basename(str(path))
    ext = os.path.splitext(name)[1].lower()
    try:
        if os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
            return {"name": name, "text": "", "error": f"File is larger than {MAX_FILE_MB} MB."}
        if ext in (".txt", ".md"):
            with open(path, "rb") as f:
                raw = f.read()
            for enc in ("utf-8-sig", "utf-16", "latin-1"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
        elif ext == ".docx":
            d = docx.Document(path)
            parts = [p.text for p in d.paragraphs]
            for table in d.tables:  # rubrics are often tables
                for row in table.rows:
                    cells = []
                    for cell in row.cells:
                        t = cell.text.strip()
                        if t and (not cells or cells[-1] != t):  # skip repeated merged cells
                            cells.append(t)
                    if cells:
                        parts.append(" | ".join(cells))
            text = "\n".join(parts)
        elif ext == ".pdf":
            reader = PdfReader(path)
            if reader.is_encrypted:
                return {"name": name, "text": "", "error": "The PDF is password-protected."}
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        elif ext == ".doc":
            return {"name": name, "text": "", "error": "Old .doc files are not supported. Save it as .docx or PDF."}
        else:
            return {"name": name, "text": "", "error": f"Unsupported file type '{ext}'. Use .docx, .pdf, or .txt."}
    except Exception as e:
        return {"name": name, "text": "", "error": f"Could not read this file ({type(e).__name__})."}
    text = text.replace("\r\n", "\n").replace("\x00", "").strip()
    if not text:
        return {"name": name, "text": "", "error": "No text found. If this is a scanned or photographed document, "
                                                    "paste the text instead."}
    return {"name": name, "text": text, "error": None}

