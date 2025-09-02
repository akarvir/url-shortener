import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [url, setUrl] = useState('');
  const [shortenedUrl, setShortenedUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const api = axios.create({
    baseURL: ""  // Use relative URLs since we're served from the same server
  });
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);           
    setError('');
    setShortenedUrl('');
    setCopied(false);

    try {
      const response = await api.post('/api/shorten', { url });
      setShortenedUrl(response.data.short_url);
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while shortening the URL');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shortenedUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const reset = () => {
    setUrl('');
    setShortenedUrl('');
    setError('');
    setCopied(false);
  };

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>🔗 URL Shortener (Not!)</h1>
          <p>Transform your long URLs into even longer links</p>
        </header>

        <div className="card">
          {!shortenedUrl ? (
            <form onSubmit={handleSubmit} className="url-form">
              <div className="input-group">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Enter your URL here..."
                  className="url-input"
                  required
                />
                <button 
                  type="submit" 
                  className="shorten-btn"
                  disabled={loading || !url.trim()}
                >
                  {loading ? (
                    <span className="loading-spinner"></span>
                  ) : (
                    'Shorten'
                  )}
                </button>
              </div>
              {error && <div className="error-message">{error}</div>}
            </form>
          ) : (
            <div className="result">
              <div className="success-icon">✅</div>
              <h3>Your elongated URL is ready!</h3>
              
              <div className="url-result">
                <input
                  type="text"
                  value={shortenedUrl}
                  readOnly
                  className="result-input"
                />
                <button 
                  onClick={copyToClipboard}
                  className={`copy-btn ${copied ? 'copied' : ''}`}
                >
                  {copied ? '✓ Copied!' : '📋 Copy'}
                </button>
              </div>

              <div className="original-url">
                <small>Original: <a href={url} target="_blank" rel="noopener noreferrer">{url}</a></small>
              </div>

              <button onClick={reset} className="new-url-btn">
                Create Another elongated URL
              </button>
            </div>
          )}
        </div>

        <footer className="footer">
          <p>Built for the love of the game</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
