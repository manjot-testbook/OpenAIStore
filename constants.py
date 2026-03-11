"""
constants.py – Every config value and variable lives here.
"""
import os

APP_NAME = "Testbook ChatGPT App"
PORT = int(os.getenv("PORT", "8000"))

# Widget
MIME_TYPE = "text/html+skybridge"
WIDGET_URI = "ui://widget/testbook-app.html"

