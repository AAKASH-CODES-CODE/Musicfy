from flask import Flask, render_template, jsonify, request
from ytmusicapi import YTMusic
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

app = Flask(__name__)

# YouTube API (Home screen ke gaano ke liye)
yt = YTMusic()

# Spotify API (Super-Accurate Search ke liye)
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID', '46ce8700cbcb4a739423feab1f207455')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET', 'aae5cab476fd44719ba0fdd3c0dac53f')

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/home_music')
def home_music():
    try:
        # Trending aur Recommended gaane fetch karna (YouTube se)
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

# --- NAYA SPOTIFY SEARCH API ROUTE ---
@app.route('/api/search')
def search_music():
    query = request.args.get('q')
    if not query:
        return jsonify({"success": False, "error": "No query provided"})
    
    try:
        # market='IN' lagane se Indian hits sabse upar aayenge!
        results = sp.search(q=query, limit=10, type='track', market='IN')
        tracks = results['tracks']['items']
        
        cleaned_results = []
        for track in tracks:
            title = track['name']
            artists = [{"name": artist['name']} for artist in track['artists']]
            
            if track['album']['images']:
                thumb_url = track['album']['images'][0]['url']
            else:
                thumb_url = "https://via.placeholder.com/55"
                
            cleaned_results.append({
                "title": title,
                "artists": artists,
                "thumbnails": [{"url": thumb_url}],
                "id": track['id']
            })
            
        return jsonify({
            "success": True,
            "results": cleaned_results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    # Cloud automatically apna port assign karega
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
