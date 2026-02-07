# Installation Guide

## Prerequisites

### Required Software
- **Docker** and **Docker Compose** (recommended for production)
- **Python 3.8+** (for development)
- **Node.js 16+** (for frontend development)
- **PostgreSQL 13+** (if not using Docker)

### Required API Keys
- **OpenAI API Key** (for AI summaries and chat)
- **Claude API Key** (optional, for enhanced AI responses)
- **Thaura.ai API Key** (optional, for additional AI capabilities)

## Quick Start with Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/Emesgee/Melo-News.git
   cd melo-news
   ```

2. **Configure environment**
   ```bash
   cp config.py.example config.py
   # Edit config.py with your API keys and settings
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Web interface: http://localhost:5000
   - API endpoints: http://localhost:5000/api

## Development Installation

### Backend Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database setup**
   ```bash
   # Create PostgreSQL database
   createdb mydb
   
   # Run migrations (if available)
   python migrate.py
   ```

4. **Configure settings**
   ```bash
   cp config.py.example config.py
   # Edit config.py with your database and API settings
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd app/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm start
   ```

## Configuration

### Essential Settings (config.py)

```python
# Database Configuration
DATABASE_URL = "postgresql://user:password@localhost:5432/melo_news"

# API Keys
OPENAI_API_KEY = "your_openai_api_key_here"
CLAUDE_API_KEY = "your_claude_api_key_here"  # Optional
THAURA_AI_API_KEY = "your_thaura_ai_api_key_here"  # Optional

# Telegram Settings
TELEGRAM_CHANNELS = [
    "https://t.me/channel1",
    "https://t.me/channel2"
]

# Geospatial Settings
DEFAULT_CENTER_LAT = 31.7683
DEFAULT_CENTER_LNG = 35.2137
MAX_ZOOM_LEVEL = 16  # Privacy protection
```

### Docker Configuration

The `docker-compose.yaml` includes:
- **PostgreSQL** database with persistent storage
- **Kafka** for real-time streaming
- **Redis** for caching
- **Web application** with auto-reload

## Verification

1. **Check services are running**
   ```bash
   docker-compose ps
   ```

2. **Verify database connection**
   ```bash
   python -c "from app import create_app; app = create_app(); print('Database connected!')"
   ```

3. **Test API endpoints**
   ```bash
   curl http://localhost:5000/api/health
   ```

## Troubleshooting

### Common Issues

**Port conflicts**
- Change ports in `docker-compose.yaml` if 5000, 5432, or 9092 are in use

**Database connection errors**
- Ensure PostgreSQL is running: `docker-compose logs postgres`
- Check credentials in config.py

**Selenium/Chrome issues**
- Install Chrome and ChromeDriver for local development
- Use headless mode in production: `CHROME_HEADLESS = True`

**API key errors**
- Verify API keys are valid and have sufficient credits
- Check API key permissions for your use case

### Getting Help

- Check the [troubleshooting docs](docs/troubleshooting.md)
- Open an issue on GitHub
- Join our community discussions

## Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive configuration
- Implement rate limiting for production deployments
- Regular security updates for all dependencies
