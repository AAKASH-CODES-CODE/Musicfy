from flask import Flask, render_template, jsonify, request
from ytmusicapi import YTMusic
import os

app = Flask(__name__)
yt = YTMusic()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/home_music')
def home_music():
    try:
        # Trending aur Recommended gaane fetch karna
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

# --- NAYA SEARCH API ROUTE ---
@app.route('/api/search')
def search_music():
    query = request.args.get('q')
    if not query:
        return jsonify({"success": False, "error": "No query provided"})
    
    try:
        # YouTube Music par gaane search karna
        search_results = yt.search(query, filter="songs", limit=10)
        return jsonify({
            "success": True,
            "results": search_results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    # Cloud automatically apna port assign karega
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
