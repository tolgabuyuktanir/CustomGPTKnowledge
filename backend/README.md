# Custom Knowledge Base Preparation Tool

This project provides a flexible and powerful Python script for processing various document types (`.pdf`, `.epub`, `.docx`, `.txt`) and consolidating them into a structured knowledge base. The output is suitable for training custom GPT models or for use with Retrieval-Augmented Generation (RAG) systems.

The script is designed to be run from the command line and uses **Hydra** for advanced configuration management. This allows you to easily override any setting directly from the terminal without modifying configuration files. It intelligently handles large files, performs Optical Character Recognition (OCR) on scanned documents, and uses an efficient streaming and batching algorithm to pack the final output PDFs while respecting token and file size limits.

---

## ✨ Key Features

-   **Multi-Format Support:** Handles PDFs, EPUBs, DOCX, and TXT files seamlessly.
-   **Intelligent PDF Handling:** Automatically distinguishes between text-based and scanned (image-based) PDFs.
-   **OCR for Scanned Documents:** Integrates Tesseract-OCR to extract text from scanned PDFs, making non-searchable documents accessible.
-   **Memory-Efficient Streaming:** Processes large files page-by-page to minimize memory usage, preventing crashes with large documents.
-   **Configuration-Driven with Hydra:** All settings are managed through a clean `config.yaml` file. Every parameter can be easily overridden directly from the command line for maximum flexibility.
-   **Detailed JSON Reporting:** Generates a `report.json` file summarizing processed files, skipped files, token counts, and final output sizes.

---

## ⚙️ Prerequisites

Before running the script, you need to install the following dependencies:

1.  **Python 3.8+**
2.  **Tesseract-OCR** (Required for the OCR feature):
    * [Official Installation Guide](https://github.com/tesseract-ocr/tesseract)
    * Ensure the `tesseract` command is available in your system's PATH.
3.  **Poppler** (A PDF rendering library required by the script):
    * **macOS (Homebrew):**
        ```bash
        brew install poppler
        ```
    * **Linux (Debian/Ubuntu):**
        ```bash
        sudo apt-get install poppler-utils
        ```
    * **Windows:** Download the [latest release](https://github.com/oschwartz10612/poppler-windows/releases/) and add its `bin/` folder to your system's PATH.

---

## 🚀 Setup

1.  **Clone the repository and navigate into the project directory.**
2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use: venv\Scripts\activate
    ```
3.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 📄 Configuration

All settings are controlled via the `configs/config.yaml` file. You can edit this file directly or, more powerfully, override its values from the command line.

**`configs/config.yaml`:**
```yaml
# Directory Settings
source_directory: "source_pdfs"
output_directory: "outputs/knowledge_base"
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
tiktoken_model: "gpt-4o"
use_ocr: true

# Optional: Provide absolute paths if tools are not in your system's PATH
poppler_path: null
tesseract_cmd: null
````

| Field                 | Description                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| `source_directory`    | The input folder where your source documents are located.                                               |
| `output_directory`    | The directory where the final, merged PDF files will be saved.                                          |
| `report_path`         | The path where the final JSON report will be saved.                                                     |
| `max_tokens_per_file` | The maximum number of tokens allowed per output PDF file.                                               |
| `max_file_size_mb`    | The maximum file size (in MB) for any single source file. Files larger than this will be skipped.         |
| `tiktoken_model`      | The model to use for token counting (e.g., `gpt-4o`, `gpt-4`).                                            |
| `use_ocr`             | A boolean (`true` or `false`) to enable or disable the OCR feature for scanned PDFs.                      |
| `poppler_path`        | Optional: The absolute path to your Poppler `bin` directory if it's not in your system's PATH.            |
| `tesseract_cmd`       | Optional: The absolute path to the Tesseract executable if it's not in your system's PATH.                |

-----

## ▶️ Usage

The script is designed to be run from the terminal.

1.  **Place your documents** in the folder specified by `source_directory` (e.g., `source_pdfs/`).
2.  **Run the script** with the default configuration:
    ```bash
    python prepare_kb.py
    ```
    The script will display its progress in the terminal, including the current file being processed.

### Overriding Configuration with Hydra

You can easily change any setting from the command line without editing the `config.yaml` file.

**Examples:**

  - **Change the token limit and disable OCR:**

    ```bash
    python prepare_kb.py max_tokens_per_file=1500000 use_ocr=false
    ```

  - **Process only `.docx` and `.txt` files and save to a different output directory:**

    ```bash
    python prepare_kb.py file_types="[.docx,.txt]" output_directory=outputs/text_only
    ```

  - **Specify paths for Poppler and Tesseract on macOS (if not in PATH):**

    ```bash
    python prepare_kb.py poppler_path=/opt/homebrew/bin tesseract_cmd=/opt/homebrew/bin/tesseract
    ```

-----

## 🔧 How It Works

1.  **Configuration Loading:** Hydra loads the base configuration from `config.yaml` and merges it with any command-line overrides.
2.  **File Discovery:** The script scans the `source_directory` for files that match the extensions listed in `file_types`.
3.  **Content Extraction:** It processes each file one by one:
      * **Native PDFs:** Text is extracted directly, page by page.
      * **Other Formats & Scanned PDFs:** Text is extracted (using OCR if necessary) and converted into a temporary, searchable PDF. This unifies the processing pipeline.
4.  **Streaming & Batching:** Pages are added to an output file one at a time. If adding a page would exceed `max_tokens_per_file`, the current output file is saved, and a new one is started.
5.  **Cleanup & Reporting:** All temporary files are deleted, and a final `report.json` is generated with detailed statistics about the completed job.

<!-- end list -->