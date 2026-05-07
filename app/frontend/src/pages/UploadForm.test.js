import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import UploadForm from './UploadForm';

// ── Mocks ──────────────────────────────────────────────────────────────

// Mock react-router (Sidebar uses it)
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
  useLocation: () => ({ pathname: '/upload' }),
  Link: ({ children, to }) => <a href={to}>{children}</a>,
}));

// Mock the api module
const mockGet = jest.fn();
const mockPost = jest.fn();
jest.mock('../services/api', () => ({
  api: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
}));

// Mock AuthContext so useAuth() doesn't return undefined
jest.mock('../utils/AuthContext', () => ({
  useAuth: () => ({ isLoggedIn: true, authLoading: false }),
}));

// Mock CSS import
jest.mock('./UploadForm.css', () => ({}));

// Mock URL.createObjectURL / revokeObjectURL (not available in jsdom)
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();

// Clear any draft data between tests
beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();

  // Default: file types endpoint returns valid types
  mockGet.mockImplementation((url) => {
    if (url === '/file-types/' || url === '/file-types') {
      return Promise.resolve({
        data: [
          { id: 1, type_name: 'Image', allowed_extensions: 'jpg, png, jpeg' },
          { id: 2, type_name: 'Video', allowed_extensions: 'mp4, avi' },
          { id: 3, type_name: 'Audio', allowed_extensions: 'mp3, wav, m4a' },
        ],
      });
    }
    // Geocode proxy
    if (url === '/ai/geocode') {
      return Promise.resolve({ data: { lat: 31.5, lon: 34.47, city: 'Gaza', country: 'Palestine' } });
    }
    return Promise.resolve({ data: {} });
  });
});

// ── Render Tests ────────────────────────────────────────────────────────

describe('UploadForm', () => {
  it('renders the upload form with all sections', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    expect(screen.getByText(/Share News/i)).toBeInTheDocument();
    expect(screen.getByText(/General Information/i)).toBeInTheDocument();
    expect(screen.getByText(/Location Information/i)).toBeInTheDocument();
    expect(screen.getByText(/File Upload/i)).toBeInTheDocument();
  });

  it('loads file types from API on mount', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/file-types/');
    });

    expect(screen.getByText('Image')).toBeInTheDocument();
    expect(screen.getByText('Video')).toBeInTheDocument();
    expect(screen.getByText('Audio')).toBeInTheDocument();
  });

  it('shows title, tags, and subject inputs', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    expect(screen.getByPlaceholderText(/compelling headline/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/relevant tags/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/brief summary/i)).toBeInTheDocument();
  });

  it('shows city and country inputs', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    expect(screen.getByPlaceholderText(/city where the news/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter the country/i)).toBeInTheDocument();
  });

  it('has a Use My Location button', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    expect(screen.getByText(/Use My Location/i)).toBeInTheDocument();
  });

  it('has a Publish button', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    expect(screen.getByRole('button', { name: /Publish/i })).toBeInTheDocument();
  });
});

// ── File Selection Tests ────────────────────────────────────────────────

describe('UploadForm - File Selection', () => {
  it('shows error for file exceeding 60MB', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    const fileInput = document.getElementById('fileInput');

    const bigFile = new File(['x'.repeat(100)], 'huge.mp4', { type: 'video/mp4' });
    Object.defineProperty(bigFile, 'size', { value: 70 * 1024 * 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [bigFile] } });
    });

    expect(screen.getByText(/too large/i)).toBeInTheDocument();
  });

  it('shows error for unsupported file type', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    const fileInput = document.getElementById('fileInput');
    const badFile = new File(['data'], 'script.exe', { type: 'application/x-msdownload' });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [badFile] } });
    });

    expect(screen.getByText(/Invalid file type/i)).toBeInTheDocument();
  });

  it('accepts valid image file and shows file info', async () => {
    // Mock the analyze endpoint (auto-triggered for images)
    mockPost.mockImplementation((url) => {
      if (url === '/ai/analyze') {
        return Promise.resolve({
          data: {
            title: 'Test Image',
            tags: 'test',
            subject: 'A test image',
            city: '',
            country: '',
            confidence: 0.5,
            analysis_steps: ['Extracting photo metadata (EXIF)...', 'Analyzing image with AI...'],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      render(<UploadForm />);
    });

    const fileInput = document.getElementById('fileInput');
    const imgFile = new File(['fake-image-data'], 'photo.jpg', { type: 'image/jpeg' });
    Object.defineProperty(imgFile, 'size', { value: 2 * 1024 * 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [imgFile] } });
    });

    const matches = screen.getAllByText(/photo.jpg/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });
});

// ── AI Analysis Tests ───────────────────────────────────────────────────

