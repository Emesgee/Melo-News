import {
  parseMediaLinks,
  filterVideoFiles,
  filterImageFiles,
  formatNewsTime,
  getRelativeTime,
} from './mediaUtils';

describe('parseMediaLinks', () => {
  it('returns empty array for null/undefined', () => {
    expect(parseMediaLinks(null)).toEqual([]);
    expect(parseMediaLinks(undefined)).toEqual([]);
    expect(parseMediaLinks('')).toEqual([]);
  });

  it('parses an array of URLs', () => {
    const input = ['https://a.com/img.jpg', 'https://b.com/vid.mp4'];
    expect(parseMediaLinks(input)).toEqual(input);
  });

  it('filters out falsy values from arrays', () => {
    expect(parseMediaLinks([null, '', 'https://a.com/x.jpg', undefined])).toEqual(['https://a.com/x.jpg']);
  });

  it('parses a JSON string array', () => {
    const json = '["https://a.com/1.jpg","https://b.com/2.png"]';
    expect(parseMediaLinks(json)).toEqual(['https://a.com/1.jpg', 'https://b.com/2.png']);
  });

  it('parses pipe-separated strings', () => {
    expect(parseMediaLinks('a.jpg|b.png|c.gif')).toEqual(['a.jpg', 'b.png', 'c.gif']);
  });

  it('trims whitespace from entries', () => {
    expect(parseMediaLinks([' a.jpg ', '  b.png'])).toEqual(['a.jpg', 'b.png']);
  });

  it('returns empty array for non-string non-array', () => {
    expect(parseMediaLinks(42)).toEqual([]);
    expect(parseMediaLinks({})).toEqual([]);
  });
});

describe('filterVideoFiles', () => {
  it('identifies video files by extension', () => {
    const urls = ['a.mp4', 'b.jpg', 'c.webm', 'd.png', 'e.ogg'];
    expect(filterVideoFiles(urls)).toEqual(['a.mp4', 'c.webm', 'e.ogg']);
  });

  it('identifies Azure blob video URLs', () => {
    const urls = ['https://storage.blob.core.windows.net/container/file'];
    expect(filterVideoFiles(urls)).toEqual(urls);
  });

  it('identifies URLs containing "video"', () => {
    expect(filterVideoFiles(['https://cdn.com/video/stream123'])).toHaveLength(1);
  });

  it('returns empty for no videos', () => {
    expect(filterVideoFiles(['a.jpg', 'b.png'])).toEqual([]);
  });

  it('handles empty/undefined input', () => {
    expect(filterVideoFiles([])).toEqual([]);
    expect(filterVideoFiles()).toEqual([]);
  });
});

describe('filterImageFiles', () => {
  it('identifies image files by extension', () => {
    const urls = ['a.jpg', 'b.mp4', 'c.png', 'd.webp'];
    expect(filterImageFiles(urls)).toEqual(['a.jpg', 'c.png', 'd.webp']);
  });

  it('excludes URLs that are also in the video set', () => {
    const urls = ['a.jpg', 'b.jpg'];
    const videoUrls = ['b.jpg'];
    expect(filterImageFiles(urls, videoUrls)).toEqual(['a.jpg']);
  });

  it('returns empty for no images', () => {
    expect(filterImageFiles(['a.mp4', 'b.mp3'])).toEqual([]);
  });
});

describe('formatNewsTime', () => {
  it('returns "Recent" for falsy input', () => {
    expect(formatNewsTime(null)).toBe('Recent');
    expect(formatNewsTime('')).toBe('Recent');
    expect(formatNewsTime(undefined)).toBe('Recent');
  });

  it('formats a valid ISO date string', () => {
    const result = formatNewsTime('2024-06-15T14:30:00Z');
    expect(result).toContain('Jun');
    expect(result).toContain('2024');
  });

  it('formats a timestamp number', () => {
    const result = formatNewsTime(1700000000000);
    expect(result).not.toBe('Recent');
  });

  it('returns "Recent" for invalid date', () => {
    expect(formatNewsTime('not-a-date')).toBe('Recent');
  });
});

describe('getRelativeTime', () => {
  it('returns empty string for falsy input', () => {
    expect(getRelativeTime('')).toBe('');
    expect(getRelativeTime(null)).toBe('');
  });

  it('returns seconds for very recent dates', () => {
    const now = new Date();
    const result = getRelativeTime(now.toISOString());
    expect(result).toMatch(/^\d+s$/);
  });

  it('returns minutes for dates within the hour', () => {
    const thirtyMinAgo = new Date(Date.now() - 30 * 60 * 1000);
    expect(getRelativeTime(thirtyMinAgo.toISOString())).toBe('30m');
  });

  it('returns hours for dates within the day', () => {
    const fiveHoursAgo = new Date(Date.now() - 5 * 60 * 60 * 1000);
    expect(getRelativeTime(fiveHoursAgo.toISOString())).toBe('5h');
  });

  it('returns days for older dates', () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000);
    expect(getRelativeTime(threeDaysAgo.toISOString())).toBe('3d');
  });
});
