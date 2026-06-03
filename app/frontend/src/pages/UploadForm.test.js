import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import UploadForm from './UploadForm';

// ── Mocks ──────────────────────────────────────────────────────────────

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const mockGet = jest.fn();
const mockPost = jest.fn();
jest.mock('../services/api', () => ({
  api: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
}));

jest.mock('../utils/AuthContext', () => ({
  useAuth: () => ({ isLoggedIn: true, authLoading: false }),
}));

const mockAddToast = jest.fn();
jest.mock('../utils/ToastContext', () => ({
  useToast: () => ({ addToast: (...args) => mockAddToast(...args) }),
}));

jest.mock('./UploadForm.css', () => ({}));

global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();

beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();

  mockGet.mockImplementation((url) => {
    if (url === '/ai/geocode') {
      return Promise.resolve({ data: { lat: 31.5, lon: 34.47, city: 'Gaza', country: 'Palestine' } });
    }
    // /health and anything else
    return Promise.resolve({ data: {} });
  });
  mockPost.mockResolvedValue({ data: {} });
});

// ── Render Tests ────────────────────────────────────────────────────────

describe('UploadForm', () => {
  it('renders the report form with its sections', async () => {
    await act(async () => { render(<UploadForm />); });

    expect(screen.getByText(/Submit a report/i)).toBeInTheDocument();
    expect(screen.getByText(/General Information/i)).toBeInTheDocument();
    expect(screen.getByText(/Location Information/i)).toBeInTheDocument();
    expect(screen.getByText(/Severity/i)).toBeInTheDocument();
    expect(screen.getByText(/Source & Witness/i)).toBeInTheDocument();
    // Media is optional now — framed as such, no required picker.
    expect(screen.getByText(/Add photo, video or audio \(optional\)/i)).toBeInTheDocument();
  });

  it('does NOT fetch file types (the picker is gone)', async () => {
    await act(async () => { render(<UploadForm />); });
    const fileTypeCalls = mockGet.mock.calls.filter((c) => String(c[0]).startsWith('/file-types'));
    expect(fileTypeCalls.length).toBe(0);
  });

  it('has a Submit report button', async () => {
    await act(async () => { render(<UploadForm />); });
    expect(screen.getByRole('button', { name: /Submit report/i })).toBeInTheDocument();
  });

  it('defaults severity to LOW and lets the reporter raise it', async () => {
    await act(async () => { render(<UploadForm />); });

    const low = screen.getByRole('button', { name: /LOW/i });
    const high = screen.getByRole('button', { name: /HIGH/i });
    expect(low).toHaveAttribute('aria-pressed', 'true');
    expect(high).toHaveAttribute('aria-pressed', 'false');

    await act(async () => { fireEvent.click(high); });
    expect(high).toHaveAttribute('aria-pressed', 'true');
    expect(low).toHaveAttribute('aria-pressed', 'false');
  });
});

// ── File Selection Tests ────────────────────────────────────────────────

describe('UploadForm - File Selection', () => {
  it('shows error for file exceeding 60MB', async () => {
    await act(async () => { render(<UploadForm />); });

    const fileInput = document.getElementById('fileInput');
    const bigFile = new File(['x'.repeat(100)], 'huge.mp4', { type: 'video/mp4' });
    Object.defineProperty(bigFile, 'size', { value: 70 * 1024 * 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [bigFile] } });
    });

    expect(screen.getByText(/too large/i)).toBeInTheDocument();
  });

  it('shows error for unsupported file type', async () => {
    await act(async () => { render(<UploadForm />); });

    const fileInput = document.getElementById('fileInput');
    const badFile = new File(['data'], 'script.exe', { type: 'application/x-msdownload' });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [badFile] } });
    });

    expect(screen.getByText(/isn’t supported|isn't supported/i)).toBeInTheDocument();
  });

  it('attaches a valid image and shows its name', async () => {
    await act(async () => { render(<UploadForm />); });

    const fileInput = document.getElementById('fileInput');
    const imgFile = new File(['fake-image-data'], 'photo.jpg', { type: 'image/jpeg' });
    Object.defineProperty(imgFile, 'size', { value: 2 * 1024 * 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [imgFile] } });
    });

    expect(screen.getAllByText(/photo.jpg/).length).toBeGreaterThanOrEqual(1);
  });
});

