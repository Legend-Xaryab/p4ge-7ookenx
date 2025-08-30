from flask import Flask, request, render_template, redirect, url_for, session
import requests
from threading import Thread, Event
import time
import os

app = Flask(__name__)
app.secret_key = "super-secret-key"  # 🔒 change for production

FB_GRAPH_URL = "https://graph.facebook.com/v19.0"

# Credentials (better: use env vars on Render)
USERNAME = os.getenv("USERNAME", "admin")
PASSWORD = os.getenv("PASSWORD", "password123")

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
        time.sleep(300)


@app.route("/", methods=["GET", "POST"])
def login():
    """Login page"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    """Menu after login"""
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/check", methods=["GET", "POST"])
def check_token():
    """Check if a token is valid"""
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    result = None
    if request.method == "POST":
        token = request.form.get("token")
        url = f"{FB_GRAPH_URL}/me"
        params = {"access_token": token}
        response = requests.get(url, params=params)

        if response.status_code == 200:
            user = response.json()
            result = f"✅ Valid token! User: {user.get('name')} (ID: {user.get('id')})"
        else:
            result = f"❌ Invalid token. Error: {response.json()}"

    return render_template("check.html", result=result)


@app.route("/extract", methods=["GET", "POST"])
def extract_pages():
    """Extract page tokens from a user token"""
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    pages = None
    error = None
    if request.method == "POST":
        user_token = request.form.get("token")
        url = f"{FB_GRAPH_URL}/me/accounts"
        params = {"access_token": user_token}
        response = requests.get(url, params=params)

        if response.status_code != 200:
            error = f"Error: {response.json()}"
        else:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                pages = [
                    {"name": page["name"], "id": page["id"], "access_token": page["access_token"]}
                    for page in data["data"]
                ]
            else:
                error = "No pages found for this account."

    return render_template("extract.html", pages=pages, error=error)


@app.route("/logout")
def logout():
    """Logout user"""
    session.pop("logged_in", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    t = Thread(target=self_ping, daemon=True)
    t.start()
    try:
        app.run(host="0.0.0.0", port=5000)
    finally:
        stop_event.set()
