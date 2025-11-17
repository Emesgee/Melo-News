# API Reference

## Overview

The Melo-News API provides RESTful endpoints for news story management, AI-powered features, and real-time data access. All endpoints return JSON responses and follow standard HTTP conventions.

## Base URL

```
Development: http://localhost:5000/api
Production: https://your-domain.com/api
```

## Authentication

Currently, the API uses environment variable-based authentication for AI services. Future versions may implement user authentication.

## File Upload API

### Upload File

```http
POST /api/file_upload/upload
```

**Headers:**
- `Authorization: Bearer <jwt_token>`
- `Content-Type: multipart/form-data`

**Form Data:**
- `file` (required) - The file to upload
- `file_type_id` (required) - File type identifier

**Response:**
```json
{
  "message": "File uploaded successfully",
  "file_id": 123,
  "file_path": "uploads/20241115_story_document.pdf",
  "azure_url": "https://storage.blob.core.windows.net/uploads/file.pdf",
  "processed_stories": [
    {
      "id": 456,
      "title": "Extracted Story Title",
      "description": "Automatically extracted content...",
      "city": "Gaza",
      "coordinates": [31.5017, 34.4668]
    }
  ]
}
```

### Get Upload History

```http
GET /api/file_upload/history
```

**Headers:**
- `Authorization: Bearer <jwt_token>`

**Response:**
```json
{
  "uploads": [
    {
      "id": 123,
      "filename": "news_report.pdf",
      "upload_date": "2024-01-15T14:30:00Z",
      "file_type": "Document",
      "processing_status": "completed",
      "stories_extracted": 3
    }
  ],
  "total": 15
}
```

## Stories API

### Get All Stories

```http
GET /api/stories
```

**Parameters:**
- `limit` (optional) - Maximum number of stories (default: 100)
- `offset` (optional) - Skip number of stories (default: 0)

**Response:**
```json
{
  "stories": [
    {
      "id": 1,
      "title": "Story Title",
      "description": "Story description...",
      "city": "Jerusalem",
      "country": "Palestine",
      "lat": 31.7683,
      "lng": 35.2137,
      "date_occurred": "2024-01-15T14:30:00Z",
      "source_url": "https://t.me/channel/123",
      "created_at": "2024-01-15T14:35:00Z"
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

### Get Story by ID

```http
GET /api/stories/:id
```

**Response:**
```json
{
  "id": 1,
  "title": "Story Title",
  "description": "Story description...",
  "city": "Jerusalem",
  "country": "Palestine", 
  "lat": 31.7683,
  "lng": 35.2137,
  "date_occurred": "2024-01-15T14:30:00Z",
  "source_url": "https://t.me/channel/123",
  "created_at": "2024-01-15T14:35:00Z"
}
```

### Create Story

```http
POST /api/stories
```

**Request Body:**
```json
{
  "title": "New Story Title",
  "description": "Story description...",
  "city": "Gaza", 
  "country": "Palestine",
  "lat": 31.5017,
  "lng": 34.4668,
  "date_occurred": "2024-01-15T14:30:00Z",
  "source_url": "https://source.com/story"
}
```

**Response:** `201 Created`
```json
{
  "id": 123,
  "message": "Story created successfully"
}
```

## Search API

### Search Stories

```http
GET /api/search
```

**Parameters:**
- `q` (required) - Search query
- `city` (optional) - Filter by city
- `country` (optional) - Filter by country
- `date_from` (optional) - Start date (ISO 8601)
- `date_to` (optional) - End date (ISO 8601)
- `limit` (optional) - Maximum results (default: 50)

**Example:**
```http
GET /api/search?q=protest&city=Jerusalem&limit=25
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "title": "Protest in Jerusalem",
      "description": "Large protest occurred...",
      "city": "Jerusalem",
      "relevance_score": 0.95,
      "highlight": "Large <mark>protest</mark> occurred..."
    }
  ],
  "total": 15,
  "query": "protest",
  "filters_applied": {
    "city": "Jerusalem"
  }
}
```

### Geographic Search

```http
GET /api/stories/by-location
```

**Parameters:**
- `lat` (required) - Latitude
- `lng` (required) - Longitude  
- `radius` (optional) - Search radius in km (default: 5)

**Response:**
```json
{
  "stories": [
    {
      "id": 1,
      "title": "Local Story",
      "distance_km": 2.3,
      "lat": 31.7683,
      "lng": 35.2137
    }
  ],
  "center": {
    "lat": 31.7683,
    "lng": 35.2137
  },
  "radius_km": 5
}
```

## AI Features API

### Generate Melo Summary

```http
POST /api/generate-melo-summary
```

**Request Body:**
```json
{
  "story_ids": [1, 2, 3],
  "format": "professional",
  "max_length": 500
}
```

**Response:**
```json
{
  "summary": "**Daily News Summary - January 15, 2024**\n\nToday's reports highlight...",
  "word_count": 347,
  "stories_included": 3,
  "generated_at": "2024-01-15T15:00:00Z",
  "model_used": "gpt-3.5-turbo"
}
```

### News Chat

```http
POST /api/news-chat
```

**Request Body:**
```json
{
  "news_id": "story_123",
  "message": "What are the implications of this event?",
  "context": {
    "title": "Story Title",
    "description": "Story description",
    "city": "Gaza",
    "lat": 31.5017,
    "lon": 34.4668
  }
}
```

**Response:**
```json
{
  "response": "Based on the context provided, this event has several implications...",
  "conversation_id": "conv_456",
  "response_time_ms": 2300,
  "model_used": "thaura-ai"
}
```

### Get Chat History

```http
GET /api/news-chat/:conversation_id
```

**Response:**
```json
{
  "conversation_id": "conv_456", 
  "messages": [
    {
      "type": "user",
      "message": "What happened here?",
      "timestamp": "2024-01-15T14:00:00Z"
    },
    {
      "type": "assistant", 
      "message": "Based on the reports...",
      "timestamp": "2024-01-15T14:00:03Z"
    }
  ],
  "story_context": {
    "id": "story_123",
    "title": "Story Title"
  }
}
```

### Clear Chat Conversation

```http
DELETE /api/news-chat/:conversation_id
```

**Response:** `204 No Content`

### City History

```http
POST /api/city-history
```

**Request Body:**
```json
{
  "lat": 31.7683,
  "lon": 35.2137,
  "city": "Jerusalem"
}
```

**Response:**
```json
{
  "status": "success",
  "history": "Jerusalem is one of the oldest cities in the world, serving as a holy site...",
  "city": "Jerusalem",
  "generated_at": "2024-01-15T14:00:00Z",
  "cached": false
}
```

## Metadata API

### Summary Metadata

```http
GET /api/summary-metadata
```

**Response:**
```json
{
  "total_stories": 1247,
  "latest_story": "2024-01-15T14:30:00Z",
  "oldest_story": "2023-12-01T08:00:00Z",
  "cities_covered": 45,
  "countries": ["Palestine", "Israel"],
  "story_sources": [
    "https://t.me/channel1",
    "https://t.me/channel2"
  ]
}
```

### Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T15:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "ai_services": {
      "openai": "configured",
      "claude": "configured", 
      "thaura": "configured"
    },
    "kafka": "running"
  }
}
```

