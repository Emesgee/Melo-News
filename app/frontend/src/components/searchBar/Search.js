import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { api } from '../../services/api';
import './Search.css';
import DateRangePicker from '../calendar/DateRangePicker';
import { DEFAULT_TAGS, CATEGORY_ICONS, buildSuggestedTags, groupTagsByCategory } from '../../utils/searchUtils';
import { useSearch } from '../../utils/SearchContext';

const Search = ({ showAsTopbar = false }) => {
  const { setSearchResults, clearResults } = useSearch();
  const [term, setTerm] = useState('');
  const [fromDate, setFromDate] = useState(null);
  const [toDate, setToDate] = useState(null);
  const [filters, setFilters] = useState({
    city: '',
    country: '',
    lat: 55.70014671652232,
    lon: 12.574800999639141,
  });
  const [message, setMessage] = useState('');
  const [showSearch, setShowSearch] = useState(showAsTopbar);
  const [loading, setLoading] = useState(false);
  const [suggestedTags, setSuggestedTags] = useState(DEFAULT_TAGS);
  const [dateOpen, setDateOpen] = useState(false);
  const [resultCount, setResultCount] = useState(0);
  const dateDropdownRef = useRef(null);
  const MAX_VISIBLE_CHIPS = 4;

  const formatDateLabel = () => {
    if (!fromDate && !toDate) return 'Any time';
    const fmt = (d) => d ? d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '…';
    if (fromDate && toDate) return `${fmt(fromDate)} – ${fmt(toDate)}`;
    if (fromDate) return `From ${fmt(fromDate)}`;
    return `Until ${fmt(toDate)}`;
  };

  const hasActiveFilters = !!(term || fromDate || toDate);

  const handleClearAll = () => {
    setTerm('');
    setFromDate(null);
    setToDate(null);
    setMessage('');
    setResultCount(0);
    setSuggestedTags(DEFAULT_TAGS);
    clearResults();
  };

  const tagsToRender = useMemo(() => (
    suggestedTags && suggestedTags.length > 0 ? suggestedTags : DEFAULT_TAGS
  ), [suggestedTags]);

  const groupedTags = useMemo(() => groupTagsByCategory(tagsToRender), [tagsToRender]);

  const updateSuggestedTags = useCallback((results) => {
    if (!showAsTopbar) return;
    const generated = buildSuggestedTags(results, { fallbackTerm: term });
    if (generated.length > 0) {
      setSuggestedTags(generated);
    } else {
      setSuggestedTags(DEFAULT_TAGS);
    }
  }, [showAsTopbar, term]);

  // Handle ESC key to close search overlay
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') {
        // Only close on ESC if not in topbar mode
        if (!showAsTopbar) {
          setShowSearch(false);
        }
      }
    };

    if (showSearch && !showAsTopbar) {
      document.addEventListener('keydown', handleEsc);
    } else {
      document.removeEventListener('keydown', handleEsc);
    }

    // Cleanup on unmount
    return () => document.removeEventListener('keydown', handleEsc);
  }, [showSearch, showAsTopbar]);

  const handleSearch = async (e) => {
    e.preventDefault();
    setMessage('');

    // Validate 24-hour maximum constraint
    if (fromDate && toDate) {
      const timeDiff = Math.abs(toDate - fromDate);
      const hoursDiff = timeDiff / (1000 * 60 * 60);
      
      if (hoursDiff > 24) {
        setMessage('Date range cannot exceed 24 hours. Please adjust your selection.');
        return;
      }
    }

    // If no search term, still search to get recent results
    const templateIds = [1]; // Always include basic template
    if (fromDate || toDate) templateIds.push(2);
    if (filters.city || filters.country) templateIds.push(3);

    const searchData = {
      user_id: 1,
      term: term || '*', // Use wildcard if no term to get all results
      filters: {
        ...filters,
        from_date: fromDate ? fromDate.toISOString() : null,
        to_date: toDate ? toDate.toISOString() : null,
      },
      template_ids: templateIds,
    };

    try {
      setLoading(true);
      const response = await api.post('search', searchData);
      setMessage(response.data.message || 'Search completed successfully.');

      // Ensure we're getting an array of results
      const results = Array.isArray(response.data.results) ? response.data.results : (response.data.results ? [response.data.results] : []);
      
      setSearchResults(results);
      setResultCount(results.length);
      updateSuggestedTags(results);

      // Don't close the search in topbar mode
      if (!showAsTopbar) {
        setShowSearch(false);
      }
    } catch (error) {
      setMessage('Error fetching search results. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleTagClick = (tag) => {
    const tagSearchTerm = tag?.searchTerm || tag?.name || '';
    if (!tagSearchTerm) return;

    setTerm(tagSearchTerm);
    // Trigger search immediately after setting term
    setTimeout(() => {
      const searchData = {
        user_id: 1,
        term: tagSearchTerm,
        filters: {
          ...filters,
          from_date: null,
          to_date: null,
        },
        template_ids: [1],
      };
      
      api.post('search', searchData).then(response => {
        const results = Array.isArray(response.data.results) ? response.data.results : (response.data.results ? [response.data.results] : []);
        setSearchResults(results);
        updateSuggestedTags(results);
      }).catch(() => { /* tag search failed */ });
    }, 0);
  };

  // Auto-dismiss topbar message after 3s
  useEffect(() => {
    if (message && showAsTopbar) {
      const timer = setTimeout(() => setMessage(''), 3000);
      return () => clearTimeout(timer);
    }
  }, [message, showAsTopbar]);

  // Close date dropdown on outside click
  useEffect(() => {
    const handleOutside = (e) => {
      if (dateDropdownRef.current && !dateDropdownRef.current.contains(e.target)) {
        setDateOpen(false);
      }
    };
    if (dateOpen) document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, [dateOpen]);

  // Check if date range exceeds 24 hours
  const isDateRangeExceeded = () => {
    if (!fromDate || !toDate) return false;
    const timeDiff = Math.abs(toDate - fromDate);
    const hoursDiff = timeDiff / (1000 * 60 * 60);
    return hoursDiff > 24;
  };

  /* ── Topbar mode ────────────────────────────────────────────── */
  if (showAsTopbar) {
    return (
      <div className="search-wrapper search-topbar">
        <form onSubmit={handleSearch} className="search-topbar-form">

          {/* Unified search input + submit pill */}
          <div className="search-input-group">
            <input
              type="text"
              placeholder="Search stories…"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              className="search-input"
            />
            <button type="submit" disabled={loading} className="search-submit-btn" title="Search">
              {loading ? (
                <svg className="search-spin" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <path d="M12 2a10 10 0 0 1 10 10" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
                </svg>
              )}
            </button>
          </div>

          {/* Topic chips (max 4 visible + overflow badge) */}
          <div className="search-chips">
            {tagsToRender.slice(0, MAX_VISIBLE_CHIPS).map((tag) => (
              <button
                key={tag.key}
                type="button"
                onClick={() => handleTagClick(tag)}
                className={`search-chip${term === tag.searchTerm ? ' active' : ''}`}
                style={{ '--chip-color': tag.color }}
                title={tag.name}
              >
                <span>{tag.icon}</span>
                <span>{tag.name}</span>
              </button>
            ))}
            {tagsToRender.length > MAX_VISIBLE_CHIPS && (
              <span className="search-chips-more">+{tagsToRender.length - MAX_VISIBLE_CHIPS}</span>
            )}
          </div>

          {/* Compact date-range button + dropdown */}
          <div className="search-date-wrap" ref={dateDropdownRef}>
            <button
              type="button"
              className={`search-date-btn${(fromDate || toDate) ? ' has-value' : ''}`}
              onClick={() => setDateOpen((o) => !o)}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              <span>{formatDateLabel()}</span>
            </button>

            {dateOpen && (
              <div className="search-date-dropdown">
                <div className="search-date-row">
                  <label className="search-date-label">From</label>
                  <input
                    type="date"
                    className={`search-date-input${isDateRangeExceeded() ? ' error' : ''}`}
                    value={fromDate ? fromDate.toISOString().split('T')[0] : ''}
                    onChange={(e) => setFromDate(e.target.value ? new Date(e.target.value) : null)}
                  />
                </div>
                <div className="search-date-row">
                  <label className="search-date-label">To</label>
                  <input
                    type="date"
                    className={`search-date-input${isDateRangeExceeded() ? ' error' : ''}`}
                    value={toDate ? toDate.toISOString().split('T')[0] : ''}
                    onChange={(e) => setToDate(e.target.value ? new Date(e.target.value) : null)}
                  />
                </div>
                {isDateRangeExceeded() && (
                  <p className="search-date-error">⚠ Max 24-hour range</p>
                )}
                <div className="search-date-actions">
                  <button
                    type="button"
                    className="search-date-clear-btn"
                    onClick={() => { setFromDate(null); setToDate(null); setDateOpen(false); }}
                  >
                    Clear
                  </button>
                  <button
                    type="button"
                    className="search-date-apply-btn"
                    onClick={() => setDateOpen(false)}
                  >
                    Apply
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Result count — announced to screen readers */}
          <span className="search-result-count" role="status" aria-live="polite" aria-atomic="true">
            {resultCount > 0 ? `${resultCount} result${resultCount !== 1 ? 's' : ''}` : ''}
          </span>

          {/* Clear all active filters */}
          {hasActiveFilters && (
            <button type="button" className="search-clear-all" onClick={handleClearAll} title="Clear all filters">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
              Clear
            </button>
          )}
        </form>

        {message && (
          <p className={`search-message topbar-message${message.toLowerCase().includes('error') ? ' error' : ' success'}`}>
            {message}
          </p>
        )}
      </div>
    );
  }

  /* ── Full-page mode (unchanged) ─────────────────────────────── */
  return (
    <div className="search-wrapper">
      <form onSubmit={handleSearch} className="search-full">
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' }}>
          <input
            type="text"
            placeholder="Search stories…"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            className="search-input"
          />
          <button type="submit" disabled={loading} className="search-button">
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>

        {message && (
          <p className={`search-message${message.toLowerCase().includes('error') ? ' error' : ' success'}`}>
            {message}
          </p>
        )}

        <div className="tags-container">
          {Object.entries(groupedTags).map(([category, tags]) => (
            <div key={category} className="tag-category">
              <h4 className="category-header">
                {CATEGORY_ICONS[category] || '🏷️'} {category}
              </h4>
              <div className="tags-list">
                {tags.map((tag) => (
                  <button
                    key={tag.key}
                    type="button"
                    onClick={() => handleTagClick(tag)}
                    className="tag-button"
                    style={{ backgroundColor: tag.color, color: 'white', border: 'none' }}
                  >
                    <span className="tag-icon-text">
                      <span>{tag.icon}</span>
                      <span>{tag.name}</span>
                    </span>
                    {tag.score > 0 && <span className="tag-badge">{tag.score}</span>}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </form>
    </div>
  );
};
export default Search;  