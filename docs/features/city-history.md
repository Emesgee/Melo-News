# City History - AI-Generated Historical Context

## Overview

The City History feature provides AI-generated historical summaries for locations when users click on story markers. It offers contextual background about cities and regions to enhance understanding of news stories.

## Key Features

- **🏛️ Historical Context**: AI-generated historical summaries for locations
- **🤖 AI-Powered**: Uses Claude AI for accurate historical information
- **🌍 Regional Focus**: Specialized for Israel-Palestine region
- **⚡ Fast Loading**: Client-side caching for instant repeat access
- **🎯 Contextual**: Integrates seamlessly with story popups

## How to Use

1. **View Stories**: Browse news stories on the interactive map
2. **Click Marker**: Click any story marker to open popup
3. **Auto-Load**: City History section automatically appears
4. **Read Context**: View 2-3 sentence historical summary
5. **Cache**: Subsequent visits to same location load instantly

## Technical Details

### Components
- **Backend**: `app/city_history/routes.py` - API endpoint and AI integration
- **Frontend**: `CityHistory.js` - React component with loading states
- **Styling**: `CityHistory.css` - Professional popup styling

### API Endpoint
```
POST /api/city-history
```

**Request Body:**
```json
{
  "lat": 31.9,
  "lon": 35.2,
  "city": "Jerusalem"
}
```

**Response:**
```json
{
  "status": "success", 
  "history": "Historical summary text...",
  "city": "Jerusalem"
}
```

### AI Configuration
- **Primary AI**: Claude (Anthropic)
- **Response Length**: 2-3 sentences
- **Focus**: Historical significance and cultural context
- **Cache**: 100 entries in memory

## Setup Requirements

### Environment Variables
```bash
# Required for AI-generated histories
ANTHROPIC_API_KEY=your_api_key_here
```

Get your API key from [Anthropic Console](https://console.anthropic.com/).

### Dependencies
All required packages included in existing setup.

## Regional Configuration

### Coverage Area
Currently configured for Israel-Palestine region:
```python
REGION_BOUNDS = {
    'min_lat': 31.2,
    'max_lat': 33.3,
    'min_lon': 34.2,
    'max_lon': 35.9
}
```

### Customization
Modify bounds in `app/city_history/routes.py` to support other regions.

## Features

### Intelligent Caching
- **Memory Cache**: Stores 100 most recent results
- **Instant Loading**: Cached results load immediately
- **Automatic Management**: LRU cache eviction when full

### Error Handling
- **Fallback Messages**: Graceful degradation when AI unavailable
- **Region Validation**: Checks if coordinates are in supported area
- **API Failures**: User-friendly error messages

### Loading States
- **Spinner**: Visual indicator while generating history
- **Progressive Loading**: Shows cache results immediately
- **Timeout Handling**: Reasonable timeout for API calls

## Example Histories

### Jerusalem
"Jerusalem is one of the oldest cities in the world, serving as a holy site for Judaism, Christianity, and Islam for thousands of years. The city has been continuously inhabited for over 3,000 years and has been the capital of numerous empires."

### Gaza
"Gaza has been an important coastal city for over 3,000 years, serving as a major trading hub between Africa and Asia. The city has been ruled by various empires including the Egyptians, Romans, Ottomans, and has a rich cultural heritage."

### Ramallah
"Ramallah emerged as an important Palestinian city in the 20th century, becoming the de facto administrative capital of the Palestinian territories. The city has grown from a small village into a major cultural and economic center."

## Integration

### Map Integration
- Automatically triggered when story markers are clicked
- Seamlessly integrated into popup interface
- Uses story coordinates for location context

### Story Context
History provides background for understanding:
- Regional significance of news events
- Cultural and historical context
- Geographic importance of locations

## Performance

### Response Times
- **Cached**: Instant (0ms)
- **First Request**: 2-3 seconds (AI generation)
- **Timeout**: 10 seconds maximum

### Caching Strategy
- **Size**: 100 entries maximum
- **Eviction**: Least Recently Used (LRU)
- **Scope**: Per application instance

### Cost Estimates
- **Per history**: ~$0.001-0.002
- **1000 unique locations**: ~$1-2

## Customization

### Modify History Length
```python
# In generate_history_with_ai() function
prompt += "Provide a 4-5 sentence summary..."  # Longer
prompt += "Provide a 1-2 sentence summary..."  # Shorter
```

### Change Cache Size
```python
# In app/city_history/routes.py
if len(HISTORY_CACHE) > 200:  # More cache
    HISTORY_CACHE.pop(next(iter(HISTORY_CACHE)))
```

### Add Different AI Services
```python
# Replace Claude with OpenAI, Gemini, etc.
def generate_history_with_openai(city, lat, lon):
    # Custom AI integration
    pass
```

## Troubleshooting

**Common Issues:**

- **No history appears**: Check ANTHROPIC_API_KEY environment variable
- **"AI service not configured"**: Set up Claude API key
- **Slow loading**: First request takes 2-3 seconds (normal)
- **Empty responses**: Verify coordinates are in supported region

**Error Messages:**
- "History not available": Location outside supported region or API error
- "Loading...": Normal state while generating first history
- Network errors: Check internet connection and API status

## Future Enhancements

### Planned Features
- Multi-language historical summaries
- Extended regional coverage (global)
- Historical timeline integration
- Wikipedia integration for verification
- User contributions and corrections

### Possible Integrations
- Historical photos and media
- Timeline of significant events
- Cultural significance indicators
- Archaeological information
- Educational resources