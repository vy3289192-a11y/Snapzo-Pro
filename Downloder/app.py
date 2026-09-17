from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory
)

from urllib.parse import urlparse, parse_qs

import requests
import os
import re
import yt_dlp
import time
import threading


app = Flask(__name__)

# ==========================================
# ABSOLUTE PATH SETUP FOR LIVE SERVER
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(BASE_DIR, "cookies.txt")

# ==========================================
# DOWNLOAD FOLDER
# ==========================================
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")

os.makedirs(
    DOWNLOAD_FOLDER,
    exist_ok=True
)


# ==========================================
# AUTOMATIC DOWNLOAD FILE CLEANUP
# Files older than 30 minutes are removed.
# ==========================================
CLEANUP_AFTER_SECONDS = 30 * 60
CLEANUP_INTERVAL_SECONDS = 60

def cleanup_old_downloads():
    while True:
        try:
            now = time.time()
            for filename in os.listdir(DOWNLOAD_FOLDER):
                filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                if not os.path.isfile(filepath):
                    continue
                try:
                    if now - os.path.getmtime(filepath) >= CLEANUP_AFTER_SECONDS:
                        os.remove(filepath)
                except (OSError, FileNotFoundError):
                    pass
        except (OSError, FileNotFoundError):
            pass
        time.sleep(CLEANUP_INTERVAL_SECONDS)


# Start cleanup worker once when the Flask process starts.
_cleanup_thread = threading.Thread(
    target=cleanup_old_downloads,
    daemon=True
)
_cleanup_thread.start()


# ==========================================
# YOUTUBE API KEY
# ==========================================

YOUTUBE_API_KEY ="AIzaSyAgxpv5ZcAzAQ7DSwbcr9FBvmzsm9bKsSo"


# ==========================================
# SUPPORTED PLATFORMS
# ==========================================

PLATFORMS = {

    "youtube": [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be"
    ],

    "instagram": [
        "instagram.com",
        "www.instagram.com"
    ],

    "x": [
        "x.com",
        "www.x.com",
        "twitter.com",
        "www.twitter.com"
    ],

    "facebook": [
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "fb.watch"
    ],

    "snapchat": [
        "snapchat.com",
        "www.snapchat.com"
    ]

}


# ==========================================
# DETECT PLATFORM
# ==========================================

def detect_platform(url):

    try:

        parsed = urlparse(url)

        hostname = (
            parsed.netloc
            .lower()
            .split(":")[0]
        )

        for platform, domains in PLATFORMS.items():

            if hostname in domains:

                return platform

        return None

    except Exception:

        return None


# ==========================================
# YOUTUBE VIDEO ID
# ==========================================

def get_youtube_video_id(url):

    try:

        parsed = urlparse(url)

        hostname = (
            parsed.netloc
            .lower()
            .split(":")[0]
        )


        if hostname == "youtu.be":

            video_id = (
                parsed.path
                .strip("/")
                .split("/")[0]
            )

            if video_id:

                return video_id


        if hostname in [
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com"
        ]:

            query = parse_qs(
                parsed.query
            )

            video_id = query.get(
                "v",
                [None]
            )[0]

            if video_id:

                return video_id


            shorts_match = re.match(
                r"^/shorts/([^/?]+)",
                parsed.path
            )

            if shorts_match:

                return shorts_match.group(1)


            embed_match = re.match(
                r"^/embed/([^/?]+)",
                parsed.path
            )

            if embed_match:

                return embed_match.group(1)


        return None

    except Exception:

        return None


# ==========================================
# FORMAT DURATION
# ==========================================

def format_duration(duration):

    if not duration:

        return "Unknown duration"


    match = re.match(
        r"PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?",
        duration
    )


    if not match:

        return "Unknown duration"


    hours = int(
        match.group(1) or 0
    )

    minutes = int(
        match.group(2) or 0
    )

    seconds = int(
        match.group(3) or 0
    )


    if hours > 0:

        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )


    return (
        f"{minutes}:"
        f"{seconds:02d}"
    )


# ==========================================
# YOUTUBE METADATA
# ==========================================

def get_youtube_metadata(url):

    video_id = get_youtube_video_id(
        url
    )


    if not video_id:

        return {
            "success": False,
            "message":
                "Could not find YouTube video ID."
        }


    if not YOUTUBE_API_KEY:

        return {
            "success": False,
            "message":
                "YouTube API key is not configured."
        }


    api_url = (
        "https://www.googleapis.com/"
        "youtube/v3/videos"
    )


    params = {

        "part":
            "snippet,contentDetails",

        "id":
            video_id,

        "key":
            YOUTUBE_API_KEY

    }


    try:

        response = requests.get(
            api_url,
            params=params,
            timeout=10
        )


        data = response.json()


        if response.status_code != 200:

            return {
                "success": False,
                "message":
                    "YouTube API request failed."
            }


        items = data.get(
            "items",
            []
        )


        if not items:

            return {
                "success": False,
                "message":
                    "YouTube video not found."
            }


        item = items[0]


        snippet = item.get(
            "snippet",
            {}
        )


        content_details = item.get(
            "contentDetails",
            {}
        )


        thumbnails = snippet.get(
            "thumbnails",
            {}
        )


        thumbnail = None


        if "maxres" in thumbnails:

            thumbnail = thumbnails[
                "maxres"
            ]["url"]

        elif "high" in thumbnails:

            thumbnail = thumbnails[
                "high"
            ]["url"]

        elif "medium" in thumbnails:

            thumbnail = thumbnails[
                "medium"
            ]["url"]

        elif "default" in thumbnails:

            thumbnail = thumbnails[
                "default"
            ]["url"]


        return {

            "success": True,

            "title":
                snippet.get(
                    "title",
                    "YouTube Video"
                ),

            "duration":
                format_duration(
                    content_details.get(
                        "duration"
                    )
                ),

            "thumbnail":
                thumbnail

        }


    except requests.RequestException:

        return {
            "success": False,
            "message":
                "Could not connect to YouTube."
        }

