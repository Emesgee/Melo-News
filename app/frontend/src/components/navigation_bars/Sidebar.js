// src/components/Sidebar.js
import React from 'react';
import { Link} from 'react-router-dom';
import './Sidebar.css';

const Sidebar = ({ isSidebarVisible, toggleSidebar, mapLayers, selectedLayer, onMapLayerChange }) => {


  return (
    <>
      {/* Background overlay */}
      <div className={`sidebar-overlay ${isSidebarVisible ? 'active' : ''}`} onClick={toggleSidebar}></div>

      {/* Sidebar */}
      <nav className={`sidebar ${isSidebarVisible ? 'active' : ''}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">M</div>
            <div>
              <h2 className="sidebar-title">Melo News</h2>
              <p className="sidebar-subtitle">Real-time News Mapping</p>
            </div>
          </div>
        </div>

        {/* Navigation Menu */}
        <ul className="sidebar-nav">
          <li className="sidebar-nav-item">
            <Link to="/" className="sidebar-nav-link" onClick={toggleSidebar}>
              <span className="nav-icon">🏠</span>
              <span className="nav-text">Home</span>
            </Link>
          </li>
          <li className="sidebar-nav-item">
            <Link to="/profile" className="sidebar-nav-link" onClick={toggleSidebar}>
              <span className="nav-icon">👤</span>
              <span className="nav-text">Profile</span>
            </Link>
          </li>
          <li className="sidebar-nav-item">
            <Link to="/search" className="sidebar-nav-link" onClick={toggleSidebar}>
              <span className="nav-icon">🔍</span>
              <span className="nav-text">Search</span>
            </Link>
          </li>
          {/* Map Layer Selector */}
          {mapLayers && mapLayers.length > 0 && (
            <li className="sidebar-nav-item map-layer-selector">
              <label className="map-layer-label">
                <span className="nav-icon">🗺️</span>
                <span className="nav-text">Map Style</span>
              </label>
              <select
                value={selectedLayer?.name || ''}
                onChange={(e) => onMapLayerChange?.(e.target.value)}
                className="map-layer-select"
              >
                {mapLayers.map(layer => (
                  <option key={layer.name} value={layer.name}>{layer.name}</option>
                ))}
              </select>
            </li>
          )}
        </ul>

        {/* User Section */}
        <div className="sidebar-user">
          <div className="user-profile">
            <div className="user-avatar">U</div>
            <div className="user-info">
              <h4>User</h4>
              <p>user@example.com</p>
            </div>
          </div>
          <div className="user-actions">
            <button className="user-action-btn primary">Settings</button>
            <button className="user-action-btn secondary">Help</button>
          </div>
        </div>
      </nav>

    </>
  );
};

export default Sidebar;
