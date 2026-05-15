from flask import Flask, render_template, jsonify, request, redirect, session, url_for
from ytmusicapi import YTMusic
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import os

app = Flask(__name__)
app.secret_key = "any-random-string-for-session" # Zaruri hai session ke liye

yt = YTMusic()

SPOTIFY_CLIENT_ID = '46ce8700cbcb4a739423feab1f207455'
SPOTIFY_CLIENT_SECRET = 'aae5cab476fd44719ba0fdd3c0dac53f'
# Is link ko apne asli Render link se replace kar sakte hain
REDIRECT_URI = 'https://' + os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost:5000') + '/callback'

# 1. Login Route: User ko Spotify ke login page par bhejne ke liye
@app.route('/login')
def login():
    scope = "user-library-read user-top-read"
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, 
                            redirect_uri=REDIRECT_URI, scope=scope)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# 2. Callback Route: Login ke baad wapas aane ke liye
@app.route('/callback')
def callback():
    sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, 
                            redirect_uri=REDIRECT_URI)
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for('index'))

# 3. Personal Music API: User ke taste ke gaane nikalna
@app.route('/api/user_music')
def user_music():
    if "token_info" not in session:
        return jsonify({"success": False, "message": "Not logged in"})
    
    try:
        token_info = session.get("token_info")
        sp_user = spotipy.Spotify(auth=token_info['access_token'])
        # User ke top 6 gaane nikal rahe hain
        results = sp_user.current_user_top_tracks(limit=6, time_range='short_term')
        
        tracks = []
        for track in results['items']:
            tracks.append({
                "title": track['name'],
                "artist": track['artists'][0]['name'],
                "thumb": track['album']['images'][0]['url']
            })
        return jsonify({"success": True, "tracks": tracks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- Purana Search aur Home API (Waisa hi rahega) ---
@app.route('/')
def index():
    logged_in = "token_info" in session
    return render_template('index.html', logged_in=logged_in)

@app.route('/api/search')
def search_music():
    # ... (Pichla Spotify search code yahan rahega) ...
    sp_public = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
    query = request.args.get('q')
    results = sp_public.search(q=query, limit=10, type='track', market='IN')
    # ... (Baki logic wahi hai) ...
    return jsonify({"success": True, "results": []}) # (Cleaned results yahan aayenge)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
