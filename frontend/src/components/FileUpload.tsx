import { useState } from 'react';
import './FileUpload.css';

interface FileUploadProps {
  onUploadComplete?: (fileId: string, filename: string) => void;
}

export function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    await uploadFile(file);
  };

  const uploadFile = async (file: File) => {
    setUploading(true);
    setError(null);
    setSuccess(null);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // 根据文件类型选择端点
      const isMedia = file.type.startsWith('audio/') || file.type.startsWith('video/');
      const endpoint = isMedia ? '/api/v1/upload/media' : '/api/v1/upload/document';

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '上传失败');
      }

      const result = await response.json();
      setSuccess(`文件上传成功: ${result.filename}`);
      setProgress(100);

      if (onUploadComplete) {
        onUploadComplete(result.file_id, result.filename);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败');
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();

    const files = event.dataTransfer.files;
    if (files.length > 0) {
      await uploadFile(files[0]);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  };

  return (
    <div className="file-upload-container">
      <div
        className={`file-upload-dropzone ${uploading ? 'uploading' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          type="file"
          id="file-input"
          onChange={handleFileSelect}
          disabled={uploading}
          accept=".pdf,.epub,.txt,.md,.mp3,.wav,.m4a,.mp4,.webm"
          style={{ display: 'none' }}
        />

        <label htmlFor="file-input" className="file-upload-label">
          {uploading ? (
            <>
              <div className="upload-spinner"></div>
              <p>上传中... {progress}%</p>
            </>
          ) : (
            <>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <p>点击选择文件或拖拽到此处</p>
              <p className="file-upload-hint">
                支持: PDF, EPUB, 音频, 视频
              </p>
            </>
          )}
        </label>
      </div>

      {error && (
        <div className="upload-message upload-error">
          ❌ {error}
        </div>
      )}

      {success && (
        <div className="upload-message upload-success">
          ✅ {success}
        </div>
      )}
    </div>
  );
}
