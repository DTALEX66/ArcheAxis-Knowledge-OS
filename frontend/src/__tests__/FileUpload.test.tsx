/**
 * Integration test for FileUpload component
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FileUpload } from '../components/FileUpload';
import { describe, it, expect, vi } from 'vitest';

describe('FileUpload', () => {
  it('renders upload dropzone', () => {
    render(<FileUpload />);
    expect(screen.getByText(/点击选择文件或拖拽到此处/i)).toBeInTheDocument();
  });

  it('shows file type hints', () => {
    render(<FileUpload />);
    expect(screen.getByText(/支持: PDF, EPUB, 音频, 视频/i)).toBeInTheDocument();
  });

  it('handles file selection', async () => {
    const mockFetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          file_id: 'test123',
          filename: 'test.pdf'
        })
      })
    );
    global.fetch = mockFetch as any;

    const onComplete = vi.fn();
    render(<FileUpload onUploadComplete={onComplete} />);

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('test123', 'test.pdf');
    });
  });

  it('displays error message on upload failure', async () => {
    const mockFetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({
          detail: '上传失败'
        })
      })
    );
    global.fetch = mockFetch as any;

    render(<FileUpload />);

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/上传失败/i)).toBeInTheDocument();
    });
  });
});
