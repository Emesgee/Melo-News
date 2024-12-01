// src/components/Sidebar.js
import React from 'react';
import { Link} from 'react-router-dom';
import './Sidebar.css';

const Sidebar = ({ isSidebarVisible, toggleSidebar }) => {
 

  return (
    <>
      {/* Background overlay, visible only when the sidebar is open */}
      {isSidebarVisible && <div className="overlay" onClick={toggleSidebar}></div>}

      {/* Sidebar with a burger icon to close it */}
      <nav className={`sidebar ${isSidebarVisible ? 'active' : ''}`}>
        <button className="burger-menu" onClick={toggleSidebar} aria-label="Toggle sidebar">
          ☰ {/* Burger icon */}
        </button>
        <ul>
          <p>___________________</p>
          <li><Link to="/" onClick={toggleSidebar}>Home</Link></li>
          <li><Link to="/profile" onClick={toggleSidebar}>Profile</Link></li>
        </ul>
      </nav>

    </>
  );
};

export default Sidebar;
