# Custom GPT Knowledge Base Preparation Tool

This project provides a flexible Python script for processing various document types (`.pdf`, `.epub`, `.docx`, `.txt`) and consolidating them into a structured knowledge base suitable for training custom GPT models.

The script intelligently handles large files, performs OCR on scanned documents, and uses a streaming and batching algorithm to pack the final output PDFs efficiently—respecting configurable token and file size limits.

---

## ✨ Key Features

- **Multi‑Format Support:** Handles PDFs, EPUBs, DOCX, and TXT files.  
- **Intelligent PDF Handling:** Automatically distinguishes between text‑based and scanned (image‑based) PDFs.  
- **OCR for Scanned Documents:** Integrates Tesseract‑OCR to extract text from scanned PDFs, making them searchable.  
- **Advanced Streaming & Batching:** Streams pages continuously and splits outputs right at the token limit. A single source file can be split across multiple output batches.  
- **Dynamic File Splitting:**
  - **Native PDFs:** Split by page while preserving layout.
  - **Other Formats:** Split by token count.  
- **Configurable Limits:** Control max token counts and file sizes via YAML config.  
- **Detailed Reporting:** Generates `report.json` summarizing processed files, token counts, and file sizes.  
- **Configuration‑Driven:** Uses Hydra for easy overrides through `config.yaml` or the command line.

---

## ⚙️ Prerequisites

Install these before running:

1. **Python 3.8+**
2. **Tesseract‑OCR** (for OCR):
   - [Installation guide](https://github.com/tesseract-ocr/tesseract)
   - Ensure `tesseract` is in your PATH.
3. **Poppler** (required by `pdf2image`):
   - **macOS (Homebrew):**
     ```bash
     brew install poppler
     ```
   - **Linux (Debian/Ubuntu):**
     ```bash
     sudo apt-get install poppler-utils
     ```
   - **Windows:** [Download Poppler](https://github.com/oschwartz10612/poppler-windows/releases/) and add its `bin/` folder to PATH.

---

## 🚀 Setup

Clone the repository and install dependencies:

```bash
git clone <your-repository-url>
cd pdf-knowledge-base

python3 -m venv venv
source venv/bin/activate     # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

**`requirements.txt` contents:**
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

## 📄 Configuration

Edit `configs/config.yaml` to suit your needs:

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

# External Tool Paths (optional)
poppler_path: null
tesseract_cmd: null
```

**Key fields:**

| Field | Purpose |
|-------|---------|
| `source_directory` | Input folder containing your documents |
| `output_directory` | Where final PDFs are saved |
| `report_path` | Path to the JSON report |
| `max_tokens_per_file` | Max tokens per output PDF |
| `max_file_size_mb` | Max size per source file |
| `use_ocr` | Enable or disable OCR |
| `poppler_path` | Absolute path if Poppler isn’t in PATH |
| `tesseract_cmd` | Absolute path if Tesseract isn’t in PATH |

---

## ▶️ Usage

1. Place your documents in `source_directory` (e.g., `source_pdfs/`).
2. Run the script:
   ```bash
   python prepare_kb.py
   ```

**Override settings on the fly:**
```bash
# Change token limit and disable OCR
python prepare_kb.py max_tokens_per_file=1500000 use_ocr=false

# Set Poppler and Tesseract paths
python prepare_kb.py poppler_path=/opt/homebrew/bin tesseract_cmd=/opt/homebrew/bin/tesseract
```

---

## 🔧 How It Works

1. **Scan & Identify:** Finds files matching extensions in `file_types`.
2. **Process & Convert:**  
   - PDFs are read page by page.  
   - EPUB/DOCX/TXT or scanned PDFs are converted to searchable PDFs (via OCR if needed).  
3. **Batching:** Adds pages one by one to output until hitting token limit.  
4. **Split & Save:** Finalizes each batch before starting the next.  
5. **Clean Up:** Temporary converted PDFs are removed.  
6. **Report:** Generates a `report.json` with details of all processed files.

---

## 📂 Project Structure

```
pdf-knowledge-base/
├── configs/
│   └── config.yaml
├── source_pdfs/
│   ├── document_a.pdf
│   └── ...
├── prepare_kb.py
├── requirements.txt
└── README.md
```

Outputs will be created under `outputs/`, including your merged PDFs and `report.json`.
