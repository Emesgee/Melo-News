import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoadingScreen from './LoadingScreen';

describe('LoadingScreen', () => {
  it('renders the app title', () => {
    render(<LoadingScreen />);
    expect(screen.getByText('MELO-NEWS')).toBeInTheDocument();
  });

  it('renders the subtitle', () => {
    render(<LoadingScreen />);
    expect(screen.getByText('Community Intelligence Platform')).toBeInTheDocument();
  });

  it('renders a loading label', () => {
    render(<LoadingScreen />);
    expect(screen.getByText('LOADING')).toBeInTheDocument();
  });

  it('shows session verification step', () => {
    render(<LoadingScreen />);
    expect(screen.getByText(/verifying session/i)).toBeInTheDocument();
  });

  it('renders the progress bar', () => {
    const { container } = render(<LoadingScreen />);
    expect(container.querySelector('.loading-screen__bar-fill')).toBeInTheDocument();
  });
});
