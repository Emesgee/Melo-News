# Melo Summary - AI-Powered News Summaries

## Overview

The Melo Summary feature provides professional AI-generated summaries of news stories from the platform. Users can generate one-page journalist-quality summaries with multiple export options.

## Key Features

- **🤖 AI-Powered**: Uses OpenAI ChatGPT with Claude fallback
- **📄 Export Options**: HTML, Text, and PDF formats
- **⚡ Real-time**: Generates summaries in 3-8 seconds
- **🎨 Professional**: Journalist-quality, neutral tone
- **📱 Responsive**: Works on all devices

## How to Use

1. **Access**: Click "📄 Generate Melo Summary" button (top-right of map)
2. **Review**: Modal shows available story count and metadata
3. **Generate**: Click "✨ Generate Summary" to create AI summary
4. **Export**: Choose from HTML, Text, or Print/PDF options

## Technical Details

### Components
- **Backend**: `app/summary/summary.py` - AI integration and API endpoints
- **Frontend**: `MeloSummary.js` - React modal and user interface
- **Styling**: `MeloSummary.css` - Professional responsive design

### API Endpoints
```
POST /api/generate-melo-summary   # Generate new summary
GET /api/summary-metadata         # Get available data count
```

### AI Configuration
- **Model**: GPT-3.5-turbo (primary), Claude (fallback)
- **Max Tokens**: 1000 (adjustable)
- **Tone**: Professional journalist
- **Length**: ~500 words maximum

## Setup Requirements

### Dependencies
```bash
# Frontend package
npm install html2pdf.js

# Environment variable
OPENAI_API_KEY=sk-your-api-key
```

### Cost Estimates
- Per summary: ~$0.003
- 1000 summaries/month: ~$3.00

## Export Formats

### HTML Export
- Professional formatting with inline styles
- Offline viewing capability
- Email-friendly format

### Text Export
- Plain text with metadata
- Easy editing and sharing
- Import to any text editor

### PDF Export
- Browser print dialog
- High-quality output
- Professional layout

## Customization

### Change AI Model
```python
# In app/summary/summary.py
'model': 'gpt-4'  # Higher quality
'model': 'gpt-3.5-turbo'  # Faster (default)
```

### Adjust Summary Length
```python
'max_tokens': 1500  # Longer summaries
'max_tokens': 500   # Shorter summaries
```

## Performance

- **Response Time**: 3-8 seconds depending on data volume
- **Database Query**: Optimized for latest 50 stories
- **Error Handling**: Comprehensive fallback system
- **Timeout**: 20-second API timeout with retry logic

## Troubleshooting

**Common Issues:**
- Missing API key: Set OPENAI_API_KEY environment variable
- No stories: Ensure database contains news stories
- Slow generation: Normal for 30+ stories (up to 8 seconds)
- Export not working: Check browser popup blockers

**Error Messages:**
- "API key not configured": Set up OpenAI API key
- "No stories available": Import news stories first
- "Generation failed": Check API key validity and credits