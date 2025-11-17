import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../services/api';
import './Search.css';
import { FaCity, FaGlobeAmericas, FaSearch } from 'react-icons/fa';
import DateRangePicker from '../calendar/DateRangePicker';

const DEFAULT_TAGS = [
  { key: 'default-politics', name: 'Politics', icon: '🏛️', color: '#2563eb', searchTerm: 'politics' },
  { key: 'default-technology', name: 'Technology', icon: '💻', color: '#7c3aed', searchTerm: 'technology' },
  { key: 'default-sports', name: 'Sports', icon: '⚽', color: '#dc2626', searchTerm: 'sports' },
  { key: 'default-weather', name: 'Weather', icon: '🌦️', color: '#0891b2', searchTerm: 'weather' },
  { key: 'default-health', name: 'Health', icon: '⚕️', color: '#059669', searchTerm: 'health' },
];

const TAG_STYLE_MAP = {
  search: { icon: '🔍', color: '#2563eb' },
  content: { icon: '🧠', color: '#7c3aed' },
  location: { icon: '📍', color: '#dc2626' },
  media: { icon: '🎥', color: '#0891b2' },
  event: { icon: '🗓️', color: '#059669' },
  topic: { icon: '📰', color: '#f97316' },
  default: { icon: '🏷️', color: '#6b7280' },
};

const toTitleCase = (value = '') => value
  .toLowerCase()
  .split(/\s+/)
  .filter(Boolean)
  .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
  .join(' ');

const normaliseTagToken = (token = '') => token
  .replace(/[_-]/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

const extractRawTags = (result) => {
  const rawTags = new Set();
  const candidateFields = [
    result?.tags,
    result?.tag_list,
    result?.generated_tags,
    result?.auto_tags,
    result?.news_tags,
    result?.metadata?.tags,
  ];

  candidateFields.forEach((field) => {
    if (!field) return;
    if (Array.isArray(field)) {
      field.forEach((item) => {
        if (typeof item === 'string') rawTags.add(item);
      });
    } else if (typeof field === 'string') {
      field.split(/[|,]/).forEach((item) => {
        const token = item.trim();
        if (token) rawTags.add(token);
      });
    }
  });

  if (result?.city) rawTags.add(`location:${result.city}`);
  if (result?.country) rawTags.add(`location:${result.country}`);
  if (result?.media_type) rawTags.add(`media:${result.media_type}`);
  if (result?.category) rawTags.add(`topic:${result.category}`);

  return Array.from(rawTags);
};

const deriveTagObject = (tagString, score = 1) => {
  if (!tagString) return null;
  const [prefixRaw, remainderRaw] = tagString.includes(':') ? tagString.split(':', 2) : ['search', tagString];
  const prefix = prefixRaw.toLowerCase().trim() || 'search';
  const token = normaliseTagToken(remainderRaw || prefixRaw);
  if (!token) return null;

  const style = TAG_STYLE_MAP[prefix] || TAG_STYLE_MAP.default;
  const displayName = toTitleCase(token);
  const sanitisedToken = token.replace(/\s+/g, '-').toLowerCase();

  return {
    key: `${prefix}-${sanitisedToken}`,
    name: displayName,
    icon: style.icon,
    color: style.color,
    searchTerm: token,
    prefix,
    score,
  };
};

const buildSuggestedTags = (results = [], { fallbackTerm } = {}) => {
  const counts = new Map();

  results.forEach((result) => {
    extractRawTags(result).forEach((tag) => {
      const normalised = tag.trim().toLowerCase();
      if (!normalised) return;
      counts.set(normalised, (counts.get(normalised) || 0) + 1);
    });
  });

  if (fallbackTerm && fallbackTerm !== '*') {
    const fallbackTag = `search:${fallbackTerm}`;
    counts.set(fallbackTag, Math.max(counts.get(fallbackTag) || 0, results.length || 1));
  }

  const seenKeys = new Set();
  const sorted = Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([tag, score]) => deriveTagObject(tag, score))
    .filter(Boolean)
    .filter((tagObj) => {
      if (seenKeys.has(tagObj.key)) return false;
      seenKeys.add(tagObj.key);
      return true;
    })
    .slice(0, 8);

  return sorted;
};

const Search = ({ onSearchResult, showAsTopbar = false }) => {
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

  const tagsToRender = useMemo(() => (
    suggestedTags && suggestedTags.length > 0 ? suggestedTags : DEFAULT_TAGS
  ), [suggestedTags]);

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
      const response = await api.post('/api/search', searchData);
      setMessage(response.data.message || 'Search completed successfully.');

      // Ensure we're getting an array of results
      const results = Array.isArray(response.data.results) ? response.data.results : (response.data.results ? [response.data.results] : []);
      
      if (onSearchResult) {
        onSearchResult(results);
      }

      updateSuggestedTags(results);

      // Don't close the search in topbar mode
      if (!showAsTopbar) {
        setShowSearch(false);
      }
    } catch (error) {
      console.error('Search error:', error);
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
      
      api.post('/api/search', searchData).then(response => {
        const results = Array.isArray(response.data.results) ? response.data.results : (response.data.results ? [response.data.results] : []);
        if (onSearchResult) onSearchResult(results);
        updateSuggestedTags(results);
      }).catch(err => console.error('Tag search error:', err));
    }, 0);
  };

  return (
    <div className={`search-container ${showAsTopbar ? 'search-topbar' : ''}`}>
      {!showAsTopbar && (
        <button
          type="button"
          className="search-toggle-button"
          onClick={() => setShowSearch(true)}
          aria-label="Open Search"
        >
          <FaSearch />
        </button>
      )}

      {showSearch && (
        <div className={`search-overlay ${showAsTopbar ? 'search-overlay-topbar' : ''}`}>
          <form onSubmit={handleSearch} className="search-group">
            <input
              type="text"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Enter search term"
              required
              autoFocus={showAsTopbar}
            />
            <button type="submit" disabled={loading}>{loading ? 'Searching...' : 'Search'}</button>
          </form>

          {/* Quick tags - only in topbar mode */}
          {showAsTopbar && (
            <div className="search-tags">
              {tagsToRender.map((tag) => (
                <button
                  key={tag.key}
                  type="button"
                  className="search-tag"
                  onClick={() => handleTagClick(tag)}
                  style={{ '--tag-color': tag.color }}
                  title={`Search for ${tag.name}`}
                >
                  <span className="tag-icon">{tag.icon}</span>
                  <span className="tag-name">{tag.name}</span>
                </button>
              ))}
            </div>
          )}

          {!showAsTopbar && (
            <>
              <DateRangePicker
                fromDate={fromDate}
                toDate={toDate}
                onFromChange={(newValue) => setFromDate(newValue)}
                onToChange={(newValue) => setToDate(newValue)}
              />

              <div className="filter-fields">
                <div className="filter-group">
                  <FaCity className="icon" />
                  <input
                    type="text"
                    value={filters.city}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, city: e.target.value }))
                    }
                    placeholder="Enter city"
                  />
                </div>
                <div className="filter-group">
                  <FaGlobeAmericas className="icon" />
                  <input
                    type="text"
                    value={filters.country}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, country: e.target.value }))
                    }
                    placeholder="Enter country"
                  />
                </div>
              </div>

              {message && <p className="message">{message}</p>}

              <button
                type="button"
                className="close-button"
                onClick={() => setShowSearch(false)}
                aria-label="Close search"
              >
                ✕
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Search;
