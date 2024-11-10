// src/pages/InfoSidebar.js
import React, { useEffect, useState, useRef } from 'react';
import './SubTopInfoBar.css';

const sources = {
  "Al Jazeera": {
    url: "https://www.aljazeera.com/xml/rss/all.xml",
    logo: "https://www.aljazeera.com/images/logo_aje.png"
  },
  "CNN": {
    url: "http://rss.cnn.com/rss/edition.rss",
    logo: "https://cdn.cnn.com/cnn/.e/img/3.0/global/misc/cnn-logo.png"
  },
  "Fox News": {
    url: "http://feeds.foxnews.com/foxnews/latest",
    logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Fox_News_Channel_logo.svg/1200px-Fox_News_Channel_logo.svg.png"
  },
  "BBC": {
    url: "http://feeds.bbci.co.uk/news/rss.xml",
    logo: "https://th.bing.com/th/id/OIP.iMV7ImB8dIRBJW1Snd5ORAHaHa?rs=1&pid=ImgDetMain"
  },
  
  "The Guardian": {
    url: "https://www.theguardian.com/uk/rss",
    logo: "https://brandlogos.net/wp-content/uploads/2022/07/the_guardian-logo_brandlogos.net_ybiy9.png"
  },
  "DR News": {
    url: "https://www.dr.dk/nyheder/service/feeds/allenyheder",
    logo: "https://yt3.ggpht.com/a/AGF-l7_5Qr4z4GfT9MBqaQ9xVH9_AaCeDYghI9FOeg=s900-c-k-c0xffffffff-no-rj-mo"
  }
};

const TopInfoBar = () => {
  const [selectedSource, setSelectedSource] = useState(null); // Track the selected source
  const [headlines, setHeadlines] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showHeadlines, setShowHeadlines] = useState(false);
  const [headline, setHeadline] = useState('Loading news...');
  const [link, setLink] = useState('#'); // Link to the current article
  const headlineRef = useRef(null); // Reference to the headline element


  const handleNavigateLeft = () => {
    setCurrentIndex((prevIndex) => (prevIndex === 0 ? headlines.length - 1 : prevIndex - 1));
  };

  const handleNavigateRight = () => {
    setCurrentIndex((prevIndex) => (prevIndex === headlines.length - 1 ? 0 : prevIndex + 1));
  };

  const handleLogoClick = (sourceName) => {
    setSelectedSource(sourceName);
    setShowHeadlines(true);
  };

  useEffect(() => {
    if (!selectedSource) return;

    const fetchRSS = async () => {
      const rssUrl = sources[selectedSource].url;
      try {
        const response = await fetch(`https://api.rss2json.com/v1/api.json?rss_url=${rssUrl}`);
        const data = await response.json();
        if (data.items && data.items.length > 0) {
          setHeadlines(data.items); // Store all headlines
          setHeadline(data.items[0].title); // Set the first headline as the initial value
          setLink(data.items[0].link); // Set the first headline link as the initial value
        }
      } catch (error) {
        console.error('Error fetching RSS feed:', error);
        setHeadline('Error loading news');
      }
    
    };

    fetchRSS();
  }, [selectedSource]); // Refetch headlines when a new source is selected

  useEffect(() => {
    if (headlines.length > 0) {
      setHeadline(headlines[currentIndex].title); // Update the headline based on the current index
      setLink(headlines[currentIndex].link); // Update the link based on the current index
  
      // Reset the scroll position of the headline to the beginning
      if (headlineRef.current) {
        headlineRef.current.scrollLeft = 0;
      }
    }
  }, [currentIndex, headlines]);

  return (
    <div className="top-infobar">
      {/* Logo selection row */}
      {!showHeadlines && (
        <div className="logo-row">
          {Object.keys(sources).map((source) => (
            <img
              key={source}
              src={sources[source].logo}
              alt={`${source} Logo`}
              className="source-logo"
              onClick={() => handleLogoClick(source)}
            />
          ))}
        </div>
      )}

      {/* Left Navigation Arrow (only show when headlines are displayed) */}
      {showHeadlines && (
        <button className="nav-arrow" onClick={handleNavigateLeft}>
          &#x25C0;
        </button>
      )}

      {/* Center Headline */}
      {showHeadlines ? (
        <a
        href={link}
        target="_blank"
        rel="noopener noreferrer"
        className="headline"
        ref={headlineRef} // Attach the ref to the headline element
        data-fulltext={headline}
      >
        {headline}
      </a>
      ) : null}

      {/* Right Navigation Arrow (only show when headlines are displayed) */}
      {showHeadlines && (
        <button className="nav-arrow" onClick={handleNavigateRight}>
          &#x25B6;
        </button>
      )}
    </div>
  );
};

export default TopInfoBar;
