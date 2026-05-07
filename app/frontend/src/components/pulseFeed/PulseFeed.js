import React, { useState, useCallback, memo } from 'react';
import { getNewsFeed } from '../../services/api';
import { SEVERITY_CONFIG } from '../../constants/severity';
import { getRelativeTime } from '../../utils/mediaUtils';
import { useToast } from '../../utils/ToastContext';
import useVisibilityPolling from '../../utils/useVisibilityPolling';
import './PulseFeed.css';

const PulseFeed = ({ onStoryClick, filter = 'all' }) => {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  const fetchStories = useCallback(async () => {
    try {
      const resp = await getNewsFeed(100);
      // Handle both {items:[]} (Story API) and bare array (legacy shape)
      const raw = resp.data?.items ?? (Array.isArray(resp.data) ? resp.data : []);
      // Flatten nested Story shape so the rest of the component stays unchanged
      const normalized = raw.map(s => {
        const loc  = s.location   || {};
        const met  = s.metrics    || {};
        const ts   = s.timestamps || {};
        const prov = s.provenance || {};
        return {
          ...s,
          subject:          s.subject          || s.title,
          message:          s.body             || s.message,
          matched_city:     loc.city           || s.matched_city,
          severity:         met.severity       || s.severity        || 'LOW',
          confidence_score: met.confidence_score ?? s.confidence_score ?? null,
          time:             ts.published_at    || s.time,
          source:           prov.source_name   || s.source_type     || s.source,
          source_count:     met.source_count   ?? s.source_count    ?? 1,
          escalation:       met.escalation     || s.escalation      || null,
        };
      });
      let data = normalized;
      if (filter !== 'all') {
        data = data.filter(s => s.severity === filter);
      }
      setStories(data);
    } catch (err) {
      addToast('Failed to load news feed.', 'error');
    } finally {
      setLoading(false);
    }
  }, [filter, addToast]);

  // Polls every 30s, pauses when tab is hidden
  useVisibilityPolling(fetchStories, 30000);

  const [activeFilter, setActiveFilter] = useState('all');

  const filteredStories = activeFilter === 'all'
    ? stories
    : stories.filter(s => s.severity === activeFilter);

  return (
    <div className="pulse-feed">
      <div className="pulse-feed-header">
        <h3 className="pulse-feed-title">Pulse Feed</h3>
        <span className="pulse-feed-live">LIVE</span>
      </div>

      {/* Severity filter pills */}
      <div className="pulse-feed-filters">
        {['all', 'HIGH', 'MEDIUM', 'LOW'].map(f => (
          <button
            key={f}
            className={`pulse-filter-btn ${activeFilter === f ? 'active' : ''}`}
            onClick={() => setActiveFilter(f)}
            style={f !== 'all' && activeFilter === f ? { 
              backgroundColor: SEVERITY_CONFIG[f]?.color,
              color: 'white'
            } : {}}
          >
            {f === 'all' ? 'All' : `${SEVERITY_CONFIG[f]?.emoji} ${f}`}
          </button>
        ))}
      </div>

      {/* Stories list */}
      <div className="pulse-feed-list">
        {loading && <div className="pulse-feed-loading">Loading...</div>}
        {!loading && filteredStories.length === 0 && (
          <div className="pulse-feed-empty">No stories found</div>
        )}
        {filteredStories.map(story => {
          const sev = SEVERITY_CONFIG[story.severity] || SEVERITY_CONFIG.LOW;
          const confidence = story.confidence_score != null
            ? Math.round(story.confidence_score * 100)
            : null;

          return (
            <div
              key={story.id}
              className="pulse-story-card"
              onClick={() => onStoryClick?.(story)}
              style={{ borderLeftColor: sev.color }}
            >
              <div className="pulse-story-top">
                <span className="pulse-severity-badge" style={{ backgroundColor: sev.color }}>
                  {sev.emoji} {sev.label}
                </span>
                <span className="pulse-story-time">{getRelativeTime(story.time)}</span>
              </div>

              <h4 className="pulse-story-title">
                {story.subject || (story.message && story.message.slice(0, 80)) || 'Untitled'}
              </h4>

              <p className="pulse-story-desc">
                {story.message && story.message.slice(0, 120)}
                {story.message && story.message.length > 120 ? '...' : ''}
              </p>

              <div className="pulse-story-meta">
                {story.matched_city && (
                  <span className="pulse-meta-location">📍 {story.matched_city}</span>
                )}
                {confidence !== null && (
                  <span className="pulse-meta-confidence">
                    Confidence {confidence}%
                  </span>
                )}
                {story.source && story.source !== 'telegram' && (
                  <span className="pulse-meta-source">{story.source.toUpperCase()}</span>
                )}
                {story.source_count > 1 && (
                  <span className="pulse-meta-sources">{story.source_count} sources</span>
                )}
                {story.escalation && story.escalation !== 'stable' && (
                  <span className={`pulse-meta-escalation ${story.escalation}`}>
                    {story.escalation === 'escalation' ? '↗' : '↘'} {story.escalation}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default memo(PulseFeed);
