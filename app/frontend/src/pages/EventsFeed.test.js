import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EventsFeed from './EventsFeed';

jest.mock('../services/api', () => ({
  getEvents: jest.fn(),
  getEventDetail: jest.fn(),
}));
import { getEvents } from '../services/api';

const EVENTS = [
  {
    id: 1, status: 'CORROBORATED', title: 'Market blast',
    location: { city: 'Testoria', country: 'Sandboxia' }, severity: 'MEDIUM',
    confidence_band: 'HIGH', corroboration: { counted: 2, supporting: 1 },
    member_count: 3, is_overridden: false,
  },
  {
    id: 2, status: 'DISPUTED', title: 'Checkpoint incident',
    location: { city: 'Testoria' }, severity: 'HIGH',
    confidence_band: 'LOW', corroboration: { counted: 2, supporting: 0 },
    member_count: 2, is_overridden: true,
  },
];

beforeEach(() => jest.clearAllMocks());

test('renders events with trust badges, corroboration, and the dispute warning', async () => {
  getEvents.mockResolvedValue({ data: { events: EVENTS } });
  render(<EventsFeed />);

  await waitFor(() => expect(screen.getByText('Market blast')).toBeInTheDocument());

  // status badges convey the basis of trust
  expect(screen.getByText('Corroborated')).toBeInTheDocument();
  expect(screen.getByText('Disputed')).toBeInTheDocument();

  // corroboration shown concretely (both events have 2 counted)
  expect(screen.getAllByText(/corroborating/).length).toBe(2);
  // anonymous supporting shown SEPARATELY (only event 1 has it)
  expect(screen.getByText(/\+1 anonymous/)).toBeInTheDocument();

  // DISPUTED is prominent
  expect(screen.getByText(/conflict — treat with caution/)).toBeInTheDocument();
});

test('shows an empty-state message when there are no events', async () => {
  getEvents.mockResolvedValue({ data: { events: [] } });
  render(<EventsFeed />);
  await waitFor(() =>
    expect(screen.getByText(/No corroborated or developing events yet/)).toBeInTheDocument()
  );
});
