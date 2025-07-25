import os
import json
import hydra
from hydra.core.config_store import ConfigStore
from dataclasses import dataclass
from pypdf import PdfReader, PdfWriter
import tiktoken
import logging

# --- OCR Dependencies ---
# The script uses pytesseract and pdf2image for OCR capabilities.
# These need to be installed: pip install pytesseract pdf2image Pillow
# IMPORTANT: You must also install the Tesseract-OCR engine on your system.
# See: https://github.com/tesseract-ocr/tesseract for installation instructions.
try:
    import pytesseract
    from pdf2image import convert_from_path

    OCR_ENABLED = True
except ImportError:
    OCR_ENABLED = False
    logging.warning("pytesseract or pdf2image not found. OCR functionality will be disabled.")
    logging.warning("To enable OCR, run: pip install pytesseract pdf2image Pillow")

# --- Setup Logging ---
# Configure logging to provide informative output.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Hydra Configuration ---
# Define a dataclass for structured configuration. This makes the configuration type-safe and self-documenting.
# To use an external YAML file (e.g., configs/config.yaml), you would change the @hydra.main decorator.
@dataclass
class AppConfig:
    source_directory: str = "source_pdfs"
    output_directory: str = "outputs/merged_pdfs"
    report_path: str = "outputs/report.json"
    max_tokens_per_file: int = 2000000
    tiktoken_model: str = "gpt-4"
    use_ocr: bool = True


# Register the configuration with Hydra's ConfigStore.
cs = ConfigStore.instance()
cs.store(name="app_config", node=AppConfig)


# --- Core Functions ---

