import os
import json
import shutil
import logging
import traceback
from typing import List, Optional, Callable

# --- Re-introduce Hydra for command-line functionality ---
import hydra
from hydra.core.config_store import ConfigStore
from dataclasses import dataclass, field
from omegaconf import OmegaConf, DictConfig

# --- Optional Dependencies ---
try:
    from pypdf import PdfReader, PdfWriter

    PDF_ENABLED = True
except ImportError:
    PDF_ENABLED = False

try:
    import pytesseract
    from pdf2image import convert_from_path

    OCR_ENABLED = True
except ImportError:
    OCR_ENABLED = False

try:
    from ebooklib import epub
    import ebooklib
    from bs4 import BeautifulSoup

    EPUBCSS_ENABLED = True
except ImportError:
    EPUBCSS_ENABLED = False

try:
    import docx

    DOCX_ENABLED = True
except ImportError:
    DOCX_ENABLED = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import simpleSplit

    REPORTLAB_ENABLED = True
except ImportError:
    REPORTLAB_ENABLED = False

try:
    import tiktoken

    TIKTOKEN_ENABLED = True
except ImportError:
    TIKTOKEN_ENABLED = False

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Hydra Configuration ---
@dataclass
class AppConfig:
    source_directory: str
    output_directory: str
    report_path: str
    max_tokens_per_file: int
    max_file_size_mb: int
    tiktoken_model: str
    use_ocr: bool
    file_types: List[str] = field(default_factory=list)
    poppler_path: Optional[str] = None
    tesseract_cmd: Optional[str] = None


cs = ConfigStore.instance()
cs.store(name="app_config", node=AppConfig)


def extract_text_from_file(file_path: str, cfg: dict, progress_callback: Callable = None) -> str:
    """Extracts text from various file types."""
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == '.epub':
            if progress_callback: progress_callback({'message': 'Extracting EPUB content...'})
            if not EPUBCSS_ENABLED: return ""
            book = epub.read_epub(file_path)
            items = [item.get_content() for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]
            text = "\n\n".join([BeautifulSoup(item, 'html.parser').get_text(separator='\n') for item in items])
        elif ext == '.docx':
            if progress_callback: progress_callback({'message': 'Extracting DOCX content...'})
            if not DOCX_ENABLED: return ""
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        elif ext == '.txt':
            if progress_callback: progress_callback({'message': 'Reading TXT file...'})
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        elif ext == '.pdf':
            if not OCR_ENABLED or not cfg.get('use_ocr', False): return ""
            if cfg.get('tesseract_cmd'):
                pytesseract.pytesseract.tesseract_cmd = cfg['tesseract_cmd']
            if progress_callback: progress_callback({'message': 'Performing OCR...'})
            images = convert_from_path(file_path, poppler_path=cfg.get('poppler_path'), fmt='jpg')
            if progress_callback: progress_callback({'message': 'Extracting text from images...'})
            text = "".join(pytesseract.image_to_string(img) for img in images)
    except Exception as e:
        logging.error(f"Error extracting text from {file_path}: {e}")
    return text


def create_pdf_from_text(text: str, output_path: str):
    if not REPORTLAB_ENABLED:
        logging.error("Cannot create PDF, 'reportlab' is not installed.")
        return
    try:
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        margin, font_name, font_size = 72, "Helvetica", 10
        text_width = width - 2 * margin
        c.setFont(font_name, font_size)
        text_object = c.beginText(margin, height - margin)
        for line in text.splitlines():
            line = line.encode('latin-1', 'replace').decode('latin-1')
            wrapped = simpleSplit(line, font_name, font_size, text_width) or ['']
            for wrapped_line in wrapped:
                text_object.textLine(wrapped_line)
                if text_object.getY() < margin:
                    c.drawText(text_object)
                    c.showPage()
                    c.setFont(font_name, font_size)
                    text_object = c.beginText(margin, height - margin)
        c.drawText(text_object)
        c.save()
    except Exception as e:
        logging.error(f"Failed to write PDF file {output_path}: {e}\n{traceback.format_exc()}")


def count_tokens(text: str, model: str) -> int:
    if not TIKTOKEN_ENABLED:
        return len(text.split())
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        return len(text.split())


def finalize_batch(writer, tokens, sources, count, cfg: dict, report: dict):
    if not writer.pages:
        return PdfWriter(), 0, []
    output_filename = f"knowledge_base_{count}.pdf"
    output_path = os.path.join(cfg['output_directory'], output_filename)
    with open(output_path, "wb") as out_file:
        writer.write(out_file)
    final_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    report["merged_files"].append({
        "output_file": output_filename,
        "source_files": sorted(list(set(sources))),
        "total_tokens": tokens,
        "total_size_mb": round(final_size_mb, 2)
    })
    return PdfWriter(), 0, []


