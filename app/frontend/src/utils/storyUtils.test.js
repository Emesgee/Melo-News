import { dedupeStories, resolveStoryId } from './storyUtils';

describe('resolveStoryId', () => {
  it('returns id when present', () => {
    expect(resolveStoryId({ id: 1 })).toBe(1);
  });

  it('falls back to story_id', () => {
    expect(resolveStoryId({ story_id: 42 })).toBe(42);
  });

  it('returns null for empty object', () => {
    expect(resolveStoryId({})).toBeNull();
  });

  it('returns null for undefined', () => {
    expect(resolveStoryId()).toBeNull();
  });
});

describe('dedupeStories', () => {
  it('removes duplicate stories by id', () => {
    const stories = [
      { id: 1, title: 'First' },
      { id: 1, title: 'Duplicate' },
      { id: 2, title: 'Second' },
    ];
    const result = dedupeStories(stories);
    expect(result).toHaveLength(2);
    expect(result[0].title).toBe('First');
    expect(result[1].title).toBe('Second');
  });

  it('deduplicates by title fallback when no id', () => {
    const stories = [
      { title: 'Breaking news' },
      { title: 'Breaking news' },
      { title: 'Other news' },
    ];
    const result = dedupeStories(stories);
    expect(result).toHaveLength(2);
  });

  it('deduplicates by geo coordinates', () => {
    const stories = [
      { lat: 31.5, lon: 34.5, title: 'Gaza report' },
      { lat: 31.5, lon: 34.5, title: 'Gaza report' },
    ];
    const result = dedupeStories(stories);
    expect(result).toHaveLength(1);
  });

  it('returns empty array for empty input', () => {
    expect(dedupeStories([])).toEqual([]);
  });

  it('handles null/undefined entries gracefully', () => {
    const stories = [null, undefined, { id: 1, title: 'Valid' }];
    const result = dedupeStories(stories);
    expect(result).toHaveLength(1);
    expect(result[0].title).toBe('Valid');
  });

  it('handles default parameter', () => {
    expect(dedupeStories()).toEqual([]);
  });
});
