/**
 * Chunked resumable upload utility.
 *
 * Strategy:
 *  1. Split the file into CHUNK_SIZE pieces.
 *  2. POST each chunk to /api/file_upload/chunk with:
 *       - chunk (blob)
 *       - upload_id  (server-assigned token from first chunk response)
 *       - chunk_index
 *       - total_chunks
 *       - filename
 *  3. After all chunks, POST /api/file_upload/chunk-complete with metadata.
 *  4. On network failure, retry up to MAX_RETRIES with exponential back-off.
 *  5. Progress is reported via onProgress(pct 0-100).
 */

const CHUNK_SIZE = 2 * 1024 * 1024; // 2 MB per chunk
const MAX_RETRIES = 4;

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function postChunk(api, formData, retries = 0) {
  try {
    return await api.post('/file_upload/chunk', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    });
  } catch (err) {
    if (retries < MAX_RETRIES) {
      await sleep(500 * 2 ** retries); // 0.5s, 1s, 2s, 4s
      return postChunk(api, formData, retries + 1);
    }
    throw err;
  }
}

/**
 * @param {object}   api          - axios instance
 * @param {File}     file         - file to upload
 * @param {object}   metadata     - { file_type_id, title, tags, subject, city, country, lat, lon }
 * @param {Function} onProgress   - (pct: number) => void
 * @returns {Promise<object>}     - server response data from chunk-complete
 */
export async function chunkedUpload(api, file, metadata, onProgress) {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  let uploadId = null;

  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);

    const fd = new FormData();
    fd.append('chunk', chunk, file.name);
    fd.append('chunk_index', i);
    fd.append('total_chunks', totalChunks);
    fd.append('filename', file.name);
    fd.append('file_type', file.type || 'application/octet-stream');
    if (uploadId) fd.append('upload_id', uploadId);

    const res = await postChunk(api, fd);
    if (i === 0) uploadId = res.data.upload_id;

    onProgress(Math.round(((i + 1) / totalChunks) * 90)); // 0-90% for chunks
  }

  // Finalise — send metadata with the assembled file
  const completeRes = await api.post('/file_upload/chunk-complete', {
    upload_id: uploadId,
    filename: file.name,
    ...metadata,
  });

  onProgress(100);
  return completeRes.data;
}
