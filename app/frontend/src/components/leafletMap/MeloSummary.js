import React, { useState, useMemo, useCallback } from 'react';
import { api } from '../../services/api';
import './MeloSummary.css';
import { resolveStoryId } from '../../utils/storyUtils';
import { useSearch } from '../../utils/SearchContext';

const MeloSummary = ({ onClose, initialOpen = false }) => {
  const { searchResults } = useSearch();
  const [isOpen, setIsOpen] = useState(initialOpen);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [filterMode, setFilterMode] = useState('all');
  const [visibleStories, setVisibleStories] = useState([]);
  const [mediaModal, setMediaModal] = useState({ isOpen: false, url: '', type: '' }); // New state for media modal

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
      const response = await api.get('/api/summary-metadata');
      setMetadata(response.data);
    } catch (err) {
      /* metadata fetch failed */
    }
  }, []);

  // Open media viewer modal
  const openMediaViewer = (url, type) => {
    setMediaModal({ isOpen: true, url, type });
  };

  // Close media viewer modal
  const closeMediaViewer = () => {
    setMediaModal({ isOpen: false, url: '', type: '' });
  };

  /**
   * Parse summary text into an array of React-safe segments.
   * Replaces dangerouslySetInnerHTML with safe React elements.
   */
  const renderSummaryContent = useCallback((text) => {
    if (!text) return null;

    // Split on markdown media links, bold, and newlines
    const MEDIA_RE = /\[(Video|Image)\]\((https?:\/\/[^)]+)\)/g;
    const segments = [];
    let lastIndex = 0;
    let match;

    while ((match = MEDIA_RE.exec(text)) !== null) {
      // Text before this match
      if (match.index > lastIndex) {
        segments.push({ type: 'text', value: text.slice(lastIndex, match.index) });
      }
      segments.push({ type: match[1].toLowerCase(), url: match[2] });
      lastIndex = MEDIA_RE.lastIndex;
    }
    if (lastIndex < text.length) {
      segments.push({ type: 'text', value: text.slice(lastIndex) });
    }

    // Render segments as React elements
    return segments.map((seg, i) => {
      if (seg.type === 'video') {
        return (
          <button key={i} className="media-link video-link" onClick={() => openMediaViewer(seg.url, 'video')}>
            📹 Video
          </button>
        );
      }
      if (seg.type === 'image') {
        return (
          <button key={i} className="media-link image-link" onClick={() => openMediaViewer(seg.url, 'image')}>
            🖼️ Image
          </button>
        );
      }
      // Render text with bold + newlines (safe — no innerHTML)
      return (
        <React.Fragment key={i}>
          {seg.value.split('\n').map((line, li, arr) => {
            // Handle **bold** within each line
            const parts = line.split(/(\*\*[^*]+\*\*)/).map((part, pi) => {
              if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={pi}>{part.slice(2, -2)}</strong>;
              }
              return part;
            });
            return (
              <React.Fragment key={li}>
                {parts}
                {li < arr.length - 1 && <br />}
              </React.Fragment>
            );
          })}
        </React.Fragment>
      );
    });
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
      
      if (filterMode === 'visible') {
        const resolvedVisibleStoryIds = visibleStories
          .map(resolveStoryId)
          .filter((value) => value !== null && value !== undefined);

        if (resolvedVisibleStoryIds.length === 0) {
          setError('Visible stories do not include identifiers. Try "All Stories" instead.');
          setLoading(false);
          return;
        }

        payload.story_ids = resolvedVisibleStoryIds;
      } else if (filterMode === 'search') {
        payload.story_ids = searchStoryIds;
      } else {
      }

const response = await api.post('generate-melo-summary', payload);
      if (response.data.status === 'success') {
        setSummary(response.data);
      } else {
        setError('Failed to generate summary');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error generating summary.');
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
    if (onClose) {
      onClose();
    }
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
              word-wrap: break-word;
              font-size: 14px;
              line-height: 1.8;
            }
            .media-link {
              color: #3498db;
              text-decoration: none;
              font-weight: 500;
              padding: 2px 6px;
              border-radius: 3px;
              background: #ecf0f1;
            }
            .video-link {
              color: #e74c3c;
              background: rgba(231, 76, 60, 0.1);
            }
            .image-link {
              color: #9b59b6;
              background: rgba(155, 89, 182, 0.1);
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
            ${summary.summary.replace(/\[Video\]\([^)]+\)/g, '[Video Link]').replace(/\[Image\]\([^)]+\)/g, '[Image Link]')}
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
      .summary-content { line-height: 1.8; }
      .media-link {
        color: #3498db;
        text-decoration: none;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(52, 152, 219, 0.1);
      }
      .media-link:hover {
        background: #3498db;
        color: white;
      }
      .video-link {
        color: #e74c3c;
        background: rgba(231, 76, 60, 0.1);
      }
      .video-link:hover {
        background: #e74c3c;
      }
      .image-link {
        color: #9b59b6;
        background: rgba(155, 89, 182, 0.1);
      }
      .image-link:hover {
        background: #9b59b6;
      }
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
    <div class="summary-content">${summary.summary.replace(/\[Video\]\([^)]+\)/g, '[Video]').replace(/\[Image\]\([^)]+\)/g, '[Image]').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br/>')}</div>
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

    const plainText = summary.summary
      .replace(/<[^>]*>/g, '')
      .replace(/\[Video\]\([^)]+\)/g, '[Video]')
      .replace(/\[Image\]\([^)]+\)/g, '[Image]');

    const textContent = `MELO NEWS SUMMARY
Generated: ${new Date().toLocaleString()}
Filter: ${activeFilterLabel}
Stories Analyzed: ${summary.stories_count}
Service: ${summary.service}

${'='.repeat(80)}

${plainText}

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

  // openModal exposed via ref or parent callback — no window globals needed

  return (
    <>
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
                    {renderSummaryContent(summary.summary)}
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

      {/* Media Viewer Modal */}
      {mediaModal.isOpen && (
        <div className="media-modal-overlay" onClick={closeMediaViewer}>
          <div className="media-modal" onClick={(e) => e.stopPropagation()}>
            <div className="media-modal-header">
              <h3>{mediaModal.type === 'video' ? '📹 Video Player' : '🖼️ Image Viewer'}</h3>
              <button className="close-btn" onClick={closeMediaViewer}>✕</button>
            </div>
            <div className="media-modal-content">
              {mediaModal.type === 'video' ? (
                <video controls autoPlay style={{ width: '100%', maxHeight: '70vh' }}>
                  <source src={mediaModal.url} type="video/mp4" />
                  Your browser does not support the video tag.
                </video>
              ) : (
                <img 
                  src={mediaModal.url} 
                  alt="Media content" 
                  style={{ width: '100%', maxHeight: '70vh', objectFit: 'contain' }}
                />
              )}
            </div>
            <div className="media-modal-footer">
              <a 
                href={mediaModal.url} 
                download 
                className="download-media-btn"
                target="_blank"
                rel="noopener noreferrer"
              >
                ⬇️ Download {mediaModal.type === 'video' ? 'Video' : 'Image'}
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default MeloSummary;