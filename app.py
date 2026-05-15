from flask import Flask, render_template, jsonify, request, redirect, session, url_for
from ytmusicapi import YTMusic
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import os

app = Flask(__name__)
app.secret_key = "musicfy-super-secret-key"

yt = YTMusic()

SPOTIFY_CLIENT_ID = '46ce8700cbcb4a739423feab1f207455'
SPOTIFY_CLIENT_SECRET = 'aae5cab476fd44719ba0fdd3c0dac53f'

# EXACT RENDER LINK (Isse login pakka kaam karega)
REDIRECT_URI = 'https://musicfy-adze.onrender.com/callback'

# Global Search ke liye Spotify
sp_public = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

@app.route('/')
def index():
    logged_in = "token_info" in session
    return render_template('index.html', logged_in=logged_in)

@app.route('/login')
def login():
    scope = "user-library-read user-top-read"
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, 
                            redirect_uri=REDIRECT_URI, scope=scope)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, 
                            redirect_uri=REDIRECT_URI)
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear() # User ko disconnect karne ke liye
    return redirect(url_for('index'))

@app.route('/api/user_music')
def user_music():
    if "token_info" not in session:
        return jsonify({"success": False, "message": "Not logged in"})
    
    try:
        token_info = session.get("token_info")
        sp_user = spotipy.Spotify(auth=token_info['access_token'])
        # User ke top 6 gaane
        results = sp_user.current_user_top_tracks(limit=6, time_range='short_term')
        
        tracks = []
        for track in results['items']:
            thumb = track['album']['images'][0]['url'] if track['album']['images'] else "https://via.placeholder.com/150"
            tracks.append({
                "title": track['name'],
                "artist": track['artists'][0]['name'],
                "thumb": thumb
            })
        return jsonify({"success": True, "tracks": tracks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/home_music')
def home_music():
    try:
        charts = yt.get_charts(country='IN')
        trending_videos = charts.get('videos', {}).get('items', [])[:4]
        recommended_songs = yt.search("haryanvi pop hits", filter="songs", limit=4)
        
        return jsonify({
            "success": True,
            "start_listening": trending_videos,
            "recommended": recommended_songs
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/search')
def search_music():
    query = request.args.get('q')
    if not query:
        return jsonify({"success": False, "error": "No query provided"})
    
    try:
        # PURA SEARCH LOGIC (Ab kachra result nahi aayega)
        results = sp_public.search(q=query, limit=10, type='track', market='IN')
        tracks = results['tracks']['items']
        
        cleaned_results = []
        for track in tracks:
            thumb = track['album']['images'][0]['url'] if track['album']['images'] else "https://via.placeholder.com/55"
            cleaned_results.append({
                "title": track['name'],
                "artists": [{"name": artist['name']} for artist in track['artists']],
                "thumbnails": [{"url": thumb}],
                "id": track['id']
            })
            
        return jsonify({
            "success": True,
            "results": cleaned_results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
