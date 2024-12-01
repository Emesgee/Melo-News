import React from 'react';
import { render, screen, fireEvent, profileDataElement } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import Login from '../src/pages/Profile';
import { loginUser, setAuthToken, ProfieData } from '../src/services/api';
import Profile from '../src/pages/Profile';

// Mocking the API call
jest.mock('../src/services/api', () => ({
    ProfilData: jest.fn(),
    setAuthToken: jest.fn(),
  }));

describe('ProfileTest Component', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('renders ProfileTest component heading correctly', () => {
        render(<Profile />);
        expect(screen.getByRole('heading', {name:'Profile Data'})).toBeInTheDocument()
    });

});
