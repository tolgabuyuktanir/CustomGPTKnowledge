# Custom GPT Knowledge Base Preparation Tool

This project provides a powerful and flexible Python script for processing various document types (`.pdf`, `.epub`, `.docx`, `.txt`) and consolidating them into a structured knowledge base suitable for training custom GPT models.

The script intelligently handles large files, performs OCR on scanned documents, and uses a sophisticated streaming and batching algorithm to pack the final output PDFs as efficiently as possible, respecting configurable token and file size limits.

## Key Features

- **Multi-Format Support**: Processes PDFs, EPUBs, DOCX, and TXT files.
- **Intelligent PDF Handling**: Automatically distinguishes between text-based and scanned (image-based) PDFs.
- **OCR for Scanned Documents**: Integrates Tesseract-OCR to extract text from scanned PDFs, making them searchable.
- **Advanced Streaming & Batching**: Processes all documents as a continuous stream of pages to efficiently pack output files right up to the specified token limit. A single source file can be split across multiple output batches to maximize space.
- **Dynamic File Splitting**:
    - **Native PDFs**: Large text-based PDFs are split by page to preserve their original layout.
    - **Other Formats**: Large EPUBs, DOCX files, or text from scanned PDFs are split by token count.
- **Configurable Limits**: Set maximum token counts and file sizes for each output file via a simple YAML configuration.
- **Detailed Reporting**: Generates a `report.json` file summarizing which files were processed, merged, or skipped, along with token counts and file sizes.
- **Configuration-Driven**: Managed by Hydra, allowing for easy changes through a `config.yaml` file or command-line overrides.

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Python 3.8+**
2.  **Tesseract-OCR Engine**: This is required for the OCR functionality.
    -   Installation instructions can be found on the [official Tesseract GitHub page](https://github.com/tesseract-ocr/tesseract). Make sure the `tesseract` command is available in your system's PATH.
3.  **Poppler** (for `pdf2image` on Windows/Linux):
    -   **Windows**: Download the latest release from [this page](https://github.com/oschwartz10612/poppler-windows/releases/) and add the `bin/` directory to your system's PATH.
    -   **Linux (Ubuntu/Debian)**: `sudo apt-get install poppler-utils`
    -   **macOS (via Homebrew)**: `brew install poppler`

---

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd pdf-knowledge-base
    ```

2.  **Create a Virtual Environment** (Recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    The project's dependencies are listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```
    The `requirements.txt` file should contain:
    ```
    hydra-core
    pypdf
    tiktoken
    pytesseract
    pdf2image
    Pillow
    python-docx
    EbookLib
    beautifulsoup4
    reportlab
    ```

---

## Configuration

All script settings are managed in the `configs/config.yaml` file.

```yaml
# Directory Settings
source_directory: "source_pdfs"
output_directory: "outputs/knowledge_base_pdf"
report_path: "outputs/report.json"

# File Types to Process
file_types:
  - ".pdf"
  - ".epub"
  - ".docx"
  - ".txt"

# Processing Limits
max_tokens_per_file: 2000000
max_file_size_mb: 512

# Model and Feature Toggles
tiktoken_model: "gpt-4"
use_ocr: true

# --- Optional External Tool Paths ---
# Provide the absolute path to your Poppler 'bin' directory if it's not in your system's PATH.
# Set to null or remove the line if Poppler is in your PATH.
# Example for macOS Homebrew: "/opt/homebrew/bin"
# Example for Windows: "C:/path/to/poppler-22.04.0/Library/bin"
poppler_path: null

# Provide the absolute path to your Tesseract executable if it's not in your system's PATH.
# Example for macOS Homebrew: "/opt/homebrew/bin/tesseract"
# Example for Windows: "C:/Program Files/Tesseract-OCR/tesseract.exe"
tesseract_cmd: null
```
source_directory: The folder containing your input documents.output_directory: Where the final, merged PDFs will be saved.report_path: The location for the final JSON summary report.file_types: A list of file extensions to look for in the source directory.max_tokens_per_file: The maximum number of tokens allowed in a single output PDF.max_file_size_mb: The maximum size in megabytes for any source file.tiktoken_model: The model to use for tokenization (e.g., gpt-4, gpt-3.5-turbo).use_ocr: Set to true to enable OCR for scanned PDFs.poppler_path: (Optional) The absolute path to your Poppler bin directory. Only needed if Poppler is not in your system's PATH.tesseract_cmd: (Optional) The absolute path to your Tesseract executable. Only needed if Tesseract is not in your system's PATH.UsagePlace all your source documents into the directory specified by source_directory in your config file (e.g., source_pdfs/).Run the script from the project's root directory:python prepare_kb.py
Overriding Configuration via Command Line:You can easily override any setting from the command line using Hydra's syntax.# Run with a different token limit and disable OCR
python prepare_kb.py max_tokens_per_file=1500000 use_ocr=false

# Specify the poppler and tesseract paths directly
python prepare_kb.py poppler_path=/opt/homebrew/bin tesseract_cmd=/opt/homebrew/bin/tesseract
How It WorksThe script operates using a sophisticated streaming pipeline to ensure maximum efficiency:File Identification: It first scans the source_directory for all files matching the specified file_types.Streaming Processing: It processes one file at a time.Content Conversion:Native PDFs: The script reads the PDF page by page directly.Other Formats (EPUB, DOCX, TXT, Scanned PDFs): The file is fully converted into text. This text is then used to generate a new, temporary, multi-page searchable PDF.Page-by-Page Batching: The script adds pages one by one from the source (either the original PDF or the temporary one) to the current output batch (e.g., knowledge_base_1.pdf).Dynamic Batch Finalization: If adding the next page would exceed the max_tokens_per_file limit, the current batch is finalized and saved. A new batch is then started with that page.Cleanup: Once all files are processed, the temporary directory containing converted PDFs is deleted.Reporting: A final report.json is generated with detailed statistics of the entire operation.This streaming approach allows the script to split a single large document across multiple final output files, ensuring each output file is packed as close to the token limit as possible.Project Structurepdf-knowledge-base/
├── configs/
│   └── config.yaml
├── source_pdfs/
│   ├── document_a.pdf
│   └── ...
├── prepare_kb.py
├── requirements.txt
└── README.md
configs/: Contains the main configuration file.source_pdfs/: Your input directory for all source documents.prepare_kb.py: The main executable Python script.outputs/ (Generated): This directory is created automatically to store the results, including the final merged PDFs and the JSON report.