def prepare_knowledge_base(cfg: dict, progress_callback: Callable = None):
    """Main processing function that now accepts a progress_callback."""
    if progress_callback is None:
        # If no callback is provided, default to logging the message.
        progress_callback = lambda data: logging.info(
            f"Processing file {data.get('file_index', 0) + 1}/{data.get('total_files', 0)}: {data.get('filename', '')} - {data.get('message', '')}"
        )

    os.makedirs(cfg['output_directory'], exist_ok=True)
    if not os.path.exists(cfg['source_directory']):
        os.makedirs(cfg['source_directory'])
    if os.path.dirname(cfg['report_path']):
        os.makedirs(os.path.dirname(cfg['report_path']), exist_ok=True)
    temp_dir = os.path.join(cfg['output_directory'], "temp_generated_pdfs")
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    report = {"merged_files": [], "skipped_files": [], "total_files_processed": 0}
    max_bytes = cfg['max_file_size_mb'] * 1024 * 1024
    all_files = sorted(
        [f for f in os.listdir(cfg['source_directory']) if any(f.lower().endswith(ext) for ext in cfg['file_types'])])
    total_files = len(all_files)
    report["total_files_processed"] = total_files

    batch_writer, batch_tokens, batch_sources = PdfWriter(), 0, []
    merged_file_count = 1

    for i, filename in enumerate(all_files):
        progress_callback({
            'file_index': i,
            'total_files': total_files,
            'filename': filename,
            'message': 'Starting to process...'
        })

        file_path = os.path.join(cfg['source_directory'], filename)
        if os.path.getsize(file_path) > max_bytes:
            report["skipped_files"].append(
                {"file": filename, "reason": f"Exceeds max size of {cfg['max_file_size_mb']} MB"})
            continue

        is_native_pdf = False
        if file_path.lower().endswith('.pdf'):
            try:
                reader = PdfReader(file_path)
                if len("".join(p.extract_text() or "" for p in reader.pages[:5])) > 100:
                    is_native_pdf = True
            except Exception:
                is_native_pdf = False

        reader = None
        temp_pdf_to_clean = None
        if is_native_pdf:
            reader = PdfReader(file_path)
        else:
            if file_path.lower().endswith('.pdf') and not cfg.get('use_ocr', False):
                report["skipped_files"].append({"file": filename, "reason": "Scanned PDF found but OCR is disabled"})
                continue

            text = extract_text_from_file(file_path, cfg, progress_callback)
            if not text.strip():
                report["skipped_files"].append({"file": filename, "reason": "No text extracted"})
                continue

            progress_callback({'message': 'Creating temporary PDF...'})
            temp_pdf_path = os.path.join(temp_dir, os.path.splitext(filename)[0] + ".pdf")
            create_pdf_from_text(text, temp_pdf_path)
            if os.path.exists(temp_pdf_path):
                reader = PdfReader(temp_pdf_path)
                temp_pdf_to_clean = temp_pdf_path

        if not reader:
            continue

        progress_callback({'message': 'Merging pages...'})
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
                page_tokens = count_tokens(page_text, cfg['tiktoken_model'])
                if page_tokens > cfg['max_tokens_per_file']:
                    report["skipped_files"].append(
                        {"file": filename, "reason": f"A page was too large ({page_tokens} tokens)."})
                    continue
                if batch_writer.pages and (batch_tokens + page_tokens > cfg['max_tokens_per_file']):
                    batch_writer, batch_tokens, batch_sources = finalize_batch(batch_writer, batch_tokens,
                                                                               batch_sources, merged_file_count, cfg,
                                                                               report)
                    merged_file_count += 1
                batch_writer.add_page(page)
                batch_tokens += page_tokens
                batch_sources.append(filename)
            except Exception as e:
                report["skipped_files"].append({"file": filename, "reason": "Error processing page"})
                continue
        if temp_pdf_to_clean:
            if hasattr(reader, 'stream') and not reader.stream.closed:
                reader.stream.close()
            os.remove(temp_pdf_to_clean)

    if batch_writer.pages:
        finalize_batch(batch_writer, batch_tokens, batch_sources, merged_file_count, cfg, report)

    shutil.rmtree(temp_dir)
    with open(cfg['report_path'], 'w') as f:
        json.dump(report, f, indent=4)

    return report


@hydra.main(config_path="configs", config_name="config", version_base=None)
def main_hydra(cfg: DictConfig):
    config_dict = OmegaConf.to_container(cfg, resolve=True)
    prepare_knowledge_base(config_dict)


if __name__ == "__main__":
    main_hydra()
