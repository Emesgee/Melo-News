# News Chat - AI Conversations About Stories

## Overview

The News Chat feature enables users to have AI-powered conversations about individual news stories. Users can ask questions, get context, and explore story details through natural language interaction.

## Key Features

- **🤖 Multi-AI Support**: Thaura.ai primary, Claude fallback
- **💬 Conversational**: Multi-turn conversations with context
- **📱 Responsive**: Works on all devices  
- **⚡ Real-time**: 2-5 second response times
- **🔄 Session History**: Preserves conversations per session

## How to Use

1. **Access**: Click on any story marker on the map
2. **Switch**: Toggle to "Chat" tab in the popup
3. **Ask**: Type questions about the story in natural language
4. **Explore**: Follow up with additional questions
5. **Clear**: Use "Clear Conversation" to reset

## Technical Details

### Components
- **Backend**: `app/city_history/chat_routes.py` - API endpoints and AI integration
- **Frontend**: `NewsChat.js` - React chat interface
- **Styling**: `NewsChat.css` - Professional chat styling

### API Endpoints
```
POST /api/news-chat              # Send chat message
GET /api/news-chat/:id          # Get conversation history
DELETE /api/news-chat/:id       # Clear conversation
```

### AI Configuration
- **Primary**: Thaura.ai with context-aware responses
- **Fallback**: Claude for enhanced reliability
- **Max Tokens**: 500 per response
- **Context**: Story details, location, and conversation history

## Setup Requirements

### Environment Variables
```bash
# Required
THAURA_AI_API_KEY=your_token_here

# Optional (fallback)
ANTHROPIC_API_KEY=your_key_here
```

### Dependencies
All required packages already included in existing setup.

## Example Interactions

### Basic Questions
- "What happened here?"
- "Tell me more about this story"
- "When did this occur?"

### Contextual Analysis
- "How does this relate to recent events?"
- "What's the significance of this location?"
- "Are there any patterns in this area?"

### Follow-up Exploration
- "Can you explain that in more detail?"
- "What are the implications?"
- "How reliable is this information?"

## Features

### Conversation Management
- **History**: Maintains context across multiple questions
- **Limit**: 100 conversations per session (memory-based)
- **Clear**: Reset conversation anytime
- **State**: Preserves chat state when switching tabs

### User Interface
- **Modern Design**: Clean, professional chat interface
- **Loading States**: Animated indicators during AI processing
- **Auto-scroll**: Automatically scrolls to new messages
- **Mobile Friendly**: Responsive design for all screen sizes

### Error Handling
- **API Failures**: Graceful fallback to Claude
- **Network Issues**: User-friendly error messages
- **Rate Limits**: Handles API rate limiting
- **Invalid Input**: Validates user messages

## Performance

### Response Times
- **Typical**: 2-3 seconds
- **Complex queries**: 3-5 seconds
- **Network dependent**: May vary with connection

### Memory Usage
- **Conversations**: Stored in memory per session
- **Limit**: 100 conversations maximum
- **Cleanup**: Automatic oldest-first removal

### Cost Estimates
- **Per message**: ~$0.001-0.005
- **1000 messages/month**: ~$1-5

## Integration

### Map Integration
- Accessible from any story marker popup
- Seamlessly switches between Info and Chat tabs
- Context automatically populated from story data

### Story Context
Chat includes:
- Story title and description
- Location (city, coordinates)
- Timestamp and metadata
- Previous conversation history

## Customization

### Modify Response Length
```python
# In app/city_history/chat_routes.py
MAX_TOKENS = 750  # Longer responses
MAX_TOKENS = 250  # Shorter responses
```

### Change Conversation Limit
```python
# In chat_routes.py
CONVERSATION_LIMIT = 200  # More conversations
CONVERSATION_LIMIT = 50   # Fewer conversations
```

### Adjust AI Personality
Edit the system prompts in the AI integration functions to:
- Change response tone
- Add domain expertise
- Modify conversation style
- Include specific instructions

## Troubleshooting

**Common Issues:**

- **No response**: Check THAURA_AI_API_KEY environment variable
- **Slow responses**: Normal for complex questions (up to 5 seconds)
- **Chat tab missing**: Ensure story has valid data and coordinates
- **Conversation lost**: Normal after page refresh (memory-based storage)

**Error Messages:**
- "API key not configured": Set up Thaura.ai API key
- "Failed to get response": Check internet connection and API status
- "Please try again": Temporary error, retry message

## Security

- **API Keys**: Stored as environment variables only
- **User Input**: Validated and sanitized
- **Context**: Only story-related data shared with AI
- **Sessions**: Isolated per user session