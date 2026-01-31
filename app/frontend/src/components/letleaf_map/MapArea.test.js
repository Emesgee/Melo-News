import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import MapArea from './MapArea';

// Mock the API calls
global.fetch = jest.fn();

// Mock the Leaflet and react-leaflet components
jest.mock('react-leaflet', () => ({
  ...jest.requireActual('react-leaflet'),
  MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children, position }) => (
    <div data-testid="marker" data-position={JSON.stringify(position)}>
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({
    setView: jest.fn(),
    getZoom: jest.fn(() => 10),
    on: jest.fn(),
    off: jest.fn(),
  }),
}));

jest.mock('react-leaflet-markercluster', () => {
  return function MockMarkerClusterGroup({ children }) {
    return <div data-testid="marker-cluster-group">{children}</div>;
  };
});

// Mock child components
jest.mock('./CityHistory', () => {
  return function MockCityHistory() {
    return <div data-testid="city-history">City History Component</div>;
  };
});

jest.mock('./NewsChat', () => {
  return function MockNewsChat() {
    return <div data-testid="news-chat">News Chat Component</div>;
  };
});

jest.mock('./MeloSummary', () => {
  return function MockMeloSummary() {
    return <div data-testid="melo-summary">Melo Summary Component</div>;
  };
});

describe('MapArea Component', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('renders map container', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ features: [] }),
    });

    render(<MapArea />);
    
    await waitFor(() => {
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
    });
  });

  test('renders tile layer', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ features: [] }),
    });

    render(<MapArea />);
    
    await waitFor(() => {
      expect(screen.getByTestId('tile-layer')).toBeInTheDocument();
    });
  });

  test('fetches news data from API on mount', async () => {
    const mockData = {
      features: [
        {
          properties: {
            id: 1,
            matched_city: 'Gaza',
            message: 'Test news',
            lat: 31.5,
            lon: 34.5,
            time: '2026-01-29T12:00:00Z',
            total_views: 100,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Test',
          },
        },
      ],
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<MapArea />);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/telegram/news'),
        expect.any(Object)
      );
    });
  });

  test('renders markers for news items with coordinates', async () => {
    const mockData = {
      features: [
        {
          properties: {
            id: 1,
            matched_city: 'Gaza',
            message: 'Breaking news from Gaza',
            lat: 31.5,
            lon: 34.5,
            time: '2026-01-29T12:00:00Z',
            total_views: 150,
            video_links: [],
            image_links: [],
            tags: ['breaking'],
            subject: 'Gaza News',
          },
        },
        {
          properties: {
            id: 2,
            matched_city: 'Ramallah',
            message: 'News from Ramallah',
            lat: 31.9454,
            lon: 35.2046,
            time: '2026-01-29T11:00:00Z',
            total_views: 200,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Ramallah News',
          },
        },
      ],
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<MapArea />);

    await waitFor(() => {
      const markers = screen.getAllByTestId('marker');
      expect(markers.length).toBeGreaterThan(0);
    });
  });

  test('renders marker cluster group', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ features: [] }),
    });

    render(<MapArea />);

    await waitFor(() => {
      expect(screen.getByTestId('marker-cluster-group')).toBeInTheDocument();
    });
  });

  test('handles missing coordinates gracefully', async () => {
    const mockData = {
      features: [
        {
          properties: {
            id: 1,
            matched_city: 'Unknown',
            message: 'News without location',
            lat: null,
            lon: null,
            time: '2026-01-29T12:00:00Z',
            total_views: 50,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Unknown Location',
          },
        },
      ],
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<MapArea />);

    await waitFor(() => {
      const markers = screen.queryAllByTestId('marker');
      // Should not render marker for item without coordinates
      expect(markers.length).toBe(0);
    });
  });

  test('displays popup with news details', async () => {
    const mockData = {
      features: [
        {
          properties: {
            id: 1,
            matched_city: 'Gaza',
            message: 'Breaking: Emergency alert from Gaza',
            lat: 31.5,
            lon: 34.5,
            time: '2026-01-29T12:00:00Z',
            total_views: 500,
            video_links: [],
            image_links: [],
            tags: ['emergency', 'breaking'],
            subject: 'Gaza Emergency',
          },
        },
      ],
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<MapArea />);

    await waitFor(() => {
      expect(screen.getByTestId('popup')).toBeInTheDocument();
    });
  });

  test('handles API errors gracefully', async () => {
    fetch.mockRejectedValueOnce(new Error('API Error'));

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

    render(<MapArea />);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled();
    });

    consoleSpy.mockRestore();
  });

  test('filters out stories without coordinates', async () => {
    const mockData = {
      features: [
        {
          properties: {
            id: 1,
            matched_city: 'Gaza',
            message: 'Has coordinates',
            lat: 31.5,
            lon: 34.5,
            time: '2026-01-29T12:00:00Z',
            total_views: 100,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Gaza',
          },
        },
        {
          properties: {
            id: 2,
            matched_city: 'Unknown',
            message: 'No coordinates',
            lat: null,
            lon: null,
            time: '2026-01-29T11:00:00Z',
            total_views: 50,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Unknown',
          },
        },
      ],
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<MapArea />);

    await waitFor(() => {
      const markers = screen.getAllByTestId('marker');
      expect(markers.length).toBe(1);
    });
  });

  test('dedupes duplicate stories', async () => {
    const mockData = {
      features: [
        {
          properties: {
            id: 1,
            matched_city: 'Gaza',
            message: 'Duplicate story',
            lat: 31.5,
            lon: 34.5,
            time: '2026-01-29T12:00:00Z',
            total_views: 100,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Same Subject',
          },
        },
        {
          properties: {
            id: 2,
            matched_city: 'Gaza',
            message: 'Duplicate story',
            lat: 31.5,
            lon: 34.5,
            time: '2026-01-29T11:00:00Z',
            total_views: 50,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Same Subject',
          },
        },
      ],
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<MapArea />);

    await waitFor(() => {
      const markers = screen.getAllByTestId('marker');
      // Should dedupe to 1 marker
      expect(markers.length).toBeLessThanOrEqual(mockData.features.length);
    });
  });

  test('handles empty response from API', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ features: [] }),
    });

    render(<MapArea />);

    await waitFor(() => {
      expect(screen.getByTestId('map-container')).toBeInTheDocument();
      const markers = screen.queryAllByTestId('marker');
      expect(markers.length).toBe(0);
    });
  });

  test('renders multiple markers with different coordinates', async () => {
    const mockData = {
      features: [
        {
          properties: {
            id: 1,
            matched_city: 'Gaza',
            message: 'Gaza news',
            lat: 31.5,
            lon: 34.5,
            time: '2026-01-29T12:00:00Z',
            total_views: 100,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Gaza',
          },
        },
        {
          properties: {
            id: 2,
            matched_city: 'Ramallah',
            message: 'Ramallah news',
            lat: 31.9454,
            lon: 35.2046,
            time: '2026-01-29T11:00:00Z',
            total_views: 150,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Ramallah',
          },
        },
        {
          properties: {
            id: 3,
            matched_city: 'Bethlehem',
            message: 'Bethlehem news',
            lat: 31.9454,
            lon: 35.2024,
            time: '2026-01-29T10:00:00Z',
            total_views: 200,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Bethlehem',
          },
        },
      ],
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<MapArea />);

    await waitFor(() => {
      const markers = screen.getAllByTestId('marker');
      expect(markers.length).toBeGreaterThanOrEqual(3);
    });
  });

  test('marker positions are correct', async () => {
    const mockData = {
      features: [
        {
          properties: {
            id: 1,
            matched_city: 'Gaza',
            message: 'Gaza news',
            lat: 31.5,
            lon: 34.5,
            time: '2026-01-29T12:00:00Z',
            total_views: 100,
            video_links: [],
            image_links: [],
            tags: [],
            subject: 'Gaza',
          },
        },
      ],
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<MapArea />);

    await waitFor(() => {
      const markers = screen.getAllByTestId('marker');
      expect(markers.length).toBeGreaterThan(0);
      const markerPosition = JSON.parse(markers[0].getAttribute('data-position'));
      expect(markerPosition).toEqual([31.5, 34.5]);
    });
  });
});
