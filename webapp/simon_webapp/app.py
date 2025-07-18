"""Simple Flask app for serving the webapp index and some associated routes.
"""

from __future__ import annotations

from pathlib import Path
from flask import Flask, render_template

APP_ROOT = Path(__file__).resolve().parent.parent

# construct app so routes can be registered via annotation
app = Flask("simon_webapp")

# set configs (@TODO: move this to a config file)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
# enables autoreload for templates, useful for dev (@TODO: should this be enabled for production?)
app.config['TEMPLATES_AUTO_RELOAD'] = True

def get_app():
    """Get the global app variable."""
    return app

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Index route.

    Request body: None

    Response (HTML): The index page containing all frontend code as SPA
    """
    return render_template("index.html"), 200

@app.route("/imprint", methods=["GET"])
def imprint():
    """Imprint route.

    Request body: None

    Response (HTML): The imprint page containing all boilerplate information
    """
    return render_template("imprint.html"), 200
