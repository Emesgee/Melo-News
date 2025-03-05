//search.js
import React, { useState } from 'react';
import axios from 'axios';
import './Search.css';
import { FaCity, FaGlobeAmericas, FaSearch } from 'react-icons/fa';
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";

const Search = ({ onSearchResult }) => {
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
  const [showSearch, setShowSearch] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    setMessage('');

    const templateIds = [1];
    if (fromDate || toDate) templateIds.push(2);
    if (filters.city || filters.country) templateIds.push(3);

    const searchData = {
      user_id: 1,
      term,
      filters: {
        ...filters,
        from_date: fromDate ? fromDate.toISOString() : null,
        to_date: toDate ? toDate.toISOString() : null,
      },
      template_ids: templateIds,
    };

    try {
      const response = await axios.post('/api/search', searchData);
      setMessage(response.data.message || 'Search completed successfully.');
      
      // Pass results to parent directly
      if (onSearchResult) onSearchResult(response.data.results);

      setShowSearch(false);
    } catch (error) {
      setMessage('Error fetching search results. Please try again.');
    }
  };

  return (
    <div className="search-container">
      <button type="button" className="search-toggle-button" onClick={() => setShowSearch(true)}>
        <FaSearch />
      </button>

      {showSearch && (
        <div className="search-overlay">
          <form onSubmit={handleSearch} className="search-group">
            <input
              type="text"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="Enter search term"
              required
            />
            <button type="submit">Search</button>
          </form>

          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <div className="date-fields">
              <DatePicker
                label="From Date"
                value={fromDate}
                onChange={(newValue) => setFromDate(newValue)}
              />
              <DatePicker
                label="To Date"
                value={toDate}
                onChange={(newValue) => setToDate(newValue)}
              />
            </div>
          </LocalizationProvider>

          <div className="filter-fields">
            <div className="filter-group">
              <FaCity className="icon" />
              <input
                type="text"
                value={filters.city}
                onChange={(e) => setFilters((prev) => ({ ...prev, city: e.target.value }))}
                placeholder="Enter city"
              />
            </div>
            <div className="filter-group">
              <FaGlobeAmericas className="icon" />
              <input
                type="text"
                value={filters.country}
                onChange={(e) => setFilters((prev) => ({ ...prev, country: e.target.value }))}
                placeholder="Enter country"
              />
            </div>
          </div>

          {message && <p className="message">{message}</p>}
        </div>
      )}
    </div>
  );
};

export default Search;
