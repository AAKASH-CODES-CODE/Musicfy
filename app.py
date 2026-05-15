from flask import Flask, render_template, jsonify, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import os
import time
import requests as req
import re
from datetime import datetime
from dotenv import load_dotenv
from ytmusicapi import YTMusic  # YouTube Music API

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-to-a-random-secret")

# YTMusic instance
yt = YTMusic(location="IN")

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:5000/callback")

def get_public_client():
    try:
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        ))
    except Exception:
        return None

def get_user_client():
    token_info = session.get("token_info")
    if not token_info:
        return None

    now = int(time.time())
    is_expired = token_info.get("expires_at", 0) - now < 60

    if is_expired:
        sp_oauth = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope="user-library-read user-top-read user-read-recently-played"
        )
        try:
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
            session["token_info"] = token_info
        except Exception:
            session.clear()
            return None

    return spotipy.Spotify(auth=token_info["access_token"])


@app.route("/")
def index():
    logged_in = "token_info" in session
    user_name = session.get("user_name", "")
    user_image = session.get("user_image", "")
    now_hour = datetime.now().hour
    return render_template("index.html", logged_in=logged_in, user_name=user_name,
                           user_image=user_image, now_hour=now_hour)


@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-library-read user-top-read user-read-recently-played"
    )
    return redirect(sp_oauth.get_authorize_url())


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return redirect(url_for("index"))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("index"))

    sp_oauth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-library-read user-top-read user-read-recently-played"
    )
    session.clear()
    try:
        token_info = sp_oauth.get_access_token(code)
        session["token_info"] = token_info

        sp_user = spotipy.Spotify(auth=token_info["access_token"])
        profile = sp_user.current_user()
        session["user_name"] = profile.get("display_name", "User")
        images = profile.get("images", [])
        session["user_image"] = images[0]["url"] if images else ""
    except Exception:
        pass

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/user_music")
def user_music():
    sp = get_user_client()
    if not sp:
        return jsonify({"success": False, "message": "Not logged in"})

    try:
        results = sp.current_user_top_tracks(limit=8, time_range="short_term")
        tracks = []
        for track in results["items"]:
            images = track["album"]["images"]
            thumb = images[0]["url"] if images else ""
            tracks.append({
                "title": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "thumb": thumb,
                "id": track["id"],
                "duration_ms": track["duration_ms"],
                "album": track["album"]["name"]
            })
        return jsonify({"success": True, "tracks": tracks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/recent_tracks")
def recent_tracks():
    sp = get_user_client()
    if not sp:
        return jsonify({"success": False, "message": "Not logged in"})

    try:
        results = sp.current_user_recently_played(limit=6)
        tracks = []
        seen = set()
        for item in results["items"]:
            track = item["track"]
            if track["id"] in seen:
                continue
            seen.add(track["id"])
            images = track["album"]["images"]
            thumb = images[0]["url"] if images else ""
            tracks.append({
                "title": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "thumb": thumb,
                "id": track["id"]
            })
        return jsonify({"success": True, "tracks": tracks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/home_music")
def home_music():
    sp = get_public_client()
    if not sp:
        return jsonify({"success": False, "error": "Spotify not configured"})

    try:
        album_results = sp.search(q="new album 2024", type="album", limit=8, market="US")
        start_listening = []
        for album in album_results["albums"]["items"]:
            images = album["images"]
            thumb = images[0]["url"] if images else ""
            start_listening.append({
                "title": album["name"],
                "artist": ", ".join(a["name"] for a in album["artists"]),
                "thumb": thumb,
                "id": album["id"],
                "type": "album"
            })

        playlist_results = sp.search(q="Top Hits Hindi India", type="playlist", limit=10, market="US")
        playlists = playlist_results["playlists"]["items"]
        recommended = []
        for pl in playlists:
            if not pl:
                continue
            images = pl.get("images", [])
            thumb = images[0]["url"] if images else ""
            recommended.append({
                "title": pl["name"],
                "thumb": thumb,
                "id": pl["id"],
                "owner": pl["owner"]["display_name"]
            })

        trending_results = sp.search(q="Bollywood hits 2024", type="track", limit=6, market="US")
        trending = []
        for track in trending_results["tracks"]["items"]:
            images = track["album"]["images"]
            thumb = images[0]["url"] if images else ""
            trending.append({
                "title": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "thumb": thumb,
                "id": track["id"]
            })

        return jsonify({
            "success": True,
            "start_listening": start_listening,
            "recommended": recommended,
            "trending": trending
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def _spotify_search(access_token, query, search_type, limit):
    """Direct HTTP call to Spotify — bypasses spotipy quirks completely."""
    r = req.get(
        "https://api.spotify.com/v1/search",
        params={"q": query, "type": search_type, "limit": limit, "market": "US"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=8
    )
    r.raise_for_status()
    return r.json()


# --- YOUTUBE MUSIC SEARCH API START ---
@app.route("/api/search")
def search_music():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": False, "error": "No query provided"})

    try:
        # Pura search ab seedha YouTube Music se hoga (bina login ke chalega)
        search_results = yt.search(query, limit=20)
        
        tracks = []
        artists = []
        
        for item in search_results:
            result_type = item.get("resultType")
            
            # Gaano aur videos ko as a track dikhayenge
            if result_type in ["song", "video"]:
                thumbnails = item.get("thumbnails", [{"url": "https://via.placeholder.com/55"}])
                thumb = thumbnails[-1]["url"] if thumbnails else "https://via.placeholder.com/55"
                
                artists_list = item.get("artists", [])
                artist_name = ", ".join(a["name"] for a in artists_list if "name" in a)
                
                tracks.append({
                    "title": item.get("title"),
                    "artist": artist_name,
                    "thumb": thumb,
                    "id": item.get("videoId"),
                    "type": "track"
                })
            
            # Artists ko alag section me dikhayenge
            elif result_type == "artist":
                thumbnails = item.get("thumbnails", [{"url": "https://via.placeholder.com/100"}])
                thumb = thumbnails[-1]["url"] if thumbnails else "https://via.placeholder.com/100"
                
                artists.append({
                    "name": item.get("artist"),
                    "thumb": thumb,
                    "id": item.get("browseId"),
                    "followers": 0,
                    "type": "artist"
                })

        return jsonify({
            "success": True,
            "results": tracks[:15],  # Top 15 gaane
            "artists": artists[:4]   # Top 4 artists
        })

    except Exception as e:
        print(f"YT Search Error: {e}")
        return jsonify({"success": False, "error": str(e)})
# --- YOUTUBE MUSIC SEARCH API END ---


@app.route("/api/saved_tracks")
def saved_tracks():
    sp = get_user_client()
    if not sp:
        return jsonify({"success": False, "message": "Not logged in"})
    try:
        results = sp.current_user_saved_tracks(limit=20)
        tracks = []
        for item in results["items"]:
            track = item["track"]
            images = track["album"]["images"]
            thumb = images[0]["url"] if images else ""
            tracks.append({
                "title": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "thumb": thumb,
                "id": track["id"],
                "duration_ms": track["duration_ms"],
                "album": track["album"]["name"]
            })
        return jsonify({"success": True, "tracks": tracks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# --- SMART AUDIO BRIDGE START (NOW USING YT-DLP) ---
import yt_dlp

@app.route("/api/get_audio")
def get_audio():
    title = request.args.get("title", "")
    artist = request.args.get("artist", "")
    
    if not title:
        return jsonify({"success": False, "error": "No title provided"})
        
    # Clean title to remove brackets like (From "Movie") which break search
    clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title).strip()
    first_artist = artist.split(',')[0].strip() if artist else ""
    
    query = f"{clean_title} {first_artist}".strip()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'default_search': 'ytsearch',
        'extract_flat': False
    }

    try:
        # Pura backend search ab yt-dlp ke through hoga
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Hum ytsearch1 use kar rahe hain matlab sirf 1st result layega
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                audio_url = info['entries'][0]['url']
                return jsonify({"success": True, "audio_url": audio_url})
            else:
                return jsonify({"success": False, "error": "Audio link not found"})

    except Exception as e:
        print(f"Audio Fetch Error: {e}")
        return jsonify({"success": False, "error": str(e)})
# --- SMART AUDIO BRIDGE END ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

