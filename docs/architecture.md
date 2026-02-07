# Architecture & Technology

## System Overview

Melo-News is built as a modern, scalable web application with real-time data processing capabilities. The architecture separates concerns between data ingestion, processing, storage, and presentation layers.

## Core Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   Kafka      │───▶│   PostgreSQL    │
│ • Telegram      │    │  Streaming   │    │   Database      │
│ • User Uploads  │    │  Pipeline    │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                       │
                              ▼                       ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   React         │◄───│    Flask     │◄───│  Processing &   │
│   Frontend      │    │   Backend    │    │  Deduplication  │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## Data Sources & Ingestion

### Automated Telegram Scraping
- **Selenium WebDriver** - Automated browser control for Telegram web interface
- **Chrome/ChromeDriver** - Headless browser for scraping operations
- **Real-time Processing** - Continuous monitoring of configured channels
- **Kafka Integration** - Scraped data flows through Kafka streams

### User File Uploads
- **File Upload API** - `/api/file_upload/upload` endpoint for user content
- **Multiple Formats** - Supports documents, images, videos, and structured data
- **Azure Blob Storage** - Cloud storage for uploaded media files
- **Story Extraction** - Automatic processing of uploaded content into news stories

### Data Processing Pipeline
- **Deduplication** - Multi-layer duplicate detection across all sources
- **Geocoding** - Automatic location extraction and coordinate assignment
- **Validation** - Data quality checks and format standardization
- **Real-time Ingestion** - Both sources feed into unified processing pipeline

## Technology Stack

### Backend
- **Python 3.8+** - Core application language
- **Flask** - Web framework and REST API
- **PostgreSQL** - Primary database for stories and metadata
- **Apache Kafka** - Real-time data streaming and processing
- **Redis** - Caching layer (via Docker)

### Frontend  
- **React 18** - User interface framework
- **Leaflet** - Interactive mapping library
- **React-Leaflet** - React integration for maps
- **Modern CSS** - Responsive styling

### AI Integration
- **OpenAI API** - GPT models for Melo Summary generation
- **Anthropic Claude** - Historical context and chat fallback
- **Thaura.ai** - Primary chat service

### Infrastructure
- **Docker & Docker Compose** - Containerized deployment
- **Selenium WebDriver** - Web scraping automation
- **Chrome/ChromeDriver** - Browser automation

## Data Flow

### 1. Data Ingestion (Dual Sources)

**Automated Scraping:**
```
Telegram Channels → Selenium Scraper → Raw Story Data → Kafka Producer
```

**User Uploads:**
```
User Files → File Upload API → File Processing → Story Extraction → Database
```

### 2. Stream Processing  
```
Raw Data → Kafka Producer → Kafka Streams → Deduplication → PostgreSQL
```

### 3. User Interaction
```
User Request → React Frontend → Flask API → Database Query → Response
```

### 4. AI Processing
```
User Action → API Request → AI Service → Processed Response → UI Update
```

## Database Schema

