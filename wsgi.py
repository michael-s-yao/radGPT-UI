#!/usr/bin/env python3
"""
Web Server Gateway Interface (WSGI) for Flask app.

Author(s):
    Michael Yao @michael-s-yao
    Allison Chae @allisonjchae

Licensed under the MIT License. Copyright University of Pennsylvania 2024.
"""
from app.main import create_app


debug = True
app = create_app(debug=debug)
app.run()
