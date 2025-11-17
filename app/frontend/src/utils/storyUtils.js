const normaliseValue = (value) => {
  if (value === null || value === undefined) return null;
  const stringValue = String(value).trim();
  return stringValue.length > 0 ? stringValue : null;
};

const normaliseCoordinate = (value) => {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue.toFixed(5) : null;
};

export const resolveStoryId = (story = {}) => (
  story.id ??
  story.story_id ??
  story.storyId ??
  story.news_id ??
  story.document_id ??
  story.uuid ??
  story._id ??
  null
);

const buildFallbackKey = (story = {}) => {
  const referenceFields = [
    story.external_id,
    story.externalId,
    story.reference_id,
    story.url,
    story.source_url,
    story.article_url,
    story.link,
  ]
    .map(normaliseValue)
    .filter(Boolean);

  if (referenceFields.length > 0) {
    return `ref:${referenceFields[0]}`.toLowerCase();
  }

  const lat = normaliseCoordinate(
    story.lat ?? story.latitude ?? story.result_lat ?? story.lat_result
  );
  const lon = normaliseCoordinate(
    story.lon ?? story.longitude ?? story.result_lon ?? story.lon_result
  );

  if (lat !== null && lon !== null) {
    const title = normaliseValue(
      story.title ?? story.headline ?? story.message ?? story.description
    ) || '';
    const published = normaliseValue(
      story.published_at ?? story.date ?? story.created_at ?? story.timestamp
    ) || '';
    return `geo:${lat}:${lon}:${title.toLowerCase()}:${published.toLowerCase()}`;
  }

  const titleOnly = normaliseValue(
    story.title ?? story.headline ?? story.message ?? story.description
  );
  if (titleOnly) {
    return `title:${titleOnly.toLowerCase()}`;
  }

  return null;
};

export const dedupeStories = (stories = []) => {
  const seenKeys = new Set();
  const uniqueStories = [];

  stories.forEach((story) => {
    if (!story) return;

    const resolvedId = resolveStoryId(story);
    const key = resolvedId !== null && resolvedId !== undefined
      ? `id:${String(resolvedId).trim().toLowerCase()}`
      : buildFallbackKey(story) ?? `index:${uniqueStories.length}`;

    if (seenKeys.has(key)) return;
    seenKeys.add(key);
    uniqueStories.push(story);
  });

  return uniqueStories;
};