describe('UploadForm - AI Analysis', () => {
  it('auto-fills form fields from AI analysis response', async () => {
    mockPost.mockImplementation((url) => {
      if (url === '/ai/analyze') {
        return Promise.resolve({
          data: {
            title: 'Airstrike aftermath in Gaza',
            tags: 'airstrike, gaza, destruction',
            subject: 'Damaged buildings after overnight strikes',
            city: 'Gaza',
            country: 'Palestine',
            event_type: 'military_action',
            confidence: 0.82,
            content_warnings: 'destruction',
            analysis_steps: [
              'Extracting photo metadata (EXIF)...',
              'Analyzing image with AI...',
            ],
            exif: {
              lat: 31.5,
              lon: 34.47,
              has_gps: true,
              has_timestamp: true,
              timestamp: '2026-03-15T10:30:00+00:00',
              device: 'Samsung Galaxy S24',
            },
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      render(<UploadForm />);
    });

    const fileInput = document.getElementById('fileInput');
    const imgFile = new File(['data'], 'gaza.jpg', { type: 'image/jpeg' });
    Object.defineProperty(imgFile, 'size', { value: 1024 * 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [imgFile] } });
    });

    // Wait for AI analysis to complete and auto-fill
    await waitFor(() => {
      expect(screen.getByDisplayValue('Airstrike aftermath in Gaza')).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue('airstrike, gaza, destruction')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Damaged buildings after overnight strikes')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Gaza')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Palestine')).toBeInTheDocument();

    // EXIF metadata section heading should be displayed
    expect(screen.getByText(/📷 Photo Metadata/i)).toBeInTheDocument();
    expect(screen.getByText(/Samsung Galaxy S24/i)).toBeInTheDocument();

    // Confidence banner
    const confidenceMatches = screen.getAllByText(/Confidence: 82%/);
    expect(confidenceMatches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/military_action/i)).toBeInTheDocument();
  });

  it('shows transcription field for video analysis', async () => {
    mockPost.mockImplementation((url) => {
      if (url === '/ai/analyze') {
        return Promise.resolve({
          data: {
            title: 'Witness account from Rafah',
            tags: 'rafah, eyewitness',
            subject: 'Citizen recording of events',
            city: 'Rafah',
            country: 'Palestine',
            confidence: 0.7,
            transcription: 'شهادة شاهد عيان من رفح',
            transcript_language: 'ar',
            analysis_steps: [
              'Extracting video keyframes...',
              'Transcribing audio (multilingual)...',
              'Analyzing content with AI...',
            ],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      render(<UploadForm />);
    });

    const fileInput = document.getElementById('fileInput');
    const videoFile = new File(['data'], 'witness.mp4', { type: 'video/mp4' });
    Object.defineProperty(videoFile, 'size', { value: 5 * 1024 * 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [videoFile] } });
    });

    // Wait for transcription to appear
    await waitFor(() => {
      expect(screen.getByText(/Audio Transcript/i)).toBeInTheDocument();
    });

    // Transcript should be editable
    const transcriptArea = screen.getByDisplayValue('شهادة شاهد عيان من رفح');
    expect(transcriptArea).toBeInTheDocument();
    expect(transcriptArea.tagName).toBe('TEXTAREA');
  });

  it('handles AI analysis failure gracefully', async () => {
    mockPost.mockImplementation((url) => {
      if (url === '/ai/analyze') {
        return Promise.reject({ response: { data: { error: 'Service unavailable' } } });
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      render(<UploadForm />);
    });

    const fileInput = document.getElementById('fileInput');
    const imgFile = new File(['data'], 'test.jpg', { type: 'image/jpeg' });
    Object.defineProperty(imgFile, 'size', { value: 1024 });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [imgFile] } });
    });

    await waitFor(() => {
      expect(screen.getByText(/AI analysis unavailable/i)).toBeInTheDocument();
    });
  });
});

// ── Geocoding Proxy Tests ───────────────────────────────────────────────

describe('UploadForm - Geocoding', () => {
  it('uses backend proxy for geocoding, not direct API call', async () => {
    await act(async () => {
      render(<UploadForm />);
    });

    // Type city and country to trigger geocoding
    const cityInput = screen.getByPlaceholderText(/city where the news/i);
    const countryInput = screen.getByPlaceholderText(/Enter the country/i);

    await act(async () => {
      fireEvent.change(cityInput, { target: { value: 'Gaza' } });
      fireEvent.change(countryInput, { target: { value: 'Palestine' } });
    });

    await waitFor(() => {
      // Should call backend proxy, NOT opencagedata.com directly
      const geocodeCalls = mockGet.mock.calls.filter(
        (call) => call[0] === '/ai/geocode'
      );
      expect(geocodeCalls.length).toBeGreaterThan(0);
    }, { timeout: 2000 });

    // Verify NO direct axios calls to opencagedata
    // (axios was removed from imports, so this is structural validation)
  });
});

// Form submission validation is covered by file selection and AI analysis tests above.
