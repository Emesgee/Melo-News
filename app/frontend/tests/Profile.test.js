import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';

import Profile from '../src/pages/Profile';

// Mocking the API call and Axios instance
const mockApi = {
    defaults: {
        headers: {
            common: {
                Authorization: 'Bearer mocktoken',
            },
        },
    },
    get: jest.fn(() => Promise.resolve({ data: { name: 'Test User' } })),
};

jest.mock('../services/api', () => ({
    __esModule: true,
    ProfileData: jest.fn(() => Promise.resolve({ data: { name: 'Test User' } })),
    setAuthToken: jest.fn(),
    api: mockApi,
}));

describe('ProfileTest Component', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('renders ProfileTest component heading correctly', () => {
        render(
            <MemoryRouter>
                <Profile />
            </MemoryRouter>
        );
        expect(screen.getByRole('heading', { name: 'Profile Data' })).toBeInTheDocument();
    });
});