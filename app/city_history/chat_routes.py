"""
News Chat Routes - API endpoints for news discussion chat
"""
from flask import Blueprint, jsonify, request
from .chat import process_chat_message, get_or_create_conversation

news_chat_bp = Blueprint('news_chat', __name__, url_prefix='/api')

@news_chat_bp.route('/news-chat', methods=['POST'])
def send_chat_message():
    """
    Send a chat message about a specific news story
    Expected JSON:
    {
        "news_id": "12345",
        "message": "What are the implications of this?",
        "context": {
            "title": "News Title",
            "description": "News description",
            "city": "Jerusalem",
            "lat": 31.9,
            "lon": 35.2
        }
    }
    """
    try:
        data = request.get_json()
        
        news_id = data.get('news_id')
        message = data.get('message', '').strip()
        context = data.get('context', {})
        
        if not news_id:
            return jsonify({"error": "news_id is required"}), 400
        
        if not message:
            return jsonify({"error": "message is required"}), 400
        
        if not context:
            return jsonify({"error": "context is required"}), 400
        
        # Process the message
        response = process_chat_message(news_id, message, context)
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in news-chat endpoint: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@news_chat_bp.route('/news-chat/<news_id>', methods=['GET'])
def get_conversation_history(news_id):
    """
    Get conversation history for a news story
    """
    try:
        conversation = get_or_create_conversation(news_id)
        
        return jsonify({
            "news_id": news_id,
            "messages": conversation['messages'],
            "created_at": conversation['created_at'].isoformat(),
            "updated_at": conversation['updated_at'].isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@news_chat_bp.route('/news-chat/<news_id>', methods=['DELETE'])
def clear_conversation(news_id):
    """
    Clear conversation history for a news story
    """
    try:
        from .chat import CONVERSATIONS
        
        if news_id in CONVERSATIONS:
            del CONVERSATIONS[news_id]
            return jsonify({"message": "Conversation cleared"}), 200
        
        return jsonify({"message": "Conversation not found"}), 404
        
    except Exception as e:
        print(f"Error clearing conversation: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
