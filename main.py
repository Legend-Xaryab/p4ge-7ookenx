from flask import Flask, request, render_template, redirect, url_for, session
import requests
from threading import Thread, Event
import time
import os

app = Flask(__name__)
app.secret_key = "super-secret-key"  # 🔒 change this to a strong random key in production

FB_GRAPH_URL = "https://graph.facebook.com/v19.0"

# Dummy credentials (you can change them)
USERNAME = "admin"
PASSWORD = "password123"

# === Self-ping setup ===
stop_event = Event()

def self_ping():
    """Ping the app every 5 minutes to keep it awake on Render."""
    while not stop_event.is_set():
        try:
            url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:5000")
            requests.get(url)
        except Exception as e:
            print(f"Self-ping failed: {e}")
        time.sleep(300)  # every 5 minutes


@app.route("/", methods=["GET", "POST"])
def login():
    """Login page"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route("/pages", methods=["GET", "POST"])
def index():
    """Facebook token input & page checker"""
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        user_token = request.form.get("token")

        # Get user pages
        url = f"{FB_GRAPH_URL}/me/accounts"
        params = {"access_token": user_token}
        response = requests.get(url, params=params)

        if response.status_code != 200:
            return f"Error: {response.json()}"

        data = response.json()

        if "data" in data and len(data["data"]) > 0:
            pages = [
                {"name": page["name"], "id": page["id"], "access_token": page["access_token"]}
                for page in data["data"]
            ]
            return render_template("index.html", pages=pages)

        return "No pages found for this account."

    return render_template("index.html", pages=None)


@app.route("/logout")
def logout():
    """Logout user"""
    session.pop("logged_in", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    # Start self-ping thread
    t = Thread(target=self_ping, daemon=True)
    t.start()

    try:
        app.run(host="0.0.0.0", port=5000)
    finally:
        stop_event.set()
