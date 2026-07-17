import React, { useState } from 'react';
import './Search.css';
import { useSearch } from '../../utils/SearchContext';

// Slim filter over the one reader screen: a keyword + a status lens. Narrows the
// Events on both the Map and the List (via SearchContext -> /api/events).
const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'CORROBORATED', label: 'Corroborated' },
  { value: 'DISPUTED', label: 'Disputed' },
  { value: 'DEVELOPING', label: 'Developing' },
];

const Search = () => {
  const { filter, setFilter, clearFilter } = useSearch();
  const [term, setTerm] = useState(filter.q || '');

  const submit = (e) => {
    e.preventDefault();
    setFilter({ q: term.trim() });
  };

  const clear = () => {
    setTerm('');
    clearFilter();
  };

  const active = Boolean(filter.q || filter.status);

  return (
    <form className="search-topbar-form" onSubmit={submit} role="search">
      <div className="search-input-group">
        <input
          type="text"
          className="search-input"
          placeholder="Search events…"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          aria-label="Search events by keyword or place"
        />
        <button type="submit" className="search-submit-btn" title="Search" aria-label="Search">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
        </button>
      </div>

      <select
        className="search-status"
        value={filter.status || ''}
        onChange={(e) => setFilter({ status: e.target.value })}
        aria-label="Filter by trust status"
      >
        {STATUS_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>

      {active && (
        <button type="button" className="search-clear-all" onClick={clear} title="Clear filters">
          Clear
        </button>
      )}
    </form>
  );
};

export default Search;
