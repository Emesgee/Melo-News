"""
News Chat Module - Handle conversations about specific news stories
Supports: OpenAI ChatGPT (primary), Thaura.ai, Claude AI (fallback)
"""
import requests
import os
from flask import Blueprint, jsonify, request
from datetime import datetime

# In-memory conversation storage (in production, use database)
CONVERSATIONS = {}

def get_or_create_conversation(news_id):
    """Get or create a conversation for a news story"""
    if news_id not in CONVERSATIONS:
        CONVERSATIONS[news_id] = {
            'news_id': news_id,
            'messages': [],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
    return CONVERSATIONS[news_id]

def chat_with_openai(messages, context):
    """
    Chat with Thaura AI (PRIMARY SERVICE)
    messages: list of {'role': 'user'/'assistant', 'content': 'text'}
    context: news story context {'title', 'description', 'city', 'lat', 'lon'}
    """
    try:
        api_key = os.getenv('THAURA_API_KEY')
        api_base = os.getenv('THAURA_API_BASE', 'https://backend.thaura.ai/v1')
        model = os.getenv('THAURA_DEFAULT_MODEL', 'thaura')
        
        if not api_key:
            print("DEBUG: THAURA_API_KEY not found in environment")
            return None
        
        print(f"DEBUG: Using Thaura AI (key found, length: {len(api_key)})")
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Build system prompt with news context
        system_prompt = f"""You are a knowledgeable news analyst discussing a specific news story.
        
News Story Context:
- Title: {context.get('title', 'Unknown')}
- Description: {context.get('description', 'Unknown')}
- Location: {context.get('city', 'Unknown')}, Israel-Palestine region
- Coordinates: {context.get('lat')}, {context.get('lon')}

Stay focused on discussing this specific news story. Provide balanced, factual analysis. 
If asked about related topics, connect them back to this news story."""
        
        # Prepare messages for API
        api_messages = [
            {'role': 'system', 'content': system_prompt}
        ] + messages
        
        payload = {
            'model': model,
            'messages': api_messages,
            'temperature': float(os.getenv('THAURA_TEMPERATURE', '0.7')),
            'max_tokens': int(os.getenv('THAURA_MAX_TOKENS', '2048'))
        }
        
        response = requests.post(
            f'{api_base}/chat/completions',
            json=payload,
            headers=headers,
            timeout=int(os.getenv('THAURA_REQUEST_TIMEOUT', '30'))
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                assistant_message = data['choices'][0]['message']['content']
                if assistant_message:
                    return {
                        "status": "success",
                        "message": assistant_message,
                        "service": "thaura"
                    }
        
        print(f"DEBUG: Thaura AI returned status {response.status_code}: {response.text[:200]}")
        return None
            
    except Exception as e:
        print(f"DEBUG: Error chatting with Thaura AI: {e}")
        return None

def chat_with_thaurae(messages, context):
    """
    Chat with Thaura.ai about a specific news story (SECONDARY)
    messages: list of {'role': 'user'/'assistant', 'content': 'text'}
    context: news story context {'title', 'description', 'city', 'lat', 'lon'}
    """
    try:
        api_key = os.getenv('THAURA_AI_API_KEY')
        if not api_key:
            return None
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Build system prompt with news context
        system_prompt = f"""You are a knowledgeable news analyst discussing a specific news story.
        
News Story Context:
- Title: {context.get('title', 'Unknown')}
- Description: {context.get('description', 'Unknown')}
- Location: {context.get('city', 'Unknown')}, Israel-Palestine region
- Coordinates: {context.get('lat')}, {context.get('lon')}

Stay focused on discussing this specific news story. Provide balanced, factual analysis. 
If asked about related topics, connect them back to this news story."""
        
        # Prepare messages for API
        api_messages = [
            {'role': 'system', 'content': system_prompt}
        ] + messages
        
        payload = {
            'model': 'default',
            'messages': api_messages,
            'temperature': 0.7,
            'max_tokens': 500
        }
        
        response = requests.post(
            'https://thaura.ai/api/v1/chat/completions',
            json=payload,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                assistant_message = data['choices'][0].get('message', {}).get('content', '')
                if assistant_message:
                    return {
                        "status": "success",
                        "message": assistant_message,
                        "service": "thaurae"
                    }
        
        return None
            
    except Exception as e:
        print(f"Error chatting with Thaura.ai: {e}")
        return None

def chat_with_claude(messages, context):
    """Fallback to Claude if Thaura.ai is unavailable"""
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return None
        
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        
        system_prompt = f"""You are a knowledgeable news analyst discussing a specific news story.
        
News Story Context:
- Title: {context.get('title', 'Unknown')}
- Description: {context.get('description', 'Unknown')}
- Location: {context.get('city', 'Unknown')}, Israel-Palestine region
- Coordinates: {context.get('lat')}, {context.get('lon')}

Stay focused on discussing this specific news story. Provide balanced, factual analysis."""
        
        # Convert to Claude format
        user_message = messages[-1]['content'] if messages else "Tell me about this news story."
        
        payload = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': 500,
            'system': system_prompt,
            'messages': [
                {'role': 'user', 'content': user_message}
            ]
        }
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            assistant_message = data['content'][0]['text']
            return {
                "status": "success",
                "message": assistant_message,
                "service": "claude"
            }
        
        return None
            
    except Exception as e:
        print(f"Error chatting with Claude: {e}")
        return None

def process_chat_message(news_id, user_message, context):
    """Process a chat message and get AI response"""
    conversation = get_or_create_conversation(news_id)
    
    # Add user message to history
    conversation['messages'].append({
        'role': 'user',
        'content': user_message
    })
    
    # Use Thaura AI only
    print(f"DEBUG: process_chat_message called for news_id={news_id}")
    response = chat_with_thaurae(conversation['messages'], context)
    
    if not response:
        print("DEBUG: Thaura AI chat failed!")
        response = {
            "error": "Chat service unavailable",
            "message": "Unable to process your message. Please check that THAURA_API_KEY is configured."
        }
    
    # Add assistant message to history
    if response.get('status') == 'success':
        conversation['messages'].append({
            'role': 'assistant',
            'content': response['message']
        })
    
    conversation['updated_at'] = datetime.now()
    
    return response
