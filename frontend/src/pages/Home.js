// src/pages/Home.js
import React, { useState } from 'react';
import MapArea from '../components/letleaf_map/MapArea'; // Ensure path is correct
import Sidebar from '../components/navigation_bars/Sidebar'; // Ensure path is correct
import Search from '../components/search_bar/Search'; // Ensure path is correct
import TopInfoBar from '../components/navigation_bars/TopInfoBar'; // Ensure path is correct


import './Home.css';

const Home = () => {
  const [isSidebarVisible, setIsSidebarVisible] = useState(false);

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
    <div className='search-container'>
      <Search />
    </div>
      {/* Main content of the Home page */}
      <h1> </h1>
      {/* Add other content here */}
      <div className='map-container'>
      <MapArea />
    </div>
    </div>
    
  );
};

export default Home;
