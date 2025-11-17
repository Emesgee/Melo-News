// src/pages/Home.js
import React, { useState } from 'react';
import MapArea from '../components/letleaf_map/MapArea';
import Sidebar from '../components/navigation_bars/Sidebar';
import Search from '../components/search_bar/Search';
import { dedupeStories } from '../utils/storyUtils';

import './Home.css';

const Home = ({ searchResults = [], onSearchResult = null }) => {
  const [isSidebarVisible, setIsSidebarVisible] = useState(false);
  const [localSearchResults, setLocalSearchResults] = useState([]);
  
  // CRITICAL: Topbar results ALWAYS take priority
  const results = (searchResults && searchResults.length > 0) ? searchResults : localSearchResults;
  
  const handleSearchResult = (newResults) => {
    const cleanedResults = dedupeStories(Array.isArray(newResults) ? newResults : []);
    // IMPORTANT: Don't update local state if topbar has results
    // This prevents the floating search from overwriting topbar results
    if (!searchResults || searchResults.length === 0) {
      setLocalSearchResults(cleanedResults);
    }
  };

  const toggleSidebar = () => {
    setIsSidebarVisible((prev) => !prev);
  };

  return (
    <div className="home">
      <Sidebar isSidebarVisible={isSidebarVisible} toggleSidebar={toggleSidebar} />

      <div className="map-wrapper">
        <MapArea searchResults={results} />

        {/* Floating Search Bar */}
        <div className="floating-search">
          <Search onSearchResult={handleSearchResult} />
        </div>
      </div>
    </div>
  );
};

export default Home;
