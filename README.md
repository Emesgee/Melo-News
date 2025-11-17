# Melo-News: Community-Controlled News Intelligence Platform

🇵🇸 **Empowering communities to own their narrative through real-time news intelligence**

[![Tech4Palestine](https://img.shields.io/badge/Tech4Palestine-Community%20Project-red)](https://tech4palestine.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-v18+-blue.svg)](https://reactjs.org/)

Melo-News is an AI-powered, geospatially-aware news aggregation platform that transforms fragmented grassroots reports into organized, verifiable, community-controlled intelligence. Built for Palestinian liberation and designed for global replication.

> **🚨 Important**: This project was developed to amplify Palestinian voices and support liberation movements. While the code is open-source, we encourage ethical use that promotes justice and human rights.

## � Demo & Screenshots

*Coming soon: Add screenshots of the interface*

## �🚀 Key Features

### 📡 **Dual-Source Data Pipeline**
- **Automated Scraping**: Telegram channels via Selenium WebDriver
- **User Uploads**: Documents, media, and structured data files
- **Unified Processing**: Kafka streaming with intelligent deduplication
- **Cloud Storage**: Azure Blob integration for media files
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

## � Quick Start

### Option 1: Docker (Recommended)
```bash
git clone https://github.com/your-org/melo-news.git
cd melo-news
cp config.py.example config.py
# Edit config.py with your API keys
docker-compose up -d
```
Open http://localhost:5000

### Option 2: Development Setup
```bash
# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp config.py.example config.py
# Edit config.py with your settings
python main.py

# Frontend (new terminal)
cd app/frontend
npm install && npm start
```
Open http://localhost:3000

## 📋 Prerequisites

**Required API Keys:**
- **OpenAI API Key** - For AI summaries ([Get key](https://platform.openai.com/api-keys))
- **Anthropic Claude** - For enhanced features ([Get key](https://console.anthropic.com/))

**Software:**
- Python 3.8+ and Node.js 16+
- Docker and Docker Compose (recommended)
- PostgreSQL 13+ (if not using Docker)

See [INSTALLATION.md](INSTALLATION.md) for detailed setup instructions.

## �🛠️ Tech Stack

**Backend:**
- Python/Flask API server
- Kafka for real-time streaming
- PostgreSQL for data persistence
- Docker containerization
- OpenAI API integration

**Frontend:**
- React with Leaflet mapping
- Real-time WebSocket connections
- Responsive design for mobile/desktop
- Dynamic search with auto-generated tags

**Infrastructure:**
- Docker Compose for local deployment
- Prometheus + Grafana monitoring
- Automated backup systems
- Self-hostable by communities

## 🏗️ Architecture

```
┌─ Telegram Scraping ──┐    ┌── Kafka Stream ──┐    ┌─ PostgreSQL ─┐
└─ User File Uploads ──┘───▶│  Deduplication   │───▶│   Database   │
                            │  & Processing    │    │              │
Frontend (React) ◄────────── Flask API ◄────────┘    └──────────────┘
```

## 📊 Current Capabilities

- **100+ stories/hour** processing capacity
- **50+ concurrent users** supported
- **Multi-language** content processing
- **Real-time** updates and notifications
- **Offline-ready** with data caching

## 📚 Documentation

- **[Installation Guide](INSTALLATION.md)** - Complete setup instructions
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

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

Built with ❤️ for Palestinian liberation and community empowerment.

## 🌍 Vision

**For Palestinian Communities:**
- Document reality in real-time
- Counter narrative control
- Preserve historical truth
- Enable rapid coordination

**For Global Communities:**
- Replicable for any conflict zone
- Decentralized truth infrastructure
- Community-governed development
- Open-source transparency

## 🚦 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+

### Quick Start
```bash
# Clone the repository
git clone https://github.com/yourusername/Melo-News.git
cd Melo-News

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start with Docker Compose
docker-compose up -d

# Access the application
http://localhost:3000
```

### Manual Setup
```bash
# Backend setup
cd app
pip install -r requirements.txt
python main.py

# Frontend setup
cd app/frontend
npm install
npm start
```

## 📖 Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [API Documentation](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing Guidelines](docs/CONTRIBUTING.md)

## 🤝 Contributing

We welcome contributions from the Tech4Palestine community and beyond!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🛡️ Security

- Rate limiting on all APIs
- Input validation and sanitization
- Secure environment variable handling
- Community-controlled data governance

## 📈 Roadmap

**Phase 1 (0-3 months):** Production polish & Docker deployment
**Phase 2 (3-12 months):** Multi-region scaling & microservices
**Phase 3 (12+ months):** Global federation & ML intelligence

## 🏛️ Community & Governance

- **Tech4Palestine** aligned development
- **Community-controlled** infrastructure
- **Transparent** decision-making
- **Open-source** by design

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Tech4Palestine community
- Palestinian journalists and activists
- Open-source contributors
- Human rights organizations

## 📞 Contact

- **Founder:** Mohammad Ghadban
- **Community:** [Tech4Palestine](https://tech4palestine.org)
- **Issues:** [GitHub Issues](https://github.com/yourusername/Melo-News/issues)

---

**"When communities control their own narrative infrastructure, truth becomes unstoppable."**

🇵🇸 Built with ❤️ for Palestinian liberation and global justice