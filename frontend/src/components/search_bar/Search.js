// src/pages/Search.js
import React, { useState } from 'react';
import axios from 'axios';
import './Search.css';
import { FaCalendarAlt, FaCity, FaGlobeAmericas } from 'react-icons/fa';

const Search = ({ onSearchResult }) => {
  const [term, setTerm] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [filters, setFilters] = useState({
    city: '',
    country: '',
    lat: 55.70014671652232,
    lon: 12.574800999639141,
  });
  const [searchResults, setSearchResults] = useState([]);
  const [message, setMessage] = useState('');

  const handleInputChange = (e) => {
    const value = e.target.value;
    setTerm(value);
  };

  const handleFromDateChange = (e) => setFromDate(e.target.value);
  const handleToDateChange = (e) => setToDate(e.target.value);
  const handleCityChange = (e) => setFilters((prev) => ({ ...prev, city: e.target.value }));
  const handleCountryChange = (e) => setFilters((prev) => ({ ...prev, country: e.target.value }));

  const handleSearch = async (e) => {
    e.preventDefault();
    setMessage('');

    const templateIds = [1];
    if (fromDate || toDate) {
      templateIds.push(2);
    }
    if (filters.city || filters.country) {
      templateIds.push(3);
    }

    const adjustedToDate = toDate ? new Date(new Date(toDate).setHours(23, 59, 59, 999)).toISOString() : null;

    const searchData = {
      user_id: 1,
      term,
      filters: {
        ...filters,
        from_date: fromDate || null,
        to_date: adjustedToDate || null,
      },
      template_ids: templateIds,
    };

    try {
      const response = await axios.post('/api/search', searchData);
      setSearchResults(response.data.results);
      setMessage(response.data.message || 'Search completed successfully.');

      if (onSearchResult) {
        onSearchResult(response.data.results);
      }
    } catch (error) {
      console.error('Error fetching search results:', error);
      setMessage('Error fetching search results. Please try again.');
    }
  };

  const handleBackClick = () => {
    setTerm(''); // Clear search term
    setMessage(''); // Clear any messages
    setSearchResults([]); // Clear search results
  };

  return (
    <div className="search-container">
      {/* Back arrow button */}
      <button type="button" className="back-button" onClick={handleBackClick}>
        ←
      </button>

      <form onSubmit={handleSearch} className="search-group">
        <input
          type="text"
          value={term}
          onChange={handleInputChange}
          placeholder="Enter search term"
          required
        />
        <button type="submit">Search</button>
      </form>

      {/* Inline filter fields with icons */}
      <div className="filter-fields">
        <div className="filter-group">
          <FaCalendarAlt className="icon" />
          <label htmlFor="from-date"></label>
          <input type="date" id="from-date" value={fromDate} onChange={handleFromDateChange} />
        </div>

        <div className="filter-group">
          <FaCalendarAlt className="icon" />
          <label htmlFor="to-date"></label>
          <input type="date" id="to-date" value={toDate} onChange={handleToDateChange} />
        </div>

        <div className="filter-group">
          <FaCity className="icon" />
          <label htmlFor="city">City:</label>
          <input
            type="text"
            id="city"
            value={filters.city}
            onChange={handleCityChange}
            placeholder="Enter city"
          />
        </div>

        <div className="filter-group">
          <FaGlobeAmericas className="icon" />
          <label htmlFor="country">Country:</label>
          <input
            type="text"
            id="country"
            value={filters.country}
            onChange={handleCountryChange}
            placeholder="Enter country"
          />
        </div>
      </div>

      {/* Display message if available */}
      {message && <p className="message">{message}</p>}

      {/* Display search results if available */}
      {searchResults.length > 0 && (
        <div>
          <h3>Results (JSON format)</h3>
          <pre>{JSON.stringify(searchResults, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default Search;
