import React, { useState, useMemo, useCallback } from 'react';
import axios from 'axios';
import './MeloSummary.css';
import { resolveStoryId } from '../../utils/storyUtils';

const MeloSummary = ({ searchResults = [] }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'visible' | 'search'
  const [visibleStories, setVisibleStories] = useState([]);

  const searchStoryIds = useMemo(() => {
    if (!Array.isArray(searchResults)) return [];
    const ids = searchResults
      .map(resolveStoryId)
      .filter((value) => value !== null && value !== undefined);
    return Array.from(new Set(ids));
  }, [searchResults]);

  const activeFilterLabel = useMemo(() => {
    switch (filterMode) {
      case 'visible':
        return `Visible Stories (${visibleStories.length})`;
      case 'search':
        return `Search Results (${searchStoryIds.length})`;
      case 'all':
      default:
        return 'All Stories';
    }
  }, [filterMode, visibleStories.length, searchStoryIds.length]);

  const fetchMetadata = useCallback(async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/summary-metadata');
      setMetadata(response.data);
    } catch (err) {
      console.error('Error fetching metadata:', err);
    }
  }, []);

  const generateSummary = async () => {
    setLoading(true);
    setError(null);

    if (filterMode === 'search' && searchStoryIds.length === 0) {
      setError('Search results do not include story identifiers. Try "All Stories" instead.');
      setLoading(false);
      return;
    }

    try {
      const payload = {};
      
      // If visible stories filter is enabled and we have visible stories
      if (filterMode === 'visible') {
        const resolvedVisibleStoryIds = visibleStories
          .map(resolveStoryId)
          .filter((value) => value !== null && value !== undefined);

        if (resolvedVisibleStoryIds.length === 0) {
          setError('Visible stories do not include identifiers. Try "All Stories" instead.');
          setLoading(false);
          return;
        }

        console.log(`Generating summary from ${resolvedVisibleStoryIds.length} visible stories`);
        payload.story_ids = resolvedVisibleStoryIds;
      } else if (filterMode === 'search') {
        console.log(`Generating summary from ${searchStoryIds.length} searched stories`);
        payload.story_ids = searchStoryIds;
      } else {
        console.log('Generating summary from all stories');
        // filterMode === 'all' will fetch all stories from backend
      }

      const response = await axios.post('http://localhost:8000/api/generate-melo-summary', payload);
      if (response.data.status === 'success') {
        setSummary(response.data);
      } else {
        setError('Failed to generate summary');
      }
    } catch (err) {
      console.error('Error generating summary:', err);
      setError(err.response?.data?.message || 'Error generating summary. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  const openModal = useCallback((visibleStoriesData = []) => {
    setVisibleStories(visibleStoriesData);
    setFilterMode((currentMode) => {
      const hasVisible = visibleStoriesData.length > 0;
      const hasSearch = searchStoryIds.length > 0;

      if (currentMode === 'search' && !hasSearch) {
        return hasVisible ? 'visible' : 'all';
      }

      if (currentMode === 'visible' && !hasVisible) {
        return hasSearch ? 'search' : 'all';
      }

      if (currentMode === 'all') {
        if (hasVisible) return 'visible';
        if (hasSearch) return 'search';
        return 'all';
      }

      return currentMode;
    });

    fetchMetadata();
    setIsOpen(true);
  }, [fetchMetadata, searchStoryIds.length]);

  const closeModal = () => {
    setIsOpen(false);
  };

  const downloadPDF = () => {
    if (!summary) return;

    const printWindow = window.open('', '_blank');
    
    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Melo News Summary</title>
          <style>
            body {
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
              max-width: 900px;
              margin: 0 auto;
              padding: 40px;
              background: white;
              color: #333;
              line-height: 1.6;
            }
            header {
              border-bottom: 3px solid #2c3e50;
              padding-bottom: 20px;
              margin-bottom: 30px;
            }
            .logo {
              font-size: 28px;
              font-weight: bold;
              color: #e74c3c;
              margin-bottom: 10px;
            }
            .date {
              color: #7f8c8d;
              font-size: 14px;
            }
            .metadata {
              background: #ecf0f1;
              padding: 15px;
              margin: 20px 0;
              border-left: 4px solid #3498db;
              font-size: 14px;
            }
            .summary-content {
              white-space: pre-wrap;
              word-wrap: break-word;
              font-size: 14px;
              line-height: 1.8;
            }
            footer {
              margin-top: 40px;
              padding-top: 20px;
              border-top: 1px solid #ecf0f1;
              text-align: center;
              color: #95a5a6;
              font-size: 12px;
            }
            @media print {
              body { margin: 0; padding: 20px; }
              header { page-break-after: avoid; }
            }
          </style>
        </head>
        <body>
          <header>
            <div class="logo">📰 Melo News</div>
            <div class="date">${new Date().toLocaleDateString('en-US', { 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric' 
            })}</div>
          </header>
          
          <div class="metadata">
            <strong>Summary Report</strong><br/>
            Stories Analyzed: ${summary.stories_count}<br/>
            Service: ${summary.service}<br/>
            Filter: ${activeFilterLabel}<br/>
            Generated: ${new Date(summary.generated_at).toLocaleString()}
          </div>
          
          <div class="summary-content">
${summary.summary}
          </div>
          
          <footer>
            <p>This report was automatically generated by Melo News Intelligence Platform</p>
          </footer>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
    
    printWindow.print();
  };

  const downloadHTML = () => {
    if (!summary) return;

    const htmlContent = `<!DOCTYPE html>
<html>
  <head>
    <title>Melo News Summary</title>
    <style>
      body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        max-width: 900px;
        margin: 0 auto;
        padding: 40px;
        background: white;
        color: #333;
      }
      header { border-bottom: 3px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; }
      .logo { font-size: 28px; font-weight: bold; color: #e74c3c; }
      .metadata { background: #ecf0f1; padding: 15px; margin: 20px 0; border-left: 4px solid #3498db; }
      .summary-content { white-space: pre-wrap; line-height: 1.8; }
      footer { margin-top: 40px; text-align: center; color: #95a5a6; }
    </style>
  </head>
  <body>
    <header>
      <div class="logo">📰 Melo News</div>
      <div>${new Date().toLocaleDateString()}</div>
    </header>
    <div class="metadata">
      <strong>Summary Report</strong><br/>
      Stories: ${summary.stories_count}<br/>
      Service: ${summary.service}<br/>
      Filter: ${activeFilterLabel}
    </div>
    <div class="summary-content">${summary.summary}</div>
    <footer><p>Generated by Melo News Intelligence Platform</p></footer>
  </body>
</html>`;

    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/html;charset=utf-8,' + encodeURIComponent(htmlContent));
    element.setAttribute('download', `melo-summary-${new Date().toISOString().split('T')[0]}.html`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const downloadTXT = () => {
    if (!summary) return;

    const textContent = `MELO NEWS SUMMARY
Generated: ${new Date().toLocaleString()}
Filter: ${activeFilterLabel}
Stories Analyzed: ${summary.stories_count}
Service: ${summary.service}

${'='.repeat(80)}

${summary.summary}

${'='.repeat(80)}
Generated by Melo News Intelligence Platform`;

    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(textContent));
    element.setAttribute('download', `melo-summary-${new Date().toISOString().split('T')[0]}.txt`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  // Export the openModal function so MapArea can call it
  React.useLayoutEffect(() => {
    window.openMeloSummary = openModal;
    return () => {
      delete window.openMeloSummary;
    };
  }, [openModal]);

  return (
    <>
      <button 
        className="melo-summary-btn" 
        onClick={() => openModal(visibleStories)}
        title="Generate AI-powered news summary"
      >
        📄 Generate Melo Summary
      </button>

      {isOpen && (
        <div className="melo-summary-modal-overlay" onClick={closeModal}>
          <div className="melo-summary-modal" onClick={(e) => e.stopPropagation()}>
            <div className="melo-summary-modal-header">
              <h2>📰 Melo News Summary</h2>
              <button className="close-btn" onClick={closeModal}>✕</button>
            </div>

            <div className="melo-summary-modal-body">
              {!summary ? (
                <>
                  <div className="intro-section">
                    <p>Generate a professional, journalist-style news summary from stories on the map.</p>
                    
                    {/* Filter Options */}
                    <div className="filter-options">
                      <label>
                        <input 
                          type="radio" 
                          value="all" 
                          checked={filterMode === 'all'}
                          onChange={(e) => setFilterMode(e.target.value)}
                        />
                        All Stories (Latest 50)
                      </label>
                      <label>
                        <input 
                          type="radio" 
                          value="visible" 
                          checked={filterMode === 'visible'}
                          onChange={(e) => setFilterMode(e.target.value)}
                          disabled={visibleStories.length === 0}
                        />
                        Visible on Map ({visibleStories.length} stories)
                      </label>
                      <label>
                        <input 
                          type="radio" 
                          value="search" 
                          checked={filterMode === 'search'}
                          onChange={(e) => setFilterMode(e.target.value)}
                          disabled={searchStoryIds.length === 0}
                        />
                        Search Results ({searchStoryIds.length} stories)
                      </label>
                    </div>

                    {metadata && (
                      <div className="metadata-info">
                        <p><strong>📊 Available Data:</strong></p>
                        <ul>
                          <li>{metadata.total_stories} total stories</li>
                          <li>{metadata.unique_cities} unique locations</li>
                          {searchStoryIds.length > 0 && (
                            <li>{searchStoryIds.length} stories in current search</li>
                          )}
                          {metadata.latest_story_date && (
                            <li>Latest: {new Date(metadata.latest_story_date).toLocaleDateString()}</li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>

                  {error && (
                    <div className="error-message">
                      ⚠️ {error}
                    </div>
                  )}

                  <button 
                    className="generate-btn"
                    onClick={generateSummary}
                    disabled={loading}
                  >
                    {loading ? '⏳ Generating...' : '✨ Generate Summary'}
                  </button>
                </>
              ) : (
                <>
                  <div className="summary-header">
                    <p className="summary-meta">
                      ✓ Generated from {summary.stories_count} stories via {summary.service} ({activeFilterLabel})
                    </p>
                  </div>

                  <div className="summary-content">
                    {summary.summary}
                  </div>

                  <div className="action-buttons">
                    <button className="action-btn download-html" onClick={downloadHTML}>
                      📄 Download HTML
                    </button>
                    <button className="action-btn download-txt" onClick={downloadTXT}>
                      📝 Download Text
                    </button>
                    <button className="action-btn download-pdf" onClick={downloadPDF}>
                      🖨️ Print/PDF
                    </button>
                    <button className="action-btn regenerate" onClick={() => setSummary(null)}>
                      🔄 Generate New
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default MeloSummary;
