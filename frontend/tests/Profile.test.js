import React from 'react';
import { render, screen} from '@testing-library/react';
import '@testing-library/jest-dom';
import Profile from '../src/pages/Profile.js';

// Mocking the API call
jest.mock('../src/services/api', () => ({
    setAuthToken: jest.fn(),
    ProfileData: jest.fn().mockResolvedValue(),
    api: {
      defaults: { headers: { common: {} } },
    },
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
