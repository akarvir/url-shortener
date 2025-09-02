from flask import Flask, request, jsonify, redirect, send_from_directory
from flask_cors import CORS, cross_origin
from supabase import create_client, Client
import string
import random
import validators
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app,origins=["*"])


# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize database table
def init_db():
    """Create the urls table if it doesn't exist"""
    try:
        # Check if table exists by trying to select from it
        result = supabase.table('urls').select('id').limit(1).execute()
        print("✅ Table 'urls' already exists")
    except Exception as e:
        print("❌ Table 'urls' doesn't exist. Please create it in Supabase dashboard.")
        print("📋 SQL to create the table:")
        print("""
CREATE TABLE urls (
    id SERIAL PRIMARY KEY,
    original_url TEXT NOT NULL,
    short_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    click_count INTEGER DEFAULT 0
);

-- Create index for faster lookups
CREATE INDEX idx_urls_short_code ON urls(short_code);
        """)

def generate_short_code(length=6):
    """Generate a random short code"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_unique_short_code():
    """Generate a unique short code that doesn't exist in database"""
    max_attempts = 10
    for _ in range(max_attempts):
        short_code = generate_short_code()
        try:
            # Check if short_code already exists
            result = supabase.table('urls').select('id').eq('short_code', short_code).execute()
            print("Supabase response:", result.data)
            if len(result.data) == 0:
                return short_code
        except Exception as e:
            print(f"Error checking short code: {e}")
            continue
    
    # If we can't find a unique code, use a longer one
    return generate_short_code(8)

@app.route('/api/shorten', methods=['POST'])
@cross_origin(supports_credentials=True)
def shorten_url():
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        original_url = data['url']
        
        # Validate URL
        if not validators.url(original_url):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Check if URL already exists
        existing_result = supabase.table('urls').select('short_code').eq('original_url', original_url).execute()
        
        if existing_result.data:
            # URL already exists, return existing short code
            short_code = existing_result.data[0]['short_code']
        else:
            # Generate new short code and insert
            short_code = get_unique_short_code()
            insert_result = supabase.table('urls').insert({
                'original_url': original_url,
                'short_code': short_code,
                'click_count': 0
            }).execute()
            
            if not insert_result.data:
                return jsonify({'error': 'Failed to create short URL'}), 500
        
        # Return the shortened URL - use environment variable for production or request host
        base_url = os.getenv('BASE_URL', request.host_url.rstrip('/'))
        short_url = f"{base_url}/{short_code}"
        
        return jsonify({
            'original_url': original_url,
            'short_url': short_url,
            'short_code': short_code
        })
        
    except Exception as e:
        print(f"Error in shorten_url: {e}")
        return jsonify({'error': 'Internal server error'}), 500



@app.route('/api/stats/<short_code>')
def get_stats(short_code):
    try:
        result = supabase.table('urls').select('original_url, click_count, created_at').eq('short_code', short_code).execute()
        
        if result.data:
            data = result.data[0]
            return jsonify({
                'short_code': short_code,
                'original_url': data['original_url'],
                'click_count': data['click_count'],
                'created_at': data['created_at']
            })
        else:
            return jsonify({'error': 'URL not found'}), 404
            
    except Exception as e:
        print(f"Error in get_stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health')
def health_check():
    try:
        # Test Supabase connection
        result = supabase.table('urls').select('id').limit(1).execute()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'supabase': 'operational'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

@app.route('/api/recent', methods=['GET'])
def get_recent_urls():
    """Get recently created URLs (optional endpoint for dashboard)"""
    try:
        limit = request.args.get('limit', 10, type=int)
        result = supabase.table('urls').select('short_code, original_url, click_count, created_at').order('created_at', desc=True).limit(limit).execute()
        
        return jsonify({
            'urls': result.data,
            'total': len(result.data)
        })
        
    except Exception as e:
        print(f"Error in get_recent_urls: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@app.route('/<short_code>')
def redirect_to_url(short_code):
    try:
        # Only consider short codes up to length 10 (avoid catching static files)
        if '.' in short_code or len(short_code) > 10:
            return send_from_directory(app.static_folder, 'index.html')

        # Look up short code in Supabase
        result = supabase.table('urls').select('original_url, click_count').eq('short_code', short_code).execute()
        
        if result.data:
            original_url = result.data[0]['original_url']
            current_count = result.data[0]['click_count']

            # Increment click count
            supabase.table('urls').update({
                'click_count': current_count + 1
            }).eq('short_code', short_code).execute()

            return redirect(original_url)
        else:
            return jsonify({'error': 'Short code not found'}), 404

    except Exception as e:
        print(f"Error in redirect_to_url({short_code}): {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Serve React App (this should be LAST to catch all non-API routes)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    # If it's an API route, let it be handled by the API endpoints above
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    
    # If it's a short code (not a file), handle the redirect
    if path and '.' not in path and len(path) <= 10:
        # Check if it's a valid short code first
        try:
            result = supabase.table('urls').select('original_url, click_count').eq('short_code', path).execute()
            if result.data:
                original_url = result.data[0]['original_url']
                current_count = result.data[0]['click_count']
                
                # Increment click count
                supabase.table('urls').update({
                    'click_count': current_count + 1
                }).eq('short_code', path).execute()
                
                return redirect(original_url)
        except Exception as e:
            print(f"Error checking short code {path}: {e}")
    
    # For everything else, serve React app files
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    print("🚀 Starting URL Shortener with Supabase...")
    print(f"🔗 Supabase URL: {SUPABASE_URL}")
    
    # Initialize database
    init_db()
    
    # Get port from environment variable (for cloud deployments) or default to 3000
    port = int(os.getenv('PORT', 3000))
    debug = os.getenv('FLASK_ENV') != 'production'
    
    print(f"✅ Server starting on port {port}")
    app.run(debug=debug, host='0.0.0.0', port=port)