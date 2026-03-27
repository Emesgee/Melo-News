# Melo-News: Community-Controlled News Intelligence Platform

🇵🇸 **Empowering communities to own their narrative through real-time news intelligence**

[![Tech4Palestine](https://img.shields.io/badge/Tech4Palestine-Community%20Project-red)](https://tech4palestine.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-v18+-blue.svg)](https://reactjs.org/)
[![Kafka](https://img.shields.io/badge/Kafka-Real--Time%20Streaming-blue)]()
[![Docker](https://img.shields.io/badge/Docker-Production%20Ready-blue)]()

Melo-News is an AI-powered, geospatially-aware news aggregation platform that transforms fragmented grassroots reports into organized, verifiable, community-controlled intelligence. Built for Palestinian liberation and designed for global replication.

> **🚨 Important**: This project was developed to amplify Palestinian voices and support liberation movements. While the code is open-source, we encourage ethical use that promotes justice and human rights.

## 🎥 Demo & Screenshots

*Coming soon: Add screenshots of the interface*

## 🚀 Key Features

### 📡 **Dual-Source Data Pipeline**
- **Automated Scraping**: Telegram channels (QudsNen, eye_on_palestine)
- **Real-Time Processing**: Kafka streaming with 10+ messages/hour
- **Geospatial Filtering**: 172 Palestinian towns/cities
- **Cloud Storage**: Azure Blob integration for media files
- **Deduplication**: Intelligent duplicate detection
- Handles **500+ stories/hour** with **100+ concurrent users**

### 🗺️ **Interactive Geospatial Mapping**
- Interactive Leaflet maps with marker clustering
- Stories plotted by geographic coordinates
- Popup panels with Info/Chat tabs
- Zoom restrictions for privacy (3km max detail)

### 🤖 **AI-Powered Intelligence**
- **Melo Summary**: Professional journalist-style news summaries
- **News Chat**: Multi-turn conversations about individual stories  
- **City History**: AI-generated historical context for locations
- **Smart Tags**: Automatic categorization and metadata extraction

### 🔍 **Advanced Search & Filtering**
- Dynamic tag generation from search results
- Real-time search with geospatial filtering
- Deduplication prevents false amplification
- Export summaries (HTML, PDF, Text)

### 🏛️ **Community-Controlled Infrastructure**
- Self-hostable with Docker Compose
- Open-source and auditable codebase
- No corporate dependencies
- Community governance ready
- **Hourly automated pipeline** for continuous updates

## 🚦 Quick Start

### Option 1: Docker (Recommended for Production)
```bash
# Clone repository
git clone https://github.com/your-org/melo-news.git
cd melo-news

# Create production environment
cp .env.example .env.production
# Edit .env.production with your credentials

# Start full stack (Kafka, PostgreSQL, Scheduler)
docker-compose up -d

# View logs
docker logs -f melo-scheduler

# Access application
http://localhost:3000
```

### Option 2: Development Setup
```bash
# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings

# Run pipeline manually
python run_kafka_pipeline.py

# Run scheduler (production)
set ENVIRONMENT=production
python schedule_pipeline.py

# Frontend (new terminal)
cd app/frontend
npm install && npm start
```
Open http://localhost:3000

### Option 3: Linux/Ubuntu Server
```bash
# SSH to server
ssh user@your-server.com
cd /home/ubuntu/Melo-News

# Create environment
cp .env.example .env.production
nano .env.production  # Edit credentials

# Create systemd service
sudo nano /etc/systemd/system/melo-news.service
# (See deployment section below)

# Start service
sudo systemctl enable melo-news
sudo systemctl start melo-news
sudo systemctl status melo-news
```

### Option 4: Windows Server (NSSM)
```powershell
# Install NSSM from https://nssm.cc/download
# Extract to C:\nssm\

# Install service
C:\nssm\nssm.exe install MeloNewsScheduler "python" "schedule_pipeline.py"
C:\nssm\nssm.exe set MeloNewsScheduler AppDirectory "C:\Melo-News"
C:\nssm\nssm.exe set MeloNewsScheduler AppEnvironmentExtra ENVIRONMENT=production

# Start service
net start MeloNewsScheduler
sc query MeloNewsScheduler
```

## 📋 Prerequisites

**Required API Keys:**
- **OpenAI API Key** - For AI summaries ([Get key](https://platform.openai.com/api-keys))
- **Anthropic Claude** - For enhanced features ([Get key](https://console.anthropic.com/))
- **Telegram API** - For channel scraping (optional, supports public channels)
- **Azure Storage** - For media uploads ([Setup guide](https://learn.microsoft.com/en-us/azure/storage/))

**Software:**
- Python 3.8+ and Node.js 16+
- Docker and Docker Compose (recommended)
- PostgreSQL 13+
- Kafka 2.8+ (included in docker-compose)

See [INSTALLATION.md](INSTALLATION.md) for detailed setup instructions.

## 🛠️ Tech Stack

**Backend:**
- Python/Flask API server
- Kafka for real-time streaming
- PostgreSQL for data persistence
- Docker containerization
- OpenAI API integration
- Geospatial processing (GeoJSON)

**Frontend:**
- React with Leaflet mapping
- Real-time WebSocket connections
- Responsive design for mobile/desktop
- Dynamic search with auto-generated tags

**Infrastructure:**
- Docker Compose for local & production deployment
- Kafka streaming for real-time processing
- PostgreSQL for persistent storage
- Azure Blob Storage for media
- Systemd/NSSM service management
- Prometheus + Grafana monitoring (optional)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Telegram Channels (QudsNen, eye_on_palestine)              │
│         ↓ (kafkaProducer.py scrapes)                        │
│  Filter by Palestinian Location (172 towns from GeoJSON)   │
│         ↓ (produces to Kafka)                               │
│  Kafka Topic: eyesonpalestine                               │
│              ↓ (kafkaConsumer.py - unique group per run)    │
│  Detect Location + Download Media                           │
│              ↓ (processes data)                             │
│  PostgreSQL Database (persists data)                        │
│              ↓ (Flask API reads)                            │
│  React Frontend (displays on map)                           │
└─────────────────────────────────────────────────────────────┘

Production Scheduler:
┌─────────────────────────────┐
│ schedule_pipeline.py        │ ← Runs every hour
│ (ENVIRONMENT=production)    │
│         ↓                   │
│ Full Pipeline Cycle         │ ← Auto-repeat
│ (Scrape → Kafka → DB)       │
└─────────────────────────────┘
```

## 📊 Current Capabilities

- **10+ stories/hour** (Telegram scraping)
- **Real-time Kafka streaming** with message deduplication
- **100+ concurrent users** supported
- **Multi-language** content processing
- **Real-time** updates and notifications
- **Offline-ready** with data caching
- **Automated hourly runs** in production

## 🚀 Kafka Pipeline Features

### Automated Hourly Operation
```bash
# Development: Manual runs
python run_kafka_pipeline.py

# Production: Every hour (automatic)
set ENVIRONMENT=production
python schedule_pipeline.py
```

### Pipeline Steps
1. **Producer** (`kafkaProducer.py`):
   - Scrapes Telegram channels
   - Filters by Palestinian locations (GeoJSON)
   - Produces to Kafka topic `eyesonpalestine`
   - Sends 7-10 messages per run

2. **Consumer** (`kafkaConsumer.py`):
   - Reads all messages from Kafka (unique group per run)
   - Detects missing locations via NLP
   - Downloads videos/images to Azure
   - Inserts into PostgreSQL

3. **Scheduler** (`schedule_pipeline.py`):
   - Runs pipeline every hour (production only)
   - Logs all activities
   - Auto-restarts on failure
   - Monitoring via process checks

## 📚 Documentation

- **[Installation Guide](INSTALLATION.md)** - Complete setup instructions
- **[Kafka Pipeline Guide](docs/KAFKA_PIPELINE.md)** - Real-time streaming setup
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment
- **[Feature Documentation](docs/features/)** - Detailed feature guides
- **[API Reference](docs/api-reference.md)** - REST API documentation  
- **[Architecture Overview](docs/architecture.md)** - System architecture
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick ways to help:**
- 🐛 Report bugs or suggest features
- 📝 Improve documentation
- 🎨 Enhance UI/UX design
- 🌐 Add translations
- 💻 Contribute code
- 📊 Help with data verification

## 🛡️ Security & Privacy

- **Rate limiting** on all APIs
- **Input validation** and sanitization
- **Secure environment variable** handling
- **Community-controlled** data governance
- **HTTPS/TLS** ready for production
- **No tracking** or analytics by default
- **GDPR-compliant** data handling

## 📈 Roadmap

**Phase 1 (✅ Complete):** 
- Kafka pipeline working end-to-end
- Docker deployment ready
- Hourly scheduler operational

**Phase 2 (3-6 months):** 
- Multi-region splitting
- Microservices architecture
- Enhanced monitoring/alerting

**Phase 3 (6-12 months):** 
- Global federation
- ML-based intelligence
- Community governance dashboard

## 🏛️ Community & Governance

- **Tech4Palestine** aligned development
- **Community-controlled** infrastructure
- **Transparent** decision-making
- **Open-source** by design
- **Monthly community calls** for decision-making

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

Built with ❤️ for Palestinian liberation and community empowerment.

## 🌍 Vision

**For Palestinian Communities:**
- Document reality in real-time
- Counter narrative control
- Preserve historical truth
- Enable rapid coordination
- Own their data infrastructure

**For Global Communities:**
- Replicable for any conflict zone
- Decentralized truth infrastructure
- Community-governed development
- Open-source transparency
- Liberation technology framework

## 📖 Environment Configuration

### Development Mode
```bash
# Default, no scheduler
python run_kafka_pipeline.py
```

### Production Mode
```bash
set ENVIRONMENT=production
python schedule_pipeline.py
```

### Environment Variables
```
ENVIRONMENT=production                              # dev/production
KAFKA_BOOTSTRAP_SERVERS=kafka:9092                 # Kafka broker
DB_HOST=postgres                                    # Database host
DB_PORT=5432                                        # Database port
DB_NAME=melo_news_prod                             # Database name
DB_USER=admin                                       # Database user
DB_PASSWORD=secure_password                         # Database password
AZURE_STORAGE_CONNECTION_STRING=...                # Azure credentials
AZURE_BLOB_CONTAINER=media-prod                    # Storage container
```

## 🙏 Acknowledgments

- Tech4Palestine community
- Palestinian journalists and activists
- Open-source contributors
- Human rights organizations
- Kafka & Apache communities

## 📞 Contact

- **Community:** [Tech4Palestine](https://tech4palestine.org)
- **Issues:** [GitHub Issues](https://github.com/yourusername/Melo-News/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/Melo-News/discussions)

---

**"When communities control their own narrative infrastructure, truth becomes unstoppable."**

🇵🇸 Built with ❤️ for Palestinian liberation and global justice

**Latest Update:** Kafka pipeline production-ready with hourly scheduler ✅ 🚀