### Stories Table
```sql
CREATE TABLE stories (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    date_occurred TIMESTAMP,
    source_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes
- Geographic coordinates (lat, lng)
- Date occurrence for temporal queries
- City names for location searches
- Full-text search on title and description

## API Design

### RESTful Endpoints

**Stories**
```
GET    /api/stories              # List all stories
POST   /api/stories              # Create new story
GET    /api/stories/:id          # Get specific story
PUT    /api/stories/:id          # Update story
DELETE /api/stories/:id          # Delete story
```

**Search & Filtering**
```
GET    /api/search?q=term        # Search stories
GET    /api/stories/by-location  # Geographic filtering
GET    /api/stories/by-date      # Temporal filtering
```

**AI Features**
```
POST   /api/generate-melo-summary # Generate AI summary
POST   /api/news-chat            # Chat about stories  
POST   /api/city-history         # Get location history
```

## Frontend Architecture

### Component Structure
```
src/
├── components/
│   ├── letleaf_map/
│   │   ├── MapArea.js           # Main map component
│   │   ├── MarkerPopupWrapper.js
│   │   ├── MeloSummary.js       # AI summary modal
│   │   ├── NewsChat.js          # Chat interface
│   │   └── CityHistory.js       # Historical context
│   ├── search/
│   │   └── SearchInterface.js
│   └── common/
│       └── Layout.js
├── utils/
│   └── storyUtils.js            # Deduplication logic
└── App.js                       # Root component
```

### State Management
- **Local State** - React hooks for component state
- **Props Drilling** - Simple data passing for current scale
- **Context API** - Could be added for global state if needed

### Performance Optimizations
- **React.memo** - Component memoization for expensive renders
- **useCallback** - Callback memoization for event handlers
- **Lazy Loading** - Code splitting for large components
- **Image Optimization** - Responsive images and lazy loading

## Real-Time Processing

### Kafka Configuration
```yaml
# docker-compose.yaml
kafka:
  image: confluentinc/cp-kafka:latest
  environment:
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
```

### Stream Processing Topics
- **raw-stories** - Initial scraped data
- **processed-stories** - Cleaned and validated data  
- **duplicate-stories** - Flagged duplicates for review
- **failed-stories** - Processing failures for debugging

### Deduplication Strategy
1. **Exact ID Match** - Same story ID from source
2. **URL Matching** - Same source URL
3. **Coordinate + Time** - Same location within time window
4. **Content Similarity** - Text similarity above threshold

## Scalability Considerations

### Current Capacity
- **Stories**: 500+ per hour sustained
- **Users**: 100+ concurrent users  
- **Response Time**: <2 seconds for most operations
- **Database**: Millions of stories supported

### Horizontal Scaling
- **Application**: Multiple Flask instances behind load balancer
- **Database**: PostgreSQL read replicas for queries
- **Kafka**: Partition scaling for increased throughput
- **Frontend**: CDN deployment for static assets

### Performance Monitoring
- **Application Metrics**: Response times, error rates
- **Database Metrics**: Query performance, connection pools
- **Infrastructure Metrics**: CPU, memory, disk usage
- **User Metrics**: Feature usage, session analytics

## Security Architecture

### API Security
- **Environment Variables** - Sensitive configuration
- **Input Validation** - SQL injection prevention
- **Rate Limiting** - API abuse protection
- **CORS Configuration** - Cross-origin request control

### Data Security
- **Database Encryption** - Encrypted data at rest
- **Transport Security** - HTTPS in production
- **API Key Management** - Secure credential handling
- **Access Logging** - Security audit trails

### Privacy Considerations
- **Coordinate Precision** - Limited zoom for privacy
- **Data Minimization** - Only necessary data collected
- **User Anonymization** - No personal data stored
- **GDPR Compliance** - European privacy regulations

## Development Workflow

### Local Development
```bash
# Backend
conda activate kafkaenv
python main.py

# Frontend  
cd app/frontend && npm start

# Database
docker-compose up postgres kafka redis
```

### Testing Strategy
- **Unit Tests** - Individual function testing
- **Integration Tests** - API endpoint testing  
- **End-to-End Tests** - Full user workflow testing
- **Performance Tests** - Load and stress testing

### Deployment Pipeline
1. **Development** - Local development and testing
2. **Staging** - Production-like environment testing
3. **Production** - Live deployment with monitoring
4. **Rollback** - Quick rollback capability for issues

## Configuration Management

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb

# AI Services  
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
THAURA_AI_API_KEY=...

# Application
FLASK_ENV=production
SECRET_KEY=your-secret-key
```

### Feature Flags
Environment-based feature enablement:
- AI_SUMMARY_ENABLED
- CHAT_FEATURE_ENABLED  
- REAL_TIME_UPDATES_ENABLED
- ADVANCED_SEARCH_ENABLED

## Monitoring & Observability

### Application Monitoring
- **Health Checks** - API endpoint availability
- **Performance Metrics** - Response time tracking
- **Error Tracking** - Exception monitoring and alerting
- **User Analytics** - Feature usage and engagement

### Infrastructure Monitoring  
- **Resource Usage** - CPU, memory, disk monitoring
- **Database Performance** - Query optimization tracking
- **Network Monitoring** - Bandwidth and latency tracking
- **Backup Monitoring** - Data backup verification

### Logging Strategy
- **Structured Logging** - JSON format for parsing
- **Log Levels** - INFO, WARN, ERROR categorization
- **Centralized Logs** - Aggregated logging for analysis
- **Retention Policy** - Automated log rotation and cleanup