def count_tokens(text: str, model: str) -> int:
    """
    Counts the number of tokens in a given text string using the tiktoken library.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logging.error(f"Error counting tokens: {e}")
        return 0


def perform_ocr(file_path: str) -> str:
    """
    Performs OCR on a PDF file by converting its pages to images and extracting text.

    Args:
        file_path: The path to the PDF file.

    Returns:
        The extracted text from the entire PDF.
    """
    logging.info(f"Attempting OCR on {os.path.basename(file_path)}...")
    try:
        images = convert_from_path(file_path)
        ocr_text = ""
        for i, image in enumerate(images):
            logging.info(f"  - Processing page {i + 1}/{len(images)}")
            ocr_text += pytesseract.image_to_string(image) + "\n"
        logging.info(f"OCR successful for {os.path.basename(file_path)}.")
        return ocr_text
    except pytesseract.TesseractNotFoundError:
        logging.error("Tesseract is not installed or not in your PATH. OCR failed.")
        logging.error("Please install Tesseract: https://github.com/tesseract-ocr/tesseract")
        return ""
    except Exception as e:
        logging.error(f"An error occurred during OCR for {file_path}: {e}")
        return ""


def process_pdf(file_path: str, model: str, use_ocr: bool) -> tuple[int, bool]:
    """
    Processes a single PDF file to extract text and count tokens.
    If the PDF appears scanned, it attempts to use OCR.

    Args:
        file_path: The path to the PDF file.
        model: The tiktoken model for token counting.
        use_ocr: A boolean flag to enable or disable OCR.

    Returns:
        A tuple containing the token count and a boolean indicating if the PDF is unreadable.
    """
    text = ""
    is_unreadable = False
    try:
        reader = PdfReader(file_path)
        if not reader.pages:
            logging.warning(f"Skipping empty PDF: {file_path}")
            return 0, False

        text = "".join(page.extract_text() or "" for page in reader.pages)

        # Heuristic to detect a scanned PDF. If text is sparse, try OCR.
        if len(text.strip()) < 100 and use_ocr and OCR_ENABLED:
            logging.warning(f"PDF seems scanned or text-light: {file_path}. Attempting OCR.")
            text = perform_ocr(file_path)
            if not text:
                logging.warning(f"OCR failed or produced no text for {file_path}.")
                is_unreadable = True
        elif len(text.strip()) < 100:
            is_unreadable = True  # No OCR, so it's unreadable

        token_count = count_tokens(text, model) if text else 0
        return token_count, is_unreadable
    except Exception as e:
        logging.error(f"Could not read PDF {file_path}: {e}")
        return 0, True  # Treat as unreadable on error


def merge_pdfs(pdf_files: list[str], output_path: str):
    """
    Merges a list of PDF files into a single PDF document.
    """
    pdf_writer = PdfWriter()
    try:
        for file_path in pdf_files:
            try:
                pdf_reader = PdfReader(file_path)
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            except Exception as e:
                logging.error(f"Could not process {file_path} during merge: {e}")

        with open(output_path, "wb") as out_file:
            pdf_writer.write(out_file)
        logging.info(f"Successfully merged {len(pdf_files)} files into {output_path}")
    except Exception as e:
        logging.error(f"Failed to write merged PDF {output_path}: {e}")


# --- Main Application Logic ---

@hydra.main(config_path=None, config_name="app_config", version_base=None)
def prepare_knowledge_base(cfg: AppConfig):
    """
    Main function to prepare the knowledge base by processing and merging PDFs.
    It is decorated with Hydra to manage configuration.
    """
    # Create output directories if they don't exist
    os.makedirs(cfg.output_directory, exist_ok=True)
    os.makedirs(cfg.source_directory, exist_ok=True)  # Also ensure source exists
    # If report path is nested, create its parent directory
    if os.path.dirname(cfg.report_path):
        os.makedirs(os.path.dirname(cfg.report_path), exist_ok=True)

    report = {
        "merged_files": [],
        "skipped_files": [],
        "total_pdfs_processed": 0,
    }

    pdf_batch = []
    current_batch_tokens = 0
    merged_file_count = 1

    source_files = sorted([f for f in os.listdir(cfg.source_directory) if f.lower().endswith('.pdf')])
    report["total_pdfs_processed"] = len(source_files)

    if not source_files:
        logging.warning(f"No PDF files found in the source directory: {cfg.source_directory}")
        with open(cfg.report_path, 'w') as f: json.dump(report, f, indent=4)
        logging.info(f"Report generated at {cfg.report_path}")
        return

    for filename in source_files:
        file_path = os.path.join(cfg.source_directory, filename)
        token_count, is_unreadable = process_pdf(file_path, cfg.tiktoken_model, cfg.use_ocr)

        if is_unreadable:
            report["skipped_files"].append({"file": filename, "reason": "Unreadable or failed OCR"})
            continue

        if token_count == 0:
            report["skipped_files"].append({"file": filename, "reason": "Empty or no text found"})
            continue

        if current_batch_tokens + token_count > cfg.max_tokens_per_file and pdf_batch:
            output_filename = f"merged_output_{merged_file_count}.pdf"
            output_path = os.path.join(cfg.output_directory, output_filename)

            logging.info(
                f"Merging batch {merged_file_count} with {len(pdf_batch)} PDFs and {current_batch_tokens} tokens.")
            merge_pdfs(pdf_batch, output_path)

            report["merged_files"].append({
                "output_file": output_filename,
                "source_pdfs": [os.path.basename(p) for p in pdf_batch],
                "total_tokens": current_batch_tokens
            })

            pdf_batch = []
            current_batch_tokens = 0
            merged_file_count += 1

        pdf_batch.append(file_path)
        current_batch_tokens += token_count

    if pdf_batch:
        output_filename = f"merged_output_{merged_file_count}.pdf"
        output_path = os.path.join(cfg.output_directory, output_filename)

        logging.info(
            f"Merging final batch {merged_file_count} with {len(pdf_batch)} PDFs and {current_batch_tokens} tokens.")
        merge_pdfs(pdf_batch, output_path)

        report["merged_files"].append({
            "output_file": output_filename,
            "source_pdfs": [os.path.basename(p) for p in pdf_batch],
            "total_tokens": current_batch_tokens
        })

    with open(cfg.report_path, 'w') as f:
        json.dump(report, f, indent=4)

    logging.info(f"Knowledge base preparation complete. Report generated at {cfg.report_path}")


if __name__ == "__main__":
    prepare_knowledge_base()
