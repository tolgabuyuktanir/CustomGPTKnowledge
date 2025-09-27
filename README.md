# Knowledge Base Builder Web App

This project provides a full-stack web application for processing documents and creating a structured knowledge base suitable for custom GPTs and RAG systems. It features a user-friendly **React frontend** and a powerful **Python Flask backend** that handles file processing, OCR, and real-time progress updates.

The application allows users to upload multiple documents (`.pdf`, `.epub`, `.docx`, `.txt`), configure processing parameters such as token limits, and receive live feedback as their files are processed.

---

## ✨ Features

- **Interactive Web Interface:** A clean, modern UI built with React for easy configuration and file management.  
- **Drag-and-Drop File Uploads:** A simple and intuitive way to add multiple documents for processing.  
- **Real-Time Progress Tracking:** The frontend receives live updates from the server, showing which file is being processed and the current task (e.g., “Performing OCR…”).  
- **Full Backend Power:** Utilizes the robust Python script for multi-format support, intelligent PDF handling, OCR, and memory-efficient streaming.  
- **Concurrent Request Handling:** The backend creates unique sessions for each request, ensuring that multiple users can use the application simultaneously without conflicts.

---

## ⚙️ System Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Node.js and npm** — v16 or higher recommended (for the React frontend)  
2. **Python 3.8+** — for the Flask backend  
3. **Tesseract-OCR** — required for the OCR feature  
   - [Official Installation Guide](https://github.com/tesseract-ocr/tesseract)  
   - Ensure the `tesseract` command is available in your system's PATH.  
4. **Poppler** — a PDF rendering library required for PDF processing  
   - **macOS (Homebrew):**
     ```bash
     brew install poppler
     ```
   - **Linux (Debian/Ubuntu):**
     ```bash
     sudo apt-get install poppler-utils
     ```
   - **Windows:**  
     Download the [latest release](https://github.com/oschwartz10612/poppler-windows/releases/)  
     and add its `bin/` folder to your system's PATH.

---

## 🚀 Setup Instructions

The setup process is divided into two parts: **Backend** and **Frontend**.

### 1. Backend Setup (Python)

Set up the Python environment and install the required dependencies.

```bash
# Navigate to the backend directory
cd backend

# Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

### 2. Frontend Setup (React)

Next, set up the React application.

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install
```

---

## ▶️ How to Run the Application

You’ll need to start both the **backend** and **frontend** in separate terminals.

### 🖥️ Terminal 1: Start the Backend Server

```bash
cd backend
source venv/bin/activate  # (Activate environment if not already)
python server.py
```

The backend server will start and listen on [http://127.0.0.1:5001](http://127.0.0.1:5001).

---

### 🌐 Terminal 2: Start the Frontend App

```bash
cd frontend
npm start
```

The React app will automatically open in your browser at [http://localhost:3000](http://localhost:3000).

---

## 📖 How to Use the Web App

1. **Open the Web Page:** Go to [http://localhost:3000](http://localhost:3000) in your browser.  
2. **Configure Settings:** Adjust parameters such as token limits and OCR options in the “Configuration” section.  
3. **Upload Files:** Drag and drop your documents, or click to select them manually.  
4. **Start Processing:** Click **Build Knowledge Base** to begin.  
5. **Monitor Progress:** Watch live updates showing the current file, step, and OCR activity.  
6. **Download Results:** Once completed, use **Download All** or individual links to retrieve processed PDFs.  
   The final **JSON report** will also be displayed.

---

## 🔧 How It Works

1. The **React frontend** provides the interface for configuration, file uploads, and progress visualization.  
2. When you start processing, the frontend sends files and settings to the **Flask backend**.  
3. The backend creates a **unique session** for each user and launches the core processing script.  
4. A **Server-Sent Events (SSE)** connection streams real-time progress logs from the backend to the UI.  
5. After processing, the backend sends the final **download links** and a **JSON summary report** to the frontend.

---
