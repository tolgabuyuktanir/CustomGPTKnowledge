import os
import json
import hydra
from hydra.core.config_store import ConfigStore
from dataclasses import dataclass, field
from typing import List, Tuple
import tiktoken
import logging
import traceback
import shutil

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


cs = ConfigStore.instance()
cs.store(name="app_config", node=AppConfig)


# --- Text Extraction and File Processing Functions ---

def extract_text_from_file(file_path: str, cfg: AppConfig) -> str:
    """Extracts text from various file types to be converted into a temporary PDF."""
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == '.epub':
            if not EPUBCSS_ENABLED: return ""
            book = epub.read_epub(file_path)
            items = [item.get_content() for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]
            text = "\n\n".join([BeautifulSoup(item, 'html.parser').get_text(separator='\n') for item in items])
        elif ext == '.docx':
            if not DOCX_ENABLED: return ""
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        elif ext == '.pdf':  # For scanned PDFs
            print(ext)
            if not OCR_ENABLED: return ""
            # Set Tesseract command if specified in config
            if cfg.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = cfg.tesseract_cmd
            logging.info(f"Performing OCR on {os.path.basename(file_path)}...")
            images = convert_from_path(file_path, poppler_path="/opt/homebrew/opt/poppler/bin", fmt='jpg')
            # convert images to grayscale for better OCR results
            print("Converting PDF to images for OCR...")
            text = "".join(pytesseract.image_to_string(img) for img in images)
    except Exception as e:
        logging.error(f"Error extracting text from {file_path}: {e}")
    return text


# --- PDF Creation and Merging ---

def create_pdf_from_text(text: str, output_path: str):
    """Creates a new searchable PDF file from a string of text."""
    if not REPORTLAB_ENABLED:
        logging.error(f"Cannot create PDF for {output_path}, 'reportlab' is not installed.")
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


# --- Core Logic ---

def count_tokens(text: str, model: str) -> int:
    """Counts tokens using tiktoken."""
    try:
        return len(tiktoken.encoding_for_model(model).encode(text))
    except Exception:
        return 0


def finalize_batch(writer, tokens, sources, size, count, cfg, report):
    """Helper function to write a completed batch to a file and update the report."""
    if not writer.pages:
        return PdfWriter(), 0, [], 0  # Return empty state if there's nothing to write

    output_filename = f"knowledge_base_{count}.pdf"
    output_path = os.path.join(cfg.output_directory, output_filename)

    with open(output_path, "wb") as out_file:
        writer.write(out_file)

    final_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    report["merged_files"].append({
        "output_file": output_filename,
        "source_files": sorted(list(set(sources))),
        "total_tokens": tokens,
        "total_size_mb": round(final_size_mb, 2)
    })
    logging.info(f"Finalized batch {count} as {output_filename} ({tokens} tokens, {final_size_mb:.2f} MB)")
    return PdfWriter(), 0, [], 0


@hydra.main(config_path="configs", config_name="config", version_base=None)
def prepare_knowledge_base(cfg: AppConfig):
    """Main function to process files and consolidate them into PDFs using a streaming approach."""
    os.makedirs(cfg.output_directory, exist_ok=True)
    os.makedirs(cfg.source_directory, exist_ok=True)
    if os.path.dirname(cfg.report_path):
        os.makedirs(os.path.dirname(cfg.report_path), exist_ok=True)

    temp_dir = os.path.join(cfg.output_directory, "temp_generated_pdfs")
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    report = {"merged_files": [], "skipped_files": [], "total_files_processed": 0}
    max_bytes = cfg.max_file_size_mb * 1024 * 1024

    all_files = [f for f in os.listdir(cfg.source_directory) if any(f.lower().endswith(ext) for ext in cfg.file_types)]
    report["total_files_processed"] = len(all_files)

    # --- Streaming Batch Processing ---
    batch_writer, batch_tokens, batch_sources, batch_size = PdfWriter(), 0, [], 0
    merged_file_count = 1

    for filename in sorted(all_files):
        file_path = os.path.join(cfg.source_directory, filename)

        if os.path.getsize(file_path) > max_bytes:
            report["skipped_files"].append(
                {"file": filename, "reason": f"Exceeds max size of {cfg.max_file_size_mb} MB"})
            continue

        # Determine if the PDF is native text-based or needs conversion
        is_native_pdf = False
        if file_path.lower().endswith('.pdf'):
            try:
                reader = PdfReader(file_path)
                # Simple heuristic: if we can extract more than a little text, it's native.
                if len("".join(p.extract_text() or "" for p in reader.pages[:5])) > 100:
                    is_native_pdf = True
            except Exception:
                is_native_pdf = False

        # Get a reader object for the page stream
        reader = None
        temp_pdf_to_clean = None
        if is_native_pdf:
            reader = PdfReader(file_path)
        else:
            # For non-native files, convert the entire text to a temporary PDF
            if file_path.lower().endswith('.pdf') and not cfg.use_ocr:
                report["skipped_files"].append({"file": filename, "reason": "Scanned PDF found but OCR is disabled"})
                logging.warning(f"Skipping scanned PDF {filename} because use_ocr is false.")
                continue

            text = extract_text_from_file(file_path, cfg)
            if not text.strip():
                report["skipped_files"].append({"file": filename, "reason": "No text extracted or file is unreadable"})
                continue

            temp_pdf_path = os.path.join(temp_dir, os.path.splitext(filename)[0] + ".pdf")
            create_pdf_from_text(text, temp_pdf_path)

            if os.path.exists(temp_pdf_path):
                reader = PdfReader(temp_pdf_path)
                temp_pdf_to_clean = temp_pdf_path

        if not reader:
            logging.warning(f"Could not create a readable PDF from {filename}. Skipping.")
            continue

        # Stream pages from the reader into batches
        for page in reader.pages:
            page_text = page.extract_text() or ""
            page_tokens = count_tokens(page_text, cfg.tiktoken_model)

            # This is a critical edge case. If a single page is larger than the max token limit,
            # it must be skipped as it cannot be split without losing its format.
            if page_tokens > cfg.max_tokens_per_file:
                logging.warning(
                    f"A single page in '{filename}' has {page_tokens} tokens, which exceeds the limit of {cfg.max_tokens_per_file}. This page will be skipped.")
                report["skipped_files"].append(
                    {"file": filename, "reason": f"A single page was too large ({page_tokens} tokens)."})
                continue

            # If the current page doesn't fit, finalize the current batch and start a new one
            if batch_writer.pages and (batch_tokens + page_tokens > cfg.max_tokens_per_file):
                batch_writer, batch_tokens, batch_sources, batch_size = finalize_batch(
                    batch_writer, batch_tokens, batch_sources, batch_size, merged_file_count, cfg, report
                )
                merged_file_count += 1

            # Add the page to the current batch
            batch_writer.add_page(page)
            batch_tokens += page_tokens
            batch_sources.append(filename)
            # Note: We don't track batch_size here as it's complex. The initial file size check is the main guard.

        if temp_pdf_to_clean:
            # We need to close the reader before deleting the file on Windows
            reader.stream.close()
            os.remove(temp_pdf_to_clean)

    # Finalize the very last batch
    if batch_writer.pages:
        finalize_batch(batch_writer, batch_tokens, batch_sources, batch_size, merged_file_count, cfg, report)

    # --- Finalize and clean up ---
    shutil.rmtree(temp_dir)
    with open(cfg.report_path, 'w') as f:
        json.dump(report, f, indent=4)

    logging.info(f"Knowledge base preparation complete. Report generated at {cfg.report_path}")


if __name__ == "__main__":
    prepare_knowledge_base()
