/**
 * Parse a media-links field that may be an array, JSON string, or pipe-separated string.
 */
export const parseMediaLinks = (field) => {
  if (!field) return [];
  if (Array.isArray(field)) return field.filter(Boolean).map(link => String(link).trim());
  if (typeof field === 'string') {
    try {
      const parsed = JSON.parse(field);
      if (Array.isArray(parsed)) return parsed.filter(Boolean).map(link => String(link).trim());
    } catch {
      /* not JSON — treat as pipe-separated */
    }
    return field.split('|').filter(Boolean).map(link => link.trim());
  }
  return [];
};

/**
 * Construct a proper URL from a filename or incomplete URL
 * Handles Azure Blob Storage URLs and local API endpoints
 */
export const normalizeMediaUrl = (url) => {
  if (!url) return null;
  
  const urlStr = String(url).trim();
  const urlLower = urlStr.toLowerCase();
  
  // Already a full URL (http, https, or blob.core.windows.net)
  if (urlLower.startsWith('http://') || urlLower.startsWith('https://') || urlLower.includes('blob.core.windows.net')) {
    return urlStr;
  }
  
  // Just a filename (no slashes and has an extension)
  if (!urlStr.includes('/') && /\.\w{2,4}$/.test(urlStr)) {
    // Return a URL that the backend can serve
    // This assumes the backend has a file_download or download endpoint
    return `/api/file_upload/download/${encodeURIComponent(urlStr)}`;
  }
  
  // Already has path structure, ensure it starts with /api or is absolute
  if (urlLower.startsWith('/')) {
    return urlStr;
  }
  
  // Relative path without leading slash
  if (!urlLower.startsWith('/api')) {
    return `/api/${urlStr}`;
  }
  
  return urlStr;
};

const VIDEO_EXT_RE = /\.(mp4|webm|ogg|mov|avi)$/i;
const IMAGE_EXT_RE = /\.(jpg|jpeg|png|gif|bmp|webp)$/i;

/**
 * Filter URLs that point to video files.
 */
export const filterVideoFiles = (urls = []) =>
  urls.filter(url => {
    if (!url) return false;
    const s = String(url).toLowerCase();
    return VIDEO_EXT_RE.test(s) || s.includes('blob.core.windows.net') || s.includes('video');
  });

/**
 * Filter URLs that point to image files (excluding videos).
 */
export const filterImageFiles = (urls = [], videoUrls = []) => {
  const videoSet = new Set(videoUrls);
  return urls.filter(url => {
    if (!url) return false;
    return IMAGE_EXT_RE.test(String(url).toLowerCase()) && !videoSet.has(url);
  });
};

/**
 * Resolve all media files (images + videos, deduplicated) from a result object.
 */
export const resolveMediaFiles = (result) => {
  const imageLinks = parseMediaLinks(result.image_links || result.fileUrl);
  const videoLinks = parseMediaLinks(result.video_links || result.videoUrl);
  return Array.from(new Set([...imageLinks, ...videoLinks])).filter(Boolean);
};

/**
 * Format a date string or timestamp into a human-readable locale string.
 * Returns 'Recent' if parsing fails or no value is given.
 */
export const formatNewsTime = (raw) => {
  if (!raw) return 'Recent';
  try {
    const d = new Date(raw);
    if (!isNaN(d.getTime())) {
      return d.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    }
  } catch {
    /* invalid date */
  }
  return 'Recent';
};

/**
 * Compute a relative time string (e.g. "5m", "2h", "3d") from a date string.
 */
export const getRelativeTime = (dateStr) => {
  if (!dateStr) return '';
  const now = new Date();
  const date = new Date(dateStr);
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
};
