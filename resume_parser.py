from pathlib import Path


def parse_resume(uploaded_file):
    """Parse PDF/DOCX/TXT uploads in-memory. No external API is used."""
    name = getattr(uploaded_file, "name", "resume")
    suffix = Path(name).suffix.lower()
    data = uploaded_file.read()
    if suffix == ".txt":
        return data.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:
            raise ValueError(f"Could not extract text from PDF: {exc}") from exc
    if suffix == ".docx":
        try:
            from docx import Document
            import io
            doc = Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs).strip()
        except Exception as exc:
            raise ValueError(f"Could not extract text from DOCX: {exc}") from exc
    raise ValueError("Unsupported resume format. Use PDF, DOCX, or TXT.")
