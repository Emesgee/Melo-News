import React from 'react';
import MapArea from '../components/letleaf_map/MapArea';
import './Home.css';

const Home = ({ searchResults = [] }) => {
  return (
    <div className="home">
      <MapArea searchResults={searchResults} />
    </div>
  );
};

export default Home;
