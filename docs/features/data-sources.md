# Data Sources - Telegram Scraping & User Uploads

## Overview

Melo-News ingests news stories from two primary sources: automated Telegram channel scraping and user-uploaded files. Both sources feed into a unified processing pipeline that handles deduplication, geocoding, and story validation.

## Telegram Scraping (Automated)

### How It Works

The system continuously monitors configured Telegram channels for new posts using automated web scraping:

```
Telegram Channels → Selenium WebDriver → Content Extraction → Kafka Stream → Database
```

### Configuration

**Environment Setup:**
```bash
# In config.py
TELEGRAM_CHANNELS = [
    "https://t.me/channel1",
    "https://t.me/channel2",
    "https://t.me/your_news_source"
]

# Chrome settings for scraping
CHROME_HEADLESS = True
CHROME_NO_SANDBOX = False
```

### Technical Implementation

**Scraping Process:**
1. **Channel Monitoring** - Selenium checks configured channels every few minutes
2. **Content Extraction** - Extracts post text, media, timestamps, and metadata
3. **Data Validation** - Checks for valid location information and content quality
4. **Kafka Publishing** - Sends extracted data to Kafka streams for processing

**Key Files:**
- `kafkaProducer.py` - Main scraping logic and Kafka publishing
- `palestinescrapper.py` - Specialized scraper for Palestinian news sources
- `app/telegram/` - Telegram-specific processing modules

### Data Extracted

From each Telegram post:
- **Content**: Post text and description
- **Media**: Images, videos, documents
- **Location**: Geographic coordinates (if available)
- **Timestamp**: When the post was created
- **Source**: Original Telegram channel and post URL
- **Metadata**: Views, forwards, reactions (if available)

## User Uploads (Manual)

### Supported File Types

The system accepts various file formats from users:

**Documents:**
- PDF reports and articles
- Word documents (.docx, .doc)
- Text files (.txt, .md)
- Structured data (JSON, CSV)

**Media:**
- Images (JPG, PNG, GIF)
- Videos (MP4, AVI, MOV)
- Audio files (MP3, WAV)

**Archives:**
- ZIP files containing multiple stories
- Compressed document collections

### Upload Process

```
User File → Upload API → File Validation → Content Extraction → Story Creation
```

**Step-by-Step:**
1. **Authentication** - User must be logged in with valid JWT token
2. **File Validation** - Check file size, type, and format
3. **Azure Storage** - Upload file to cloud storage for persistence
4. **Content Processing** - Extract text and metadata from file
5. **Story Generation** - Create news stories from extracted content
6. **Database Storage** - Save processed stories with source attribution

### API Integration

**Upload Endpoint:**
```http
POST /api/file_upload/upload
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data

{
  "file": <binary_data>,
  "file_type_id": 1,
  "description": "Optional description"
}
```

**Processing Results:**
- Files are processed asynchronously
- Users receive immediate confirmation of upload
- Story extraction results are available via separate API
- Failed processing generates error logs for debugging

## Unified Processing Pipeline

### Deduplication Strategy

Both sources feed into the same deduplication system:

**Multi-Layer Detection:**
1. **Exact Match** - Same story ID or URL
2. **Location + Time** - Same coordinates within time window
3. **Content Similarity** - Text similarity analysis
4. **Cross-Source** - Prevents duplicates between Telegram and uploads

### Quality Assurance

**Automated Validation:**
- Geographic coordinate verification
- Content quality scoring
- Source credibility assessment
- Spam and noise filtering

**Manual Review:**
- Flagged content review system
- User reporting mechanism
- Community moderation tools

## Configuration & Management

### Telegram Channel Management

**Adding New Channels:**
```python
# In config.py
TELEGRAM_CHANNELS = [
    "https://t.me/existing_channel",
    "https://t.me/new_channel",  # Add new sources here
]
```

**Channel Monitoring:**
- Real-time status dashboard
- Scraping success/failure rates
- Content volume metrics
- Channel health monitoring

### Upload System Configuration

**File Size Limits:**
```python
# In config.py
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB default
UPLOAD_FOLDER = 'app/uploads'
```

**Storage Integration:**
```python
# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = "your_connection_string"
AZURE_CONTAINER_NAME = "uploads"
```

## Data Flow Visualization

```
┌─────────────────┐     ┌─────────────────┐
│   Telegram      │────▶│   Raw Content   │
│   Scraping      │     │   Extraction    │
└─────────────────┘     └─────────────────┘
                                │
┌─────────────────┐             ▼
│   User File     │     ┌─────────────────┐     ┌─────────────────┐
│   Uploads       │────▶│   Kafka Stream  │────▶│   PostgreSQL    │
└─────────────────┘     │   Processing    │     │   Database      │
                        └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Deduplication  │
                        │   & Validation  │
                        └─────────────────┘
```

## Monitoring & Analytics

### Data Source Metrics

**Telegram Scraping:**
- Stories scraped per hour
- Channel availability status
- Processing success rates
- Geographic coverage

**User Uploads:**
- Files uploaded per day
- Processing completion rates
- File type distribution
- User engagement levels

### Quality Metrics

**Content Quality:**
- Duplicate detection rates
- Geographic accuracy
- Content completeness
- Source verification status

## Security Considerations

### Telegram Scraping
- Rate limiting to avoid detection
- Rotating user agents and IPs
- Respect for channel terms of service
- No private channel access

### User Uploads
- File type validation and sanitization
- Malware scanning for uploaded files
- User authentication and authorization
- Content moderation and filtering

## Troubleshooting

### Common Telegram Issues
- **Chrome driver not found**: Install ChromeDriver and update PATH
- **Channel access denied**: Verify channel URLs are public
- **Rate limiting**: Reduce scraping frequency in configuration

### Upload Issues
- **File too large**: Check MAX_CONTENT_LENGTH setting
- **Processing failed**: Review file format compatibility
- **Azure connection**: Verify storage connection string

## Future Enhancements

### Planned Features
- RSS feed integration
- Social media platform scraping
- Real-time collaboration features
- Advanced content classification
- Multi-language content processing