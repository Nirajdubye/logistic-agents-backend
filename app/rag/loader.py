import os
from pypdf import PdfReader


def load_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_text_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        raise ValueError("python-docx is required to read .docx files. Install it via pip install python-docx")


def load_document(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext in (".txt", ".md"):
        return load_text_file(file_path)
    elif ext == ".docx":
        return load_docx(file_path)
    raise ValueError(f"Unsupported file type: {ext}")


def load_documents_from_folder(folder_path: str) -> list[dict]:
    documents = []
    if not os.path.exists(folder_path):
        return documents

    for filename in sorted(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".pdf", ".txt", ".md", ".docx"):
            continue
        try:
            documents.append({
                "source_file": filename,
                "content": load_document(file_path),
            })
        except Exception as e:
            print(f"[loader] Warning: could not load {filename}: {e}")
    return documents