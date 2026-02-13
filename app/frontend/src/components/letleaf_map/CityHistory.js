import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import './CityHistory.css';

const CityHistory = ({ lat, lon, city }) => {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await api.post('/city-history', {
          lat,
          lon,
          city
        });

        if (response.data.status === 'success') {
          setHistory(response.data.history);
        } else if (response.data.fallback) {
          setHistory(response.data.fallback);
        } else if (response.data.error) {
          setError(response.data.error);
        }
      } catch (err) {
        console.error('Error fetching city history:', err);
        setError('Failed to load history');
      } finally {
        setLoading(false);
      }
    };

    if (lat && lon) {
      fetchHistory();
    }
  }, [lat, lon, city]);

  if (loading) {
    return (
      <div className="city-history">
        <div className="history-loading">
          <div className="spinner"></div>
          <p>Loading history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="city-history">
        <div className="history-error">
          <p>📚 {error}</p>
          <small>Configure AI API keys (OpenAI, Anthropic, etc.) to enable history</small>
        </div>
      </div>
    );
  }

  return (
    <div className="city-history">
      <div className="history-header">
        <span className="history-icon">📚</span>
        <h4>History</h4>
      </div>
      <div className="history-content">
        {history}
      </div>
    </div>
  );
};

export default CityHistory;
