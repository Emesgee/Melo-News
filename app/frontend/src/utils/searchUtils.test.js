import { DEFAULT_TAGS, CATEGORY_ICONS, buildSuggestedTags, groupTagsByCategory } from './searchUtils';

describe('DEFAULT_TAGS', () => {
  it('contains expected default categories', () => {
    expect(DEFAULT_TAGS).toHaveLength(5);
    const names = DEFAULT_TAGS.map(t => t.name);
    expect(names).toContain('Politics');
    expect(names).toContain('Technology');
    expect(names).toContain('Sports');
  });

  it('each tag has required fields', () => {
    DEFAULT_TAGS.forEach(tag => {
      expect(tag).toHaveProperty('key');
      expect(tag).toHaveProperty('name');
      expect(tag).toHaveProperty('icon');
      expect(tag).toHaveProperty('color');
      expect(tag).toHaveProperty('searchTerm');
      expect(tag).toHaveProperty('category');
    });
  });
});

describe('CATEGORY_ICONS', () => {
  it('has icons for all standard categories', () => {
    expect(CATEGORY_ICONS).toHaveProperty('Topics');
    expect(CATEGORY_ICONS).toHaveProperty('Locations');
    expect(CATEGORY_ICONS).toHaveProperty('Other');
  });
});

describe('buildSuggestedTags', () => {
  it('returns empty array for empty results', () => {
    expect(buildSuggestedTags([])).toEqual([]);
  });

  it('extracts tags from result objects', () => {
    const results = [
      { tags: ['politics', 'breaking'], city: 'Gaza' },
      { tags: ['politics'], city: 'Gaza' },
    ];
    const tags = buildSuggestedTags(results);
    expect(tags.length).toBeGreaterThan(0);
    expect(tags.some(t => t.searchTerm === 'politics')).toBe(true);
  });

  it('handles pipe-separated tag strings', () => {
    const results = [{ tags: 'breaking|urgent|live' }];
    const tags = buildSuggestedTags(results);
    expect(tags.some(t => t.searchTerm === 'breaking')).toBe(true);
  });

  it('creates location tags from city/country', () => {
    const results = [{ city: 'Berlin', country: 'Germany' }];
    const tags = buildSuggestedTags(results);
    expect(tags.some(t => t.category === 'Locations')).toBe(true);
  });

  it('includes fallbackTerm as a search tag', () => {
    const tags = buildSuggestedTags([], { fallbackTerm: 'earthquake' });
    expect(tags).toHaveLength(1);
    expect(tags[0].searchTerm).toBe('earthquake');
  });

  it('does not include fallbackTerm when it is *', () => {
    const tags = buildSuggestedTags([], { fallbackTerm: '*' });
    expect(tags).toHaveLength(0);
  });

  it('limits output to 8 tags', () => {
    const results = Array.from({ length: 50 }, (_, i) => ({ tags: [`tag${i}`] }));
    const tags = buildSuggestedTags(results);
    expect(tags.length).toBeLessThanOrEqual(8);
  });

  it('deduplicates tags by key', () => {
    const results = [
      { tags: ['hello', 'hello', 'hello'] },
    ];
    const tags = buildSuggestedTags(results);
    const helloTags = tags.filter(t => t.searchTerm === 'hello');
    expect(helloTags).toHaveLength(1);
  });
});

describe('groupTagsByCategory', () => {
  it('groups tags by their category field', () => {
    const tags = [
      { name: 'A', category: 'Topics' },
      { name: 'B', category: 'Locations' },
      { name: 'C', category: 'Topics' },
    ];
    const grouped = groupTagsByCategory(tags);
    expect(grouped.Topics).toHaveLength(2);
    expect(grouped.Locations).toHaveLength(1);
  });

  it('returns empty object for empty input', () => {
    expect(groupTagsByCategory([])).toEqual({});
  });

  it('preserves category order (Topics first)', () => {
    const tags = [
      { name: 'L', category: 'Locations' },
      { name: 'T', category: 'Topics' },
    ];
    const grouped = groupTagsByCategory(tags);
    const keys = Object.keys(grouped);
    expect(keys[0]).toBe('Topics');
    expect(keys[1]).toBe('Locations');
  });

  it('handles tags with missing category', () => {
    const tags = [{ name: 'X' }];
    const grouped = groupTagsByCategory(tags);
    expect(grouped.Other).toHaveLength(1);
  });
});
