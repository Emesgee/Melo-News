# Contributing to Melo-News

We welcome contributions to Melo-News! This guide will help you get started with contributing to our community-controlled news intelligence platform.

## 🌍 Project Mission

Melo-News empowers communities to own their narrative through real-time news intelligence, with a focus on Palestinian liberation and global replication for marginalized communities.

## 🚀 Quick Start

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/melo-news.git
   cd melo-news
   ```
3. **Set up development environment** (see [INSTALLATION.md](INSTALLATION.md))
4. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
5. **Make your changes**
6. **Submit a pull request**

## 🎯 Ways to Contribute

### Code Contributions
- **Frontend Development** - React components, UI/UX improvements
- **Backend Development** - Flask APIs, data processing
- **AI Integration** - Enhance AI features and accuracy
- **Infrastructure** - Docker, deployment, performance optimization
- **Mobile Support** - Responsive design improvements

### Non-Code Contributions  
- **Documentation** - Improve guides, tutorials, API docs
- **Testing** - Manual testing, automated test creation
- **Translation** - Multi-language support
- **Design** - UI/UX design, accessibility improvements
- **Community** - User support, community management

### Data & Research
- **Source Integration** - Add new news sources
- **Data Quality** - Improve deduplication and validation
- **Regional Expansion** - Extend to new geographic areas
- **Fact Checking** - Enhance verification systems

## 🏗️ Development Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- Docker & Docker Compose
- Git

### Environment Setup
```bash
# Backend environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend environment
cd app/frontend
npm install

# Configuration
cp config.py.example config.py
# Edit config.py with your API keys
```

### Running Locally
```bash
# Start services
docker-compose up -d postgres kafka redis

# Backend
python main.py

# Frontend (new terminal)
cd app/frontend && npm start
```

## 📝 Coding Standards

### Python (Backend)
- **Style**: Follow PEP 8
- **Type Hints**: Use type hints for functions
- **Documentation**: Docstrings for all public functions
- **Testing**: Write tests for new features

```python
def process_story_data(story: dict) -> dict:
    """
    Process raw story data and return cleaned version.
    
    Args:
        story: Raw story data from scraper
        
    Returns:
        Cleaned and validated story data
    """
    # Implementation here
```

### JavaScript/React (Frontend)
- **Style**: Use Prettier for formatting
- **Components**: Functional components with hooks
- **PropTypes**: Define prop types for all components
- **Testing**: Jest tests for utilities, React Testing Library for components

```javascript
import PropTypes from 'prop-types';

const NewsStoryCard = ({ story, onClick }) => {
  // Component implementation
};

NewsStoryCard.propTypes = {
  story: PropTypes.object.isRequired,
  onClick: PropTypes.func
};
```

### General Guidelines
- **Commits**: Use conventional commit messages
- **Branches**: Use descriptive branch names (`feature/add-search`, `fix/popup-bug`)
- **Code Review**: All changes require review before merging
- **Security**: Never commit API keys or sensitive data

## 🧪 Testing

### Running Tests
```bash
# Python tests
pytest tests/

# JavaScript tests  
cd app/frontend && npm test

# Integration tests
python -m pytest tests/integration/

# End-to-end tests (if available)
npm run test:e2e
```

### Writing Tests
- **Unit Tests**: Test individual functions/components
- **Integration Tests**: Test API endpoints and workflows
- **Performance Tests**: For data processing pipelines
- **Accessibility Tests**: Ensure WCAG compliance

### Test Coverage
- Aim for >80% code coverage
- All new features must include tests
- Critical paths require comprehensive testing

## 🗂️ Project Structure

```
melo-news/
├── app/                    # Flask application
│   ├── __init__.py
│   ├── models.py          # Database models
│   ├── auth/              # Authentication
│   ├── search/            # Search functionality
│   ├── summary/           # AI summary features
│   ├── city_history/      # Historical context
│   └── frontend/          # React application
├── docs/                  # Documentation
├── tests/                 # Test suite
├── config.py              # Configuration
├── main.py               # Application entry point
├── docker-compose.yaml   # Development services
└── requirements.txt      # Python dependencies
```

## 🎨 Design Guidelines

### UI/UX Principles
- **Accessibility First** - WCAG 2.1 AA compliance
- **Mobile Responsive** - Progressive enhancement
- **Performance** - Fast loading, optimized images
- **Internationalization** - Prepare for multi-language support

### Visual Identity
- **Colors**: Maintain existing color scheme
- **Typography**: Readable, accessible fonts
- **Icons**: Consistent iconography
- **Layout**: Clean, information-focused design

## 🐛 Bug Reports

### Before Reporting
1. Search existing issues
2. Try to reproduce the bug
3. Test on different browsers/devices
4. Check if it's already fixed in latest version

### Bug Report Template
```markdown
**Bug Description**
Clear description of what's wrong

**Steps to Reproduce**
1. Go to...
2. Click on...
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**  
What actually happens

**Environment**
- OS: [Windows/Mac/Linux]
- Browser: [Chrome/Firefox/Safari]
- Version: [version number]

**Screenshots**
If applicable, add screenshots
```

## 💡 Feature Requests

### Feature Request Process
1. **Discussion** - Open an issue to discuss the idea
2. **Design** - Create detailed specification
3. **Approval** - Get maintainer approval
4. **Implementation** - Develop the feature
5. **Review** - Code review and testing
6. **Documentation** - Update docs and guides

### Feature Request Template
```markdown
**Feature Description**
What feature would you like to see?

**Use Case**
Why is this feature needed?

**Proposed Implementation**
How might this be implemented?

**Alternatives Considered**
What other solutions were considered?

**Additional Context**
Any other relevant information
```

## 🚀 Pull Request Process

### Before Submitting
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with main

### Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature  
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots (if UI changes)
Before/after screenshots

## Checklist
- [ ] Code follows project guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

### Review Process
1. **Automated Checks** - CI/CD pipeline runs
2. **Code Review** - Maintainer review
3. **Testing** - Manual testing if needed
4. **Approval** - Approved by maintainer
5. **Merge** - Merged to main branch

## 🌐 Community Guidelines

### Code of Conduct
- **Respect** - Treat everyone with respect
- **Inclusion** - Welcome all backgrounds and skill levels
- **Collaboration** - Work together constructively
- **Focus** - Keep discussions relevant and productive

### Communication Channels
- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - General discussions and questions
- **Pull Requests** - Code review and collaboration

### Getting Help
1. **Documentation** - Check existing docs first
2. **Search Issues** - Look for existing discussions
3. **Ask Questions** - Open a GitHub discussion
4. **Community Support** - Connect with other contributors

## 🏆 Recognition

### Contributors
All contributors are recognized in:
- README.md contributor section
- Release notes
- Annual contributor highlights

### Types of Recognition
- **First-time contributor** badges
- **Significant contribution** highlights
- **Community contributor** recognition
- **Maintainer** status for long-term contributors

## 📄 License

By contributing to Melo-News, you agree that your contributions will be licensed under the MIT License.

## 🔗 Resources

- **Project Documentation** - [docs/](docs/)
- **Installation Guide** - [INSTALLATION.md](INSTALLATION.md)
- **API Reference** - [docs/api-reference.md](docs/api-reference.md)
- **Architecture Overview** - [docs/architecture.md](docs/architecture.md)

## 📞 Contact

- **Project Maintainers** - Create a GitHub issue
- **Security Issues** - See security policy
- **General Questions** - GitHub discussions

---

**Thank you for contributing to Melo-News!** 🙏

Together, we're building tools that empower communities to control their narrative and fight for justice through technology.

🇵🇸 **Free Palestine** - Tech for Liberation