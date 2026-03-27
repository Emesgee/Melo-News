import React, { createContext, useContext, useState, useCallback } from 'react';
import { dedupeStories } from './storyUtils';

const SearchContext = createContext();

export const SearchProvider = ({ children }) => {
  const [searchResults, setSearchResultsRaw] = useState([]);

  /** Deduplicate before storing — single source of truth. */
  const setSearchResults = useCallback((results = []) => {
    setSearchResultsRaw(dedupeStories(Array.isArray(results) ? results : []));
  }, []);

  const clearResults = useCallback(() => setSearchResultsRaw([]), []);

  return (
    <SearchContext.Provider value={{ searchResults, setSearchResults, clearResults }}>
      {children}
    </SearchContext.Provider>
  );
};

export const useSearch = () => useContext(SearchContext);
