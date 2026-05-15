from flask import Flask, render_template, jsonify, request, redirect, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-to-a-random-secret")

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
        # FIX: new_releases() is restricted — use album search instead
        album_results = sp.search(q="new album 2024", type="album", limit=8)
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

        playlist_results = sp.search(q="Top Hits Hindi India", type="playlist", limit=10)
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

        # FIX: removed market="IN" — causes 400 error
        trending_results = sp.search(q="Bollywood hits 2024", type="track", limit=6)
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


@app.route("/api/search")
def search_music():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": False, "error": "No query provided"})

    sp = get_public_client()
    if not sp:
        return jsonify({"success": False, "error": "Spotify not configured"})

    try:
        # FIX: separate calls per type — avoids market=None 400 error
        track_results = sp.search(q=query, limit=15, type="track")
        artist_results = sp.search(q=query, limit=4, type="artist")

        tracks = []
        for track in track_results["tracks"]["items"]:
            images = track["album"]["images"]
            thumb = images[0]["url"] if images else ""
            tracks.append({
                "title": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "thumb": thumb,
                "id": track["id"],
                "duration_ms": track["duration_ms"],
                "album": track["album"]["name"],
                "type": "track"
            })

        artists = []
        for artist in artist_results["artists"]["items"]:
            images = artist.get("images", [])
            thumb = images[0]["url"] if images else ""
            artists.append({
                "name": artist["name"],
                "thumb": thumb,
                "id": artist["id"],
                "followers": artist.get("followers", {}).get("total", 0),
                "type": "artist"
            })

        return jsonify({
            "success": True,
            "results": tracks,
            "artists": artists
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
