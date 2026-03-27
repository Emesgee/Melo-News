import React, { useState, useEffect } from 'react';
import { getTensionIndex, getTrending, getEscalation, getNewsFeed } from '../services/api';
import { useToast } from '../utils/ToastContext';
import './AdminDashboard.css';

const StatCard = ({ title, value, subtitle, color = '#111' }) => (
  <div className="stat-card">
    <div className="stat-card__title">{title}</div>
    <div className="stat-card__value" style={{ color }}>{value}</div>
    {subtitle && <div className="stat-card__subtitle">{subtitle}</div>}
  </div>
);

const escalationClass = (status) => {
  if (status === 'escalation') return 'escalation';
  if (status === 'de-escalation') return 'de-escalation';
  return 'stable';
};

const escalationLabel = (status) => {
  if (status === 'escalation') return '↗ ESC';
  if (status === 'de-escalation') return '↘ DE';
  return '— STABLE';
};

const AdminDashboard = () => {
  const [tension, setTension] = useState(null);
  const [keywords, setKeywords] = useState([]);
  const [escalation, setEscalation] = useState(null);
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [tRes, kRes, eRes, sRes] = await Promise.all([
          getTensionIndex(24),
          getTrending(24, 15),
          getEscalation(24),
          getNewsFeed(500),
        ]);
        setTension(tRes.data);
        setKeywords(kRes.data.keywords || []);
        setEscalation(eRes.data);
        setStories(sRes.data || []);
      } catch (err) {
        addToast('Failed to load dashboard data.', 'error');
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
    const interval = setInterval(fetchAll, 60000);
    return () => clearInterval(interval);
  }, [addToast]);

  if (loading) return <div className="admin-loading">Loading dashboard...</div>;

  const highCount = stories.filter(s => s.severity === 'HIGH').length;
  const medCount = stories.filter(s => s.severity === 'MEDIUM').length;
  const lowCount = stories.filter(s => s.severity === 'LOW').length;
  const sources = {};
  stories.forEach(s => { sources[s.source || 'telegram'] = (sources[s.source || 'telegram'] || 0) + 1; });

  const tensionColor = tension?.score >= 70 ? '#dc2626' : tension?.score >= 40 ? '#f59e0b' : '#22c55e';

  return (
    <div className="admin-dashboard">
      <h1>Analytics Dashboard</h1>

      <div className="admin-stats-row">
        <StatCard title="Tension Index" value={tension?.score?.toFixed(0) || '0'} subtitle={`${tension?.change_vs_previous >= 0 ? '+' : ''}${tension?.change_vs_previous?.toFixed(1) || 0}% vs last period`} color={tensionColor} />
        <StatCard title="Stories (24h)" value={tension?.story_count || 0} subtitle={`${highCount} HIGH / ${medCount} MED / ${lowCount} LOW`} />
        <StatCard title="Areas Escalating" value={escalation?.summary?.escalating || 0} subtitle={`${escalation?.summary?.de_escalating || 0} de-escalating, ${escalation?.summary?.stable || 0} stable`} color="#dc2626" />
        <StatCard title="Active Sources" value={Object.keys(sources).length} subtitle={Object.entries(sources).map(([k, v]) => `${k}: ${v}`).join(' | ')} />
      </div>

      <div className="admin-panels-row">
        <div className="admin-panel">
          <h3 className="admin-panel__title">Source Breakdown</h3>
          {Object.entries(sources).map(([source, count]) => (
            <div key={source} className="source-row">
              <span className="source-row__name">{source}</span>
              <span className="source-row__count">{count} stories</span>
            </div>
          ))}
        </div>

        <div className="admin-panel">
          <h3 className="admin-panel__title">Top Keywords</h3>
          {keywords.slice(0, 10).map((kw, idx) => (
            <div key={kw.keyword} className="keyword-row">
              <span className="keyword-row__rank">#{idx + 1}</span>
              <span className="keyword-row__word">{kw.keyword}</span>
              <span className="keyword-row__count">{kw.count}</span>
            </div>
          ))}
        </div>
      </div>

      {escalation?.escalations && (
        <div className="admin-panel">
          <h3 className="admin-panel__title">City Escalation Status</h3>
          <div className="escalation-grid">
            {Object.entries(escalation.escalations).map(([city, status]) => {
              const cls = escalationClass(status);
              return (
                <div key={city} className={`escalation-item escalation-item--${cls}`}>
                  <span className="escalation-item__city">{city}</span>
                  <span className={`escalation-badge escalation-badge--${cls}`}>
                    {escalationLabel(status)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
