from flask import Flask, render_template, jsonify, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import os
import time
import requests as req
import re
from datetime import datetime
from dotenv import load_dotenv
from ytmusicapi import YTMusic  # NAYA: YouTube Music import kiya

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-to-a-random-secret")

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


# --- JIOSAAVN SEARCH API START ---
@app.route("/api/search")
def search_music():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": False, "error": "No query provided"})

    try:
        # JioSaavn ka Unofficial Autocomplete API
        url = f"https://www.jiosaavn.com/api.php?__call=autocomplete.get&query={query}&_format=json&_marker=0&ctx=web6dot0"
        response = req.get(url, timeout=8)
        data = response.json()

        tracks = []
        artists = []

        # 1. Gaane (Songs) nikalna
        if "songs" in data and "data" in data["songs"]:
            for song in data["songs"]["data"]:
                # JioSaavn choti photo deta hai (50x50), hum use HD (500x500) me convert kar rahe hain
                thumb = song.get("image", "").replace("50x50", "500x500")
                
                # HTML entities (jaise &quot;) ko theek karna
                title = song.get("title", "").replace("&quot;", '"')
                singers = song.get("more_info", {}).get("singers", "Unknown Artist")
                
                tracks.append({
                    "title": title,
                    "artist": singers,
                    "thumb": thumb,
                    "id": song.get("id"), # Ye ID aage Music Player me kaam aayegi
                    "type": "track"
                })

        # 2. Artists nikalna (Agar kisi ne Arijit Singh search kiya)
        if "topquery" in data and "data" in data["topquery"]:
            for item in data["topquery"]["data"]:
                if item.get("type") == "artist":
                    thumb = item.get("image", "").replace("50x50", "500x500")
                    artists.append({
                        "name": item.get("title", "").replace("&quot;", '"'),
                        "thumb": thumb,
                        "id": item.get("id"),
                        "followers": 0, # JioSaavn yahan followers count nahi deta
                        "type": "artist"
                    })

        return jsonify({
            "success": True,
            "results": tracks[:15],  # Top 15 results
            "artists": artists[:4]   # Top 4 artists
        })

    except Exception as e:
        print(f"JioSaavn Search Error: {e}")
        return jsonify({"success": False, "error": "Search API failed"})
# --- JIOSAAVN SEARCH API END ---


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

# --- SMART AUDIO BRIDGE START ---
@app.route("/api/get_audio")
def get_audio():
    title = request.args.get("title", "")
    artist = request.args.get("artist", "")
    
    if not title:
        return jsonify({"success": False, "error": "No title provided"})
        
    # Clean title to remove brackets like (From "Movie") which break search
    clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title).strip()
    # Use only first artist name to simplify search
    first_artist = artist.split(',')[0].strip() if artist else ""
    
    query = f"{clean_title} {first_artist}".strip()
    
    try:
        # Backend proxy: Browser ki jagah server gaana layega (Bypasses CORS & ID issues)
        search_url = f"https://saavn.dev/api/search/songs?query={query}"
        res = req.get(search_url, timeout=10).json()
        
        if res.get("success") and res.get("data", {}).get("results"):
            # Pehla result pakdo
            song = res["data"]["results"][0]
            download_urls = song.get("downloadUrl", [])
            
            if download_urls:
                # Sabse high quality (last item) wala link nikalo
                audio_url = download_urls[-1]["url"]
                return jsonify({"success": True, "audio_url": audio_url})
                
        # If specific search fails, try only title
        search_url = f"https://saavn.dev/api/search/songs?query={clean_title}"
        res = req.get(search_url, timeout=10).json()
        if res.get("success") and res.get("data", {}).get("results"):
            song = res["data"]["results"][0]
            download_urls = song.get("downloadUrl", [])
            if download_urls:
                audio_url = download_urls[-1]["url"]
                return jsonify({"success": True, "audio_url": audio_url})

        return jsonify({"success": False, "error": "Audio link not found"})
        
    except Exception as e:
        print(f"Audio Fetch Error: {e}")
        return jsonify({"success": False, "error": str(e)})
# --- SMART AUDIO BRIDGE END ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
