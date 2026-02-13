import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './NewsChat.css';

const API_URL = process.env.REACT_APP_API_URL || '/api';

const NewsChat = ({ newsId, newsData }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch conversation history on mount
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get(
          `${API_URL}/api/news-chat/${newsId}`
        );
        setMessages(response.data.messages || []);
      } catch (err) {
        console.log('No conversation history yet');
      }
    };

    fetchHistory();
  }, [newsId]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!input.trim()) return;

    // Add user message to chat immediately
    const userMessage = {
      role: 'user',
      content: input
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(
        `${API_URL}/api/news-chat`,
        {
          news_id: newsId,
          message: input,
          context: {
            title: newsData?.title || 'News Story',
            description: newsData?.description || '',
            city: newsData?.city || '',
            lat: newsData?.lat,
            lon: newsData?.lon
          }
        }
      );

      if (response.data.status === 'success') {
        const assistantMessage = {
          role: 'assistant',
          content: response.data.message
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else if (response.data.error) {
        setError(response.data.error);
        // Remove last user message if there was an error
        setMessages(prev => prev.slice(0, -1));
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Failed to get response';
      setError(errorMsg);
      // Remove last user message on error
      setMessages(prev => prev.slice(0, -1));
      console.error('Chat error:', err);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      await axios.delete(`${API_URL}/api/news-chat/${newsId}`);
      setMessages([]);
      setError('');
    } catch (err) {
      setError('Failed to clear conversation');
      console.error('Clear error:', err);
    }
  };

  return (
    <div className="news-chat-container">
      <div className="chat-header">
        <h3>Discussion</h3>
        {messages.length > 0 && (
          <button 
            className="clear-btn"
            onClick={clearChat}
            title="Clear conversation"
          >
            ✕
          </button>
        )}
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <p>Ask about this story...</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`chat-message chat-${msg.role}`}>
              <div className="message-role">
                {msg.role === 'user' ? '🧑' : '🤖'}
              </div>
              <div className="message-content">
                {msg.content}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="chat-message chat-assistant">
            <div className="message-role">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="chat-error">
          ⚠️ {error}
        </div>
      )}

      <form onSubmit={handleSendMessage} className="chat-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about this story..."
          disabled={loading}
          className="chat-input"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="chat-send-btn"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default NewsChat;
