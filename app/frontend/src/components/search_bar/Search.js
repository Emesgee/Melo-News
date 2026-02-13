import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../services/api';
import './Search.css';
import { FaCity, FaGlobeAmericas, FaSearch } from 'react-icons/fa';
import DateRangePicker from '../calendar/DateRangePicker';

const DEFAULT_TAGS = [
  { key: 'default-politics', name: 'Politics', icon: '🏛️', color: '#2563eb', searchTerm: 'politics', category: 'Topics', score: 0 },
  { key: 'default-technology', name: 'Technology', icon: '💻', color: '#7c3aed', searchTerm: 'technology', category: 'Topics', score: 0 },
  { key: 'default-sports', name: 'Sports', icon: '⚽', color: '#dc2626', searchTerm: 'sports', category: 'Topics', score: 0 },
  { key: 'default-weather', name: 'Weather', icon: '🌦️', color: '#0891b2', searchTerm: 'weather', category: 'Topics', score: 0 },
  { key: 'default-health', name: 'Health', icon: '⚕️', color: '#059669', searchTerm: 'health', category: 'Topics', score: 0 },
];

const TAG_STYLE_MAP = {
  search: { icon: '🔍', color: '#2563eb', category: 'Topics' },
  content: { icon: '🧠', color: '#7c3aed', category: 'Topics' },
  location: { icon: '📍', color: '#dc2626', category: 'Locations' },
  media: { icon: '🎥', color: '#0891b2', category: 'Media Types' },
  event: { icon: '🗓️', color: '#059669', category: 'Events' },
  topic: { icon: '📰', color: '#f97316', category: 'Topics' },
  default: { icon: '🏷️', color: '#6b7280', category: 'Other' },
};

const CATEGORY_ICONS = {
  Topics: '📌',
  Locations: '📍',
  'Media Types': '🎥',
  Events: '🗓️',
  Other: '🏷️',
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
    category: style.category || 'Other',
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

  // Group tags by category
  const groupedTags = useMemo(() => {
    const groups = {};
    tagsToRender.forEach((tag) => {
      const category = tag.category || 'Other';
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(tag);
    });
    
    // Sort categories by priority and filter empty categories
    const categoryOrder = ['Topics', 'Locations', 'Media Types', 'Events', 'Other'];
    const sorted = {};
    categoryOrder.forEach((cat) => {
      if (groups[cat] && groups[cat].length > 0) {
        sorted[cat] = groups[cat];
      }
    });
    Object.keys(groups).forEach((cat) => {
      if (!sorted[cat] && groups[cat] && groups[cat].length > 0) {
        sorted[cat] = groups[cat];
      }
    });
    
    return sorted;
  }, [tagsToRender]);

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
      const response = await api.post('/search', searchData);
      setMessage(response.data.message || 'Search completed successfully.');

      // Ensure we're getting an array of results
      let results = Array.isArray(response.data.results) ? response.data.results : (response.data.results ? [response.data.results] : []);
      
      // Filter results to only show items from the last 24 hours
      const now = new Date();
      const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      
      results = results.filter(result => {
        const resultTime = result.time ? new Date(result.time) : null;
        if (!resultTime) return false; // Exclude results without timestamps
        return resultTime >= twentyFourHoursAgo;
      });
      
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
      
      api.post('/search', searchData).then(response => {
        const results = Array.isArray(response.data.results) ? response.data.results : (response.data.results ? [response.data.results] : []);
        if (onSearchResult) onSearchResult(results);
        updateSuggestedTags(results);
      }).catch(err => console.error('Tag search error:', err));
    }, 0);
  };

  // Check if date range exceeds 24 hours
  const isDateRangeExceeded = () => {
    if (!fromDate || !toDate) return false;
    const timeDiff = Math.abs(toDate - fromDate);
    const hoursDiff = timeDiff / (1000 * 60 * 60);
    return hoursDiff > 24;
  };

  return (
    <div className={`search-wrapper ${showAsTopbar ? 'search-topbar' : ''}`}>
      <form onSubmit={handleSearch} className={showAsTopbar ? 'search-topbar' : 'search-full'}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Search stories..."
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            className="search-input"
          />
          <button type="submit" disabled={loading} style={{ padding: '8px 16px' }}>
            {loading ? '🔄' : '🔍'}
          </button>

          {/* Tags inline for topbar */}
          {showAsTopbar && tagsToRender.length > 0 && (
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flex: 1, marginLeft: '8px', overflow: 'auto', maxWidth: '250px' }}>
              {tagsToRender.slice(0, 5).map((tag) => (
                <button
                  key={tag.key}
                  type="button"
                  onClick={() => handleTagClick(tag)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    border: `1px solid ${tag.color}`,
                    background: `${tag.color}20`,
                    color: tag.color,
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: '500',
                    whiteSpace: 'nowrap',
                    flexShrink: 0
                  }}
                >
                  {tag.icon} {tag.name}
                </button>
              ))}
            </div>
          )}

          {/* Date range picker inline */}
          {showAsTopbar && (
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexShrink: 0 }}>
              <input
                type="date"
                value={fromDate ? fromDate.toISOString().split('T')[0] : ''}
                onChange={(e) => setFromDate(e.target.value ? new Date(e.target.value) : null)}
                style={{
                  padding: '6px 10px',
                  borderRadius: '4px',
                  border: isDateRangeExceeded() ? '2px solid #dc2626' : '1px solid #d1d5db',
                  fontSize: '12px',
                  backgroundColor: isDateRangeExceeded() ? '#fee2e2' : 'white',
                  cursor: 'pointer'
                }}
                title="From date (max 24 hours range)"
              />
              <span style={{ fontSize: '12px', color: '#666' }}>to</span>
              <input
                type="date"
                value={toDate ? toDate.toISOString().split('T')[0] : ''}
                onChange={(e) => setToDate(e.target.value ? new Date(e.target.value) : null)}
                style={{
                  padding: '6px 10px',
                  borderRadius: '4px',
                  border: isDateRangeExceeded() ? '2px solid #dc2626' : '1px solid #d1d5db',
                  fontSize: '12px',
                  backgroundColor: isDateRangeExceeded() ? '#fee2e2' : 'white',
                  cursor: 'pointer'
                }}
                title="To date (max 24 hours range)"
              />
            </div>
          )}
        </div>

        {message && <p style={{ marginTop: '8px', color: '#666' }}>{message}</p>}
      </form>
    </div>
  );
};
export default Search;  