// ── No AI auto-authoring ──────────────────────────────────────────────────

describe('UploadForm - reporter authors the claim', () => {
  it('does NOT auto-fill title/subject from the photo (AI cannot author the report)', async () => {
    mockPost.mockImplementation((url) => {
      if (url === '/ai/analyze') {
        return Promise.resolve({
          data: {
            title: 'Airstrike aftermath in Gaza',
            subject: 'Damaged buildings',
            tags: 'airstrike',
            city: 'Gaza',
            country: 'Palestine',
            exif: { has_gps: false },
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => { render(<UploadForm />); });

    const fileInput = document.getElementById('fileInput');
    const imgFile = new File(['data'], 'gaza.jpg', { type: 'image/jpeg' });
    Object.defineProperty(imgFile, 'size', { value: 1024 * 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [imgFile] } });
    });

    // The photo IS checked (for embedded GPS)…
    await waitFor(() => {
      expect(mockPost.mock.calls.some((c) => c[0] === '/ai/analyze')).toBe(true);
    });

    // …but the reporter's fields stay empty — the model never authors them.
    const titleInput = screen.getByPlaceholderText(/compelling headline/i);
    expect(titleInput.value).toBe('');
    expect(screen.queryByDisplayValue('Airstrike aftermath in Gaza')).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue('Damaged buildings')).not.toBeInTheDocument();
  });
});

// ── Required contract + honest pending redirect ───────────────────────────

describe('UploadForm - submission', () => {
  it('requires a title', async () => {
    await act(async () => { render(<UploadForm />); });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Submit report/i }));
    });

    expect(screen.getByText(/describe what happened in the title/i)).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('requires city and country', async () => {
    await act(async () => { render(<UploadForm />); });

    fireEvent.change(screen.getByPlaceholderText(/compelling headline/i), { target: { value: 'Something happened' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Submit report/i }));
    });

    expect(screen.getByText(/at least a city and country/i)).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('submits a text-only report and redirects to Your reports with an honest pending toast', async () => {
    mockPost.mockImplementation((url) => {
      if (url === '/file_upload/upload') {
        return Promise.resolve({ data: { file_id: 7, verification_status: 'PENDING' } });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => { render(<UploadForm />); });

    fireEvent.change(screen.getByPlaceholderText(/compelling headline/i), { target: { value: 'Shelling near the market' } });
    fireEvent.change(screen.getByPlaceholderText(/city where the news/i), { target: { value: 'Gaza' } });
    fireEvent.change(screen.getByPlaceholderText(/Enter the country/i), { target: { value: 'Palestine' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Submit report/i }));
    });

    await waitFor(() => {
      expect(mockPost.mock.calls.some((c) => c[0] === '/file_upload/upload')).toBe(true);
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/my-uploads');
    });

    // Honest copy: pending, not "live on the map".
    const [, toastMsg] = mockAddToast.mock.calls.find(() => true) || [];
    expect(mockAddToast).toHaveBeenCalled();
    expect(String(mockAddToast.mock.calls[0][0])).toMatch(/pending review/i);
  });
});

// ── Geocoding Proxy Tests ───────────────────────────────────────────────

describe('UploadForm - Geocoding', () => {
  it('uses the backend proxy for geocoding', async () => {
    await act(async () => { render(<UploadForm />); });

    fireEvent.change(screen.getByPlaceholderText(/city where the news/i), { target: { value: 'Gaza' } });
    fireEvent.change(screen.getByPlaceholderText(/Enter the country/i), { target: { value: 'Palestine' } });

    await waitFor(() => {
      const geocodeCalls = mockGet.mock.calls.filter((call) => call[0] === '/ai/geocode');
      expect(geocodeCalls.length).toBeGreaterThan(0);
    }, { timeout: 2000 });
  });
});
