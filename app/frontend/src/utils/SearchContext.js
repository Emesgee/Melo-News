import React, { createContext, useCallback, useContext, useState } from 'react';

const SearchContext = createContext();

// Shared reader filter. Narrows the Events shown on BOTH the Map and the List —
// one filter, two views. Backed by /api/events?q=&status=.
export const SearchProvider = ({ children }) => {
  const [filter, setFilterState] = useState({ q: '', status: '' });

  const setFilter = useCallback((patch) => {
    setFilterState((f) => ({ ...f, ...patch }));
  }, []);

  const clearFilter = useCallback(() => setFilterState({ q: '', status: '' }), []);

  return (
    <SearchContext.Provider value={{ filter, setFilter, clearFilter }}>
      {children}
    </SearchContext.Provider>
  );
};

export const useSearch = () => useContext(SearchContext);