## Error Responses

### Standard Error Format

```json
{
  "error": "Error type",
  "message": "Human-readable error message",
  "code": "ERROR_CODE",
  "timestamp": "2024-01-15T15:00:00Z",
  "request_id": "req_123456"
}
```

### Common Error Codes

| Status | Code | Description |
|--------|------|-------------|
| 400 | `INVALID_REQUEST` | Malformed request body or parameters |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Resource already exists or conflict |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 429 | `RATE_LIMIT` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | External service unavailable |

### Example Error Response

```json
{
  "error": "Validation Error",
  "message": "Required field 'title' is missing",
  "code": "VALIDATION_ERROR", 
  "timestamp": "2024-01-15T15:00:00Z",
  "request_id": "req_123456",
  "details": {
    "field": "title",
    "constraint": "required"
  }
}
```

## Rate Limiting

**Limits:**
- General API: 1000 requests/hour per IP
- AI endpoints: 100 requests/hour per IP
- Search: 500 requests/hour per IP

**Headers:**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642262400
```

## Data Types

### Story Object
```typescript
{
  id: number,
  title: string,
  description: string,
  city: string,
  country: string,
  lat: number,        // Latitude (-90 to 90)
  lng: number,        // Longitude (-180 to 180)
  date_occurred: string,  // ISO 8601 timestamp
  source_url: string,
  created_at: string      // ISO 8601 timestamp
}
```

### Coordinate Object
```typescript
{
  lat: number,    // Latitude
  lng: number     // Longitude  
}
```

### Search Result Object
```typescript
{
  id: number,
  title: string,
  description: string,
  city: string,
  relevance_score: number,    // 0.0 to 1.0
  highlight: string           // HTML with <mark> tags
}
```

## SDKs and Clients

### JavaScript/Node.js Example

```javascript
const MeloNewsClient = {
  baseURL: 'http://localhost:5000/api',
  
  async getStories(limit = 100) {
    const response = await fetch(`${this.baseURL}/stories?limit=${limit}`);
    return await response.json();
  },
  
  async searchStories(query, filters = {}) {
    const params = new URLSearchParams({ q: query, ...filters });
    const response = await fetch(`${this.baseURL}/search?${params}`);
    return await response.json();
  },
  
  async generateSummary(storyIds) {
    const response = await fetch(`${this.baseURL}/generate-melo-summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ story_ids: storyIds })
    });
    return await response.json();
  }
};
```

### Python Example

```python
import requests

class MeloNewsClient:
    def __init__(self, base_url='http://localhost:5000/api'):
        self.base_url = base_url
    
    def get_stories(self, limit=100):
        response = requests.get(f'{self.base_url}/stories', 
                              params={'limit': limit})
        return response.json()
    
    def search_stories(self, query, **filters):
        params = {'q': query, **filters}
        response = requests.get(f'{self.base_url}/search', params=params)
        return response.json()
    
    def generate_summary(self, story_ids):
        response = requests.post(f'{self.base_url}/generate-melo-summary',
                               json={'story_ids': story_ids})
        return response.json()
```

## Webhooks (Future)

*Webhooks for real-time notifications are planned for future releases.*

**Planned Events:**
- `story.created` - New story added
- `story.updated` - Story modified  
- `summary.generated` - AI summary completed
- `chat.message` - New chat message

## Versioning

The API uses semantic versioning. Current version: `v1`

**URL Structure:**
- Current: `/api/endpoint` (default v1)
- Future: `/api/v2/endpoint` (explicit versioning)

**Backward Compatibility:**
- v1 will be maintained for 12 months after v2 release
- Breaking changes only in major versions
- Deprecation notices 6 months before removal