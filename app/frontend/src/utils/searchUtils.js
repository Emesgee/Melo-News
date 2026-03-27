export const DEFAULT_TAGS = [
  { key: 'default-politics', name: 'Politics', icon: '🏛️', color: '#2563eb', searchTerm: 'politics', category: 'Topics', score: 0 },
  { key: 'default-technology', name: 'Technology', icon: '💻', color: '#7c3aed', searchTerm: 'technology', category: 'Topics', score: 0 },
  { key: 'default-sports', name: 'Sports', icon: '⚽', color: '#dc2626', searchTerm: 'sports', category: 'Topics', score: 0 },
  { key: 'default-weather', name: 'Weather', icon: '🌦️', color: '#0891b2', searchTerm: 'weather', category: 'Topics', score: 0 },
  { key: 'default-health', name: 'Health', icon: '⚕️', color: '#059669', searchTerm: 'health', category: 'Topics', score: 0 },
];

const TAG_STYLE_MAP = {
  search: { icon: '🔍', color: '#2563eb', category: 'Topics' },
  content: { icon: '🧠', color: '#7c3aed', category: 'Topics' },
  location: { icon: '📍', color: '#dc2626', category: 'Locations' },
  media: { icon: '🎥', color: '#0891b2', category: 'Media Types' },
  event: { icon: '🗓️', color: '#059669', category: 'Events' },
  topic: { icon: '📰', color: '#f97316', category: 'Topics' },
  default: { icon: '🏷️', color: '#6b7280', category: 'Other' },
};

export const CATEGORY_ICONS = {
  Topics: '📌',
  Locations: '📍',
  'Media Types': '🎥',
  Events: '🗓️',
  Other: '🏷️',
};

export const CATEGORY_ORDER = ['Topics', 'Locations', 'Media Types', 'Events', 'Other'];

const toTitleCase = (value = '') => value
  .toLowerCase()
  .split(/\s+/)
  .filter(Boolean)
  .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
  .join(' ');

const normaliseTagToken = (token = '') => token
  .replace(/[_-]/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

const extractRawTags = (result) => {
  const rawTags = new Set();
  const candidateFields = [
    result?.tags,
    result?.tag_list,
    result?.generated_tags,
    result?.auto_tags,
    result?.news_tags,
    result?.metadata?.tags,
  ];

  candidateFields.forEach((field) => {
    if (!field) return;
    if (Array.isArray(field)) {
      field.forEach((item) => {
        if (typeof item === 'string') rawTags.add(item);
      });
    } else if (typeof field === 'string') {
      field.split(/[|,]/).forEach((item) => {
        const token = item.trim();
        if (token) rawTags.add(token);
      });
    }
  });

  if (result?.city) rawTags.add(`location:${result.city}`);
  if (result?.country) rawTags.add(`location:${result.country}`);
  if (result?.media_type) rawTags.add(`media:${result.media_type}`);
  if (result?.category) rawTags.add(`topic:${result.category}`);

  return Array.from(rawTags);
};

const deriveTagObject = (tagString, score = 1) => {
  if (!tagString) return null;
  const [prefixRaw, remainderRaw] = tagString.includes(':') ? tagString.split(':', 2) : ['search', tagString];
  const prefix = prefixRaw.toLowerCase().trim() || 'search';
  const token = normaliseTagToken(remainderRaw || prefixRaw);
  if (!token) return null;

  const style = TAG_STYLE_MAP[prefix] || TAG_STYLE_MAP.default;
  const displayName = toTitleCase(token);
  const sanitisedToken = token.replace(/\s+/g, '-').toLowerCase();

  return {
    key: `${prefix}-${sanitisedToken}`,
    name: displayName,
    icon: style.icon,
    color: style.color,
    searchTerm: token,
    prefix,
    score,
    category: style.category || 'Other',
  };
};

export const buildSuggestedTags = (results = [], { fallbackTerm } = {}) => {
  const counts = new Map();

  results.forEach((result) => {
    extractRawTags(result).forEach((tag) => {
      const normalised = tag.trim().toLowerCase();
      if (!normalised) return;
      counts.set(normalised, (counts.get(normalised) || 0) + 1);
    });
  });

  if (fallbackTerm && fallbackTerm !== '*') {
    const fallbackTag = `search:${fallbackTerm}`;
    counts.set(fallbackTag, Math.max(counts.get(fallbackTag) || 0, results.length || 1));
  }

  const seenKeys = new Set();
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([tag, score]) => deriveTagObject(tag, score))
    .filter(Boolean)
    .filter((tagObj) => {
      if (seenKeys.has(tagObj.key)) return false;
      seenKeys.add(tagObj.key);
      return true;
    })
    .slice(0, 8);
};

/**
 * Group tags by category, sorted in a consistent priority order.
 */
export const groupTagsByCategory = (tags) => {
  const groups = {};
  tags.forEach((tag) => {
    const category = tag.category || 'Other';
    if (!groups[category]) groups[category] = [];
    groups[category].push(tag);
  });

  const sorted = {};
  CATEGORY_ORDER.forEach((cat) => {
    if (groups[cat]?.length > 0) sorted[cat] = groups[cat];
  });
  Object.keys(groups).forEach((cat) => {
    if (!sorted[cat] && groups[cat]?.length > 0) sorted[cat] = groups[cat];
  });

  return sorted;
};
