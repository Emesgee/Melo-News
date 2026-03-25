import React, { useState, useCallback } from 'react';
import { getTrending, getTensionIndex, getPredictions, votePrediction, getMarketData } from '../../services/api';
import { useToast } from '../../utils/ToastContext';
import useVisibilityPolling from '../../utils/useVisibilityPolling';
import './IntelSidebar.css';

// --- Tension Gauge (P1-6) ---
const TensionGauge = ({ score, change }) => {
  const getColor = (s) => {
    if (s >= 70) return '#dc2626';
    if (s >= 40) return '#f59e0b';
    return '#22c55e';
  };

  return (
    <div className="intel-tension">
      <h4 className="intel-section-title">Global Tension Index</h4>
      <div className="tension-gauge">
        <div className="tension-score" style={{ color: getColor(score) }}>
          {score.toFixed(0)}
        </div>
        <div className="tension-bar-bg">
          <div
            className="tension-bar-fill"
            style={{ width: `${Math.min(score, 100)}%`, backgroundColor: getColor(score) }}
          />
        </div>
        {change !== undefined && (
          <div className={`tension-change ${change >= 0 ? 'up' : 'down'}`}>
            {change >= 0 ? '↗' : '↘'} {Math.abs(change).toFixed(1)}% vs last period
          </div>
        )}
      </div>
    </div>
  );
};

// --- Trending Keywords (P1-5) ---
const TrendingKeywords = ({ keywords }) => (
  <div className="intel-trending">
    <h4 className="intel-section-title">Top Keywords (24h)</h4>
    <div className="trending-list">
      {keywords.map((kw, idx) => (
        <div key={kw.keyword} className="trending-item">
          <span className="trending-rank">#{idx + 1}</span>
          <span className="trending-keyword">{kw.keyword}</span>
          <span className="trending-count">{kw.count} mentions</span>
        </div>
      ))}
      {keywords.length === 0 && (
        <div className="intel-empty">No keywords yet</div>
      )}
    </div>
  </div>
);

// --- Prediction Polls (P2-9) ---
const PredictionPolls = ({ predictions, onVote }) => (
  <div className="intel-predictions">
    <h4 className="intel-section-title">Top Predictions</h4>
    {predictions.map(p => (
      <div key={p.id} className="prediction-card">
        <div className="prediction-category">{p.category?.toUpperCase()}</div>
        <p className="prediction-question">{p.question}</p>
        <div className="prediction-bar-container">
          <div className="prediction-bar">
            <div
              className="prediction-bar-yes"
              style={{ width: `${p.yes_pct}%` }}
            />
          </div>
          <div className="prediction-labels">
            <span className="prediction-yes">{p.yes_pct}% yes</span>
            <span className="prediction-no">{(100 - p.yes_pct).toFixed(1)}%</span>
          </div>
        </div>
        <div className="prediction-votes">{p.total_votes} votes</div>
        <div className="prediction-actions">
          <button className="pred-btn pred-yes" onClick={() => onVote(p.id, 'yes')}>Yes</button>
          <button className="pred-btn pred-no" onClick={() => onVote(p.id, 'no')}>No</button>
        </div>
      </div>
    ))}
    {predictions.length === 0 && (
      <div className="intel-empty">No active predictions</div>
    )}
  </div>
);

// --- Financial Widget (P2-12) ---
const FinancialWidget = ({ marketData }) => {
  if (!marketData || !marketData.rates) return null;
  return (
    <div className="intel-markets">
      <h4 className="intel-section-title">Markets</h4>
      <div className="market-rates">
        {Object.entries(marketData.rates).map(([currency, rate]) => (
          <div key={currency} className="market-rate-item">
            <span className="market-pair">USD/{currency}</span>
            <span className="market-value">{rate.toFixed(4)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// --- Main IntelSidebar ---
const IntelSidebar = ({ isOpen, onClose }) => {
  const [tension, setTension] = useState({ score: 0, change_vs_previous: 0 });
  const [keywords, setKeywords] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [marketData, setMarketData] = useState(null);
  const { addToast } = useToast();

  const fetchAll = useCallback(async () => {
    try {
      const [tensionResp, trendingResp, predResp] = await Promise.all([
        getTensionIndex(24),
        getTrending(24, 10),
        getPredictions(),
      ]);
      setTension(tensionResp.data);
      setKeywords(trendingResp.data.keywords || []);
      setPredictions(predResp.data.predictions || []);
    } catch (err) {
      addToast('Failed to load intelligence data.', 'error');
    }

    try {
      const market = await getMarketData();
      setMarketData(market);
    } catch { /* market data is optional */ }
  }, [addToast]);

  // Polls every 60s, pauses when tab is hidden, disabled when panel is closed
  useVisibilityPolling(fetchAll, 60000, isOpen);

  const handleVote = async (predId, vote) => {
    try {
      await votePrediction(predId, vote);
      const resp = await getPredictions();
      setPredictions(resp.data.predictions || []);
      addToast('Vote recorded!', 'success', 2000);
    } catch (err) {
      addToast('Failed to submit vote.', 'error');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="intel-sidebar">
      <div className="intel-sidebar-header">
        <h3>Intelligence Panel</h3>
        <button className="intel-close-btn" onClick={onClose}>✕</button>
      </div>
      <div className="intel-sidebar-content">
        <TensionGauge score={tension.score} change={tension.change_vs_previous} />
        <TrendingKeywords keywords={keywords} />
        <PredictionPolls predictions={predictions} onVote={handleVote} />
        <FinancialWidget marketData={marketData} />
      </div>
    </div>
  );
};

export default IntelSidebar;
