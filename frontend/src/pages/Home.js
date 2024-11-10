// src/pages/Home.js
import React, { useState } from 'react';
import MapArea from '../components/letleaf_map/MapArea'; // Ensure path is correct
import Sidebar from '../components/navigation_bars/Sidebar'; // Ensure path is correct
import Search from '../components/search_bar/Search'; // Ensure path is correct
import TopInfoBar from '../components/navigation_bars/TopInfoBar'; // Ensure path is correct
import SubTopInfoBar from '../components/navigation_bars/SubTopInfoBar'; // Ensure path is correct
import InfoBottomBar from '../components/navigation_bars/InfoBottomBar';
import './Home.css';

const Home = () => {
  const [isSidebarVisible, setIsSidebarVisible] = useState(false);
  const [searchResults, setSearchResults] = useState([]); // State to hold search results

  // Function to toggle sidebar visibility
  const toggleSidebar = () => {
    setIsSidebarVisible((prev) => !prev);
  };

  return (
    <div className="home">
      {/* Sidebar component, with the toggleSidebar function passed as a prop */}
      <Sidebar isSidebarVisible={isSidebarVisible} toggleSidebar={toggleSidebar} />

      <div className='top-info'>
        <TopInfoBar />
      </div>

      <div className='sup-top-info'>
        <SubTopInfoBar />
      </div>

      <div className='search-container'>
        {/* Pass setSearchResults to Search to update search results */}
        <Search onSearchResult={setSearchResults} />
      </div>

      <div className='map-container'>
        {/* Pass searchResults to MapArea to display markers */}
        <MapArea searchResults={searchResults} />
      </div>

      <div className='bottom-info'>
        <InfoBottomBar />
        <h1>Test</h1>
      </div>
    </div>
  );
};

export default Home;