@app.route("/youtube-mp3")
def youtube_mp3():
    return render_template("youtube-mp3.html")


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# CHECK URL
# ==========================================

@app.route(
    "/api/check-url",
    methods=["POST"]
)
def check_url():

    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({
            "success": False,
            "message":
                "Invalid request."
        }), 400


    url = data.get(
        "url",
        ""
    ).strip()


    if not url:

        return jsonify({
            "success": False,
            "message":
                "Please enter a video URL."
        }), 400


    if not url.startswith(
        ("http://", "https://")
    ):

        return jsonify({
            "success": False,
            "message":
                "Please enter a valid URL."
        }), 400


    platform = detect_platform(
        url
    )


    if not platform:

        return jsonify({
            "success": False,
            "message":
                "This platform is not supported."
        }), 400


    # YouTube metadata only

    if platform == "youtube":

        metadata = get_youtube_metadata(
            url
        )


        if metadata["success"]:

            return jsonify({

                "success": True,

                "platform":
                    platform,

                "message":
                    "YouTube video found successfully.",

                "video": {

                    "title":
                        metadata["title"],

                    "duration":
                        metadata["duration"],

                    "thumbnail":
                        metadata["thumbnail"]

                }

            })


        return jsonify({

            "success": False,

            "message":
                metadata["message"]

        }), 400


    return jsonify({

        "success": True,

        "platform":
            platform,

        "message":
            f"{platform.title()} URL detected successfully.",

        "video": {

            "title":
                "Your video is ready",

            "duration":
                "Available after processing",

            "thumbnail":
                None

        }

    })


# ==========================================
# DOWNLOAD
# ==========================================

@app.route(
    "/api/download",
    methods=["POST"]
)
def download():

    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({

            "success": False,

            "message":
                "Invalid request."

        }), 400


    url = data.get(
        "url",
        ""
    ).strip()


    quality = str(
        data.get(
            "quality",
            "720"
        )
    )


    if not url:

        return jsonify({

            "success": False,

            "message":
                "No URL provided."

        }), 400


    parsed = urlparse(url)


    if parsed.scheme not in [
        "http",
        "https"
    ]:

        return jsonify({

            "success": False,

            "message":
                "Invalid media URL."

        }), 400


    # ======================================
    # CHECK IF AUDIO OR VIDEO IS REQUESTED
    # ======================================
    
    is_audio = quality in [
        "mp3",
        "128",
        "192",
        "320"
    ]


    if is_audio:
        
        ydl_opts = {

            'format': 'bestaudio[ext=m4a]/bestaudio',

            'outtmpl': os.path.join(
                DOWNLOAD_FOLDER,
                '%(title)s.%(ext)s'
            ),

            'restrictfilenames': True,

            'quiet': True,

            'noplaylist': True,
            
            'source_address': '0.0.0.0',
            
            'cookiefile': COOKIE_FILE  # Absolute path for live server

        }

    else:

        if quality not in [
            "720",
            "480",
            "360"
        ]:

            quality = "720"


        ydl_opts = {

            'format': 'b[ext=mp4]/b/best',

            'outtmpl': os.path.join(
                DOWNLOAD_FOLDER,
                '%(title)s.%(ext)s'
            ),

            'restrictfilenames': True,

            'quiet': True,

            'noplaylist': True,
            
            'source_address': '0.0.0.0',
            
            'cookiefile': COOKIE_FILE  # Absolute path for live server

        }


    # ======================================
    # DOWNLOAD LOCALLY TO FORCE BROWSER
    # TO SHOW DIRECT "SAVE AS" DIALOG
    # ======================================

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            # download=True saves the file to your 'downloads' folder first
            info = ydl.extract_info(
                url,
                download=True
            )


            downloaded_path = ydl.prepare_filename(
                info
            )


            filename = os.path.basename(
                downloaded_path
            )


            # This points to your local serve_file route which forces the download
            local_url = f"/files/{filename}"


            return jsonify({

                "success": True,

                "url":
                    local_url,

                "download_url":
                    local_url,

                "message":
                    "Ready for download!"

            })


    except Exception as e:

        return jsonify({

            "success": False,

            "message":
                f"Extraction failed: {str(e)}"

        }), 400


# ==========================================
# SERVE LOCAL FILE
# ==========================================

@app.route(
    "/files/<filename>"
)
def serve_file(filename):

    filename = os.path.basename(
        filename
    )


    return send_from_directory(

        DOWNLOAD_FOLDER,

        filename,

        as_attachment=True

    )


# ==========================================
# PLATFORM PAGES
# ==========================================

@app.route("/youtube")
def youtube_page():
    return render_template("youtube.html")


@app.route("/instagram")
def instagram_page():
    return render_template("instagram.html")


@app.route("/x")
def x_page():
    return render_template("x.html")


@app.route("/snapchat")
def snapchat_page():
    return render_template("snapchat.html")


@app.route("/facebook")
def facebook_page():
    return render_template("facebook.html")

# ==========================================
# LEGAL / INFORMATION PAGES
# ==========================================

@app.route("/privacy")
def privacy_page():
    return render_template("privacy.html")


@app.route("/terms")
def terms_page():
    return render_template("terms.html")


@app.route("/copyright")
def copyright_page():
    return render_template("copyright.html")


@app.route("/disclaimer")
def disclaimer_page():
    return render_template("disclaimer.html")


@app.route("/contact")
def contact_page():
    return render_template("contact.html")


# ==========================================
# ERROR PAGES
# ==========================================

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500

# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
