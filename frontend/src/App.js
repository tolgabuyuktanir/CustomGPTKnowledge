import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = "http://127.0.0.1:5001";

// --- SVG Icons ---
const UploadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);
const FileIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" /><polyline points="13 2 13 9 20 9" />
  </svg>
);
const CheckIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
    </svg>
);
const XCircleIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>
    </svg>
);

const ProgressTracker = ({ currentStep }) => {
    const steps = ['Upload', 'Process', 'Complete'];
    const progressFillWidth = currentStep > 1 ? ((currentStep - 1) / (steps.length - 1)) * 100 : 0;

    return (
        <div className="progress-tracker">
            <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${progressFillWidth}%` }}></div>
            </div>
            {steps.map((step, index) => {
                const isCompleted = index + 1 < currentStep;
                const isActive = index + 1 === currentStep;
                const isFinalStepCompleted = isActive && currentStep === steps.length;

                return (
                    <div key={step} className={`progress-step ${isCompleted || isFinalStepCompleted ? 'completed' : ''} ${isActive && !isFinalStepCompleted ? 'active' : ''}`}>
                        <div className="step-icon">{isCompleted || isFinalStepCompleted ? <CheckIcon/> : index + 1}</div>
                        <div className="step-label">{step}</div>
                    </div>
                );
            })}
        </div>
    );
};


function App() {
  const [files, setFiles] = useState([]);
  const [config, setConfig] = useState({
    max_tokens_per_file: 2000000, max_file_size_mb: 512,
    tiktoken_model: 'gpt-4o', use_ocr: true,
    file_types: ['.pdf', '.docx', '.txt', '.epub'],
  });
  const [availableModels, setAvailableModels] = useState([]);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const [progressStep, setProgressStep] = useState(1);
  const [uploadProgress, setUploadProgress] = useState(0);

  const [progressData, setProgressData] = useState({
      file_index: 0, total_files: 0, filename: '', message: ''
  });

  const [isDragging, setIsDragging] = useState(false);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/models`);
        const models = response.data;
        setAvailableModels(models);
        if (models.length > 0 && !models.includes(config.tiktoken_model)) {
          setConfig(prev => ({ ...prev, tiktoken_model: models[0] }));
        }
      } catch (err) {
        setAvailableModels(['gpt-4o', 'gpt-4', 'gpt-3.5-turbo']);
      }
    };
    fetchModels();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [config.tiktoken_model]);

  const handleFileChange = (e) => setFiles([...e.target.files]);
  const handleConfigChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (type === 'checkbox') setConfig(p => ({ ...p, [name]: checked }));
    else if (name === 'file_types') setConfig(p => ({ ...p, [name]: value.split(',').map(ext => ext.trim()) }));
    else setConfig(p => ({ ...p, [name]: value }));
  };

  const handleDownloadAll = () => {
    if (result && result.download_links) {
        result.download_links.forEach((link, index) => {
            setTimeout(() => {
                const a = document.createElement('a');
                a.href = `${API_BASE_URL}${link}`;
                a.download = link.split('/').pop();
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }, index * 300);
        });
    }
  };

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e) => {
      e.preventDefault();
      setIsDragging(false);
      setFiles([...e.dataTransfer.files]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) {
      setError('Please select at least one file.');
      return;
    }
    setIsLoading(true);
    setError('');
    setResult(null);
    setProgressStep(1);
    setUploadProgress(0);
    setProgressData({ file_index: 0, total_files: files.length, filename: '', message: ''});


    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('config', JSON.stringify({
      ...config,
      max_tokens_per_file: parseInt(config.max_tokens_per_file),
      max_file_size_mb: parseInt(config.max_file_size_mb),
    }));

    try {
      const setupResponse = await axios.post(`${API_BASE_URL}/api/process`, formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        },
      });

      const { session_id } = setupResponse.data;
      if (!session_id) throw new Error("Failed to get session ID.");

      setProgressStep(2);

      const eventSource = new EventSource(`${API_BASE_URL}/api/stream/${session_id}`);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'progress') {
            setProgressData(prev => ({...prev, ...data})); // Merge new progress data
        } else if (data.type === 'complete') {
            setResult(data);
            setProgressStep(3);
            setIsLoading(false);
            eventSource.close();
        } else if (data.type === 'error') {
            setError(data.message);
            setProgressStep(1);
            setIsLoading(false);
            eventSource.close();
        }
      };

      eventSource.onerror = () => {
        setError('Connection to server lost.');
        setProgressStep(1);
        setIsLoading(false);
        eventSource.close();
      };

    } catch (err) {
      setError(err.response?.data?.details || err.response?.data?.error || 'An unexpected error during setup.');
      setProgressStep(1);
      setIsLoading(false);
    }
  };

  const processingProgress = progressData.total_files > 0
    ? (((progressData.file_index || 0) + 1) / progressData.total_files) * 100
    : 0;

  const ProgressMessage = () => {
    if (progressStep === 1) return `Uploading files... ${uploadProgress}%`;
    if (progressStep === 2) {
      const fileIndex = (progressData.file_index || 0) + 1;
      const totalFiles = progressData.total_files || files.length;
      return (
        <>
          ({fileIndex}/{totalFiles}) {progressData.filename}: <span>{progressData.message}</span>
        </>
      );
    }
    if (progressStep === 3) return 'Processing complete!';
    return '';
  };


  return (
    <div className="App">
      <header className="App-header">
        <h1>Knowledge Base Builder</h1>
        <p>Turn your documents into a structured knowledge base for Custom GPTs.</p>
      </header>

      <main>
        {!isLoading && !result && (
          <form onSubmit={handleSubmit}>
            <div className="card">
                <div className="form-grid">
                    <div className="form-group"><label>Max Tokens per File</label><input type="number" name="max_tokens_per_file" value={config.max_tokens_per_file} onChange={handleConfigChange} /></div>
                    <div className="form-group"><label>Max Source File Size (MB)</label><input type="number" name="max_file_size_mb" value={config.max_file_size_mb} onChange={handleConfigChange} /></div>
                    <div className="form-group"><label>Tokenization Model</label><select name="tiktoken_model" value={config.tiktoken_model} onChange={handleConfigChange}>{availableModels.map(m => <option key={m} value={m}>{m}</option>)}</select></div>
                    <div className="form-group"><label>File Types (comma-separated)</label><input type="text" name="file_types" value={config.file_types.join(', ')} onChange={handleConfigChange} /></div>
                    <div className="checkbox-container"><input id="use_ocr" type="checkbox" name="use_ocr" checked={config.use_ocr} onChange={handleConfigChange} /><label htmlFor="use_ocr">Use OCR for Scanned PDFs</label></div>
                </div>
            </div>
            <div className="card">
                <label
                    htmlFor="file-input"
                    className={`file-upload-area ${isDragging ? 'dragging' : ''}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                >
                    <UploadIcon />
                    <p><span>Click to upload</span> or drag and drop</p>
                    <p style={{fontSize: '0.8rem'}}>Supported: .pdf, .docx, .txt, .epub</p>
                </label>
                <input id="file-input" type="file" multiple onChange={handleFileChange} />
                {files.length > 0 && (
                    <>
                        <div className="file-list-header">
                            <h4>Selected files:</h4>
                            <button type="button" onClick={() => setFiles([])} className="clear-button"><XCircleIcon/> Clear</button>
                        </div>
                        <div className="file-list">
                            {Array.from(files).map((f, i) => <div key={i} className="file-item"><FileIcon />{f.name}</div>)}
                        </div>
                    </>
                )}
            </div>
            <button type="submit" disabled={isLoading || files.length === 0}>Build Knowledge Base</button>
          </form>
        )}

        {(isLoading || result) && (
            <div className="card">
                <ProgressTracker currentStep={progressStep} />
                <div className="progress-message-text">
                  <ProgressMessage/>
                </div>
                {progressStep === 1 &&
                    <div className="progress-container">
                        <div className="progress-bar"><div className="progress-fill" style={{width: `${uploadProgress}%`}}></div></div>
                    </div>
                }
                {progressStep === 2 &&
                    <div className="progress-container">
                        <div className="progress-bar"><div className="progress-fill" style={{width: `${processingProgress}%`}}></div></div>
                    </div>
                }
            </div>
        )}

        {error && <div className="message error-message">{error}</div>}

        {result && (
          <div className="card results-section">
            <h2>Processing Complete</h2>
            <h3>Download Files</h3>
            {result.download_links.length > 0 ? (
              <>
                <button onClick={handleDownloadAll} className="download-all-button">Download All ({result.download_links.length} files)</button>
                <p style={{textAlign: 'center', marginTop: '15px', color: 'var(--subtle-text)'}}>Or download individual files:</p>
                <ul className="download-list">
                    {result.download_links.map((link, i) => <li key={i}><a href={`${API_BASE_URL}${link}`} target="_blank" rel="noopener noreferrer">{link.split('/').pop()}</a></li>)}
                </ul>
              </>
            ) : <p>No files were generated.</p>}
            <h3>Processing Report</h3>
            <pre>{JSON.stringify(result.report, null, 2)}</pre>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

