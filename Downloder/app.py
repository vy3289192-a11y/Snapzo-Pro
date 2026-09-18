from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory
)

from urllib.parse import urlparse

import os
import time
import threading
import yt_dlp


app = Flask(__name__)


# ==========================================
# ABSOLUTE PATH SETUP
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
                filepath = os.path.join(
                    DOWNLOAD_FOLDER,
                    filename
                )

                if not os.path.isfile(filepath):
                    continue

                try:
                    if (
                        now - os.path.getmtime(filepath)
                        >= CLEANUP_AFTER_SECONDS
                    ):
                        os.remove(filepath)

                except (OSError, FileNotFoundError):
                    pass

        except (OSError, FileNotFoundError):
            pass

        time.sleep(CLEANUP_INTERVAL_SECONDS)


_cleanup_thread = threading.Thread(
    target=cleanup_old_downloads,
    daemon=True
)

_cleanup_thread.start()


# ==========================================
# SUPPORTED PLATFORMS
# ==========================================

PLATFORMS = {

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
# FORMAT DURATION
# ==========================================

def format_duration(seconds):

    if seconds is None:
        return "Unknown duration"

    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "Unknown duration"

    if seconds < 0:
        return "Unknown duration"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"


# ==========================================
# GET VIDEO METADATA
# Used only for supported non-video-host pages.
# ==========================================

def get_video_metadata(url):

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "extract_flat": False,
    }

    # Use cookies only when the file actually exists.
    if os.path.isfile(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

        if not info:
            return {
                "success": False,
                "message": "Could not read video information."
            }

        title = (
            info.get("title")
            or info.get("fulltitle")
            or "Video"
        )

        thumbnail = info.get("thumbnail")

        duration = format_duration(
            info.get("duration")
        )

        return {
            "success": True,
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


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
            "message": "Invalid request."
        }), 400


    url = data.get(
        "url",
        ""
    ).strip()


    if not url:

        return jsonify({
            "success": False,
            "message": "Please enter a video URL."
        }), 400


    if not url.startswith(
        ("http://", "https://")
    ):

        return jsonify({
            "success": False,
            "message": "Please enter a valid URL."
        }), 400


    platform = detect_platform(url)


    if not platform:

        return jsonify({
            "success": False,
            "message": "This platform is not supported."
        }), 400


    # Read title, duration and thumbnail before download.
    metadata = get_video_metadata(url)


    if metadata["success"]:

        return jsonify({

            "success": True,

            "platform": platform,

            "message":
                f"{platform.title()} video found successfully.",

            "video": {

                "title":
                    metadata["title"],

                "duration":
                    metadata["duration"],

                "thumbnail":
                    metadata["thumbnail"]

            }

        })


    # Metadata can fail for private/login-protected content,
    # but the URL itself can still be accepted for processing.
    return jsonify({

        "success": True,

        "platform": platform,

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
    # AUDIO / VIDEO OPTIONS
    # ======================================

    is_audio = quality in [
        "mp3",
        "128",
        "192",
        "320"
    ]


    if is_audio:

        ydl_opts = {

            "format":
                "bestaudio",

            "outtmpl":
                os.path.join(
                    DOWNLOAD_FOLDER,
                    "%(title)s.%(ext)s"
                ),

            "restrictfilenames":
                True,

            "quiet":
                True,

            "noplaylist":
                True,

            "source_address":
                "0.0.0.0"

        }

    else:

        if quality not in [
            "720",
            "480",
            "360"
        ]:
            quality = "720"


        ydl_opts = {

            "format":
                "best",

            "outtmpl":
                os.path.join(
                    DOWNLOAD_FOLDER,
                    "%(title)s.%(ext)s"
                ),

            "restrictfilenames":
                True,

            "quiet":
                True,

            "noplaylist":
                True,

            "source_address":
                "0.0.0.0"

        }


    # Use cookies only when cookies.txt exists.
    if os.path.isfile(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE


    # ======================================
    # DOWNLOAD FILE
    # ======================================

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

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


            local_url = f"/files/{filename}"


            return jsonify({

                "success":
                    True,

                "url":
                    local_url,

                "download_url":
                    local_url,

                "message":
                    "Ready for download!"

            })


    except Exception as e:

        return jsonify({

            "success":
                False,

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

@app.route("/instagram")
def instagram_page():
    return render_template(
        "instagram.html"
    )


@app.route("/x")
def x_page():
    return render_template(
        "x.html"
    )


@app.route("/snapchat")
def snapchat_page():
    return render_template(
        "snapchat.html"
    )


@app.route("/facebook")
def facebook_page():
    return render_template(
        "facebook.html"
    )


# ==========================================
# LEGAL / INFORMATION PAGES
# ==========================================

@app.route("/privacy")
def privacy_page():
    return render_template(
        "privacy.html"
    )


@app.route("/terms")
def terms_page():
    return render_template(
        "terms.html"
    )


@app.route("/copyright")
def copyright_page():
    return render_template(
        "copyright.html"
    )


@app.route("/disclaimer")
def disclaimer_page():
    return render_template(
        "disclaimer.html"
    )


@app.route("/contact")
def contact_page():
    return render_template(
        "contact.html"
    )


# ==========================================
# ERROR PAGES
# ==========================================

@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "404.html"
    ), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template(
        "500.html"
    ), 500


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
