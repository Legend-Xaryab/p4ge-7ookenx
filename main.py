from flask import Flask, request, render_template, redirect, url_for, session
import requests
import os
import threading
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# Login credentials (set them in Render environment variables)
USERNAME = os.environ.get("APP_USERNAME", "admin")
PASSWORD = os.environ.get("APP_PASSWORD", "password")

# Facebook Graph API Base URL
FB_GRAPH_URL = "https://graph.facebook.com/v20.0"


# -----------------------------
# Routes
# -----------------------------
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
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    """Dashboard after login"""
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/check", methods=["GET", "POST"])
def check_token():
    """Check if one or more tokens are valid"""
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    results = []
    if request.method == "POST":
        tokens_input = request.form.get("tokens")
        tokens = [t.strip() for t in tokens_input.splitlines() if t.strip()]

        for token in tokens:
            url = f"{FB_GRAPH_URL}/me"
            params = {"access_token": token}
            response = requests.get(url, params=params)

            if response.status_code == 200:
                user = response.json()
                results.append({
                    "token": token,
                    "status": "valid",
                    "user": f"{user.get('name')} (ID: {user.get('id')})"
                })
            else:
                try:
                    err = response.json()
                except:
                    err = {"error": "Unknown error"}
                results.append({
                    "token": token,
                    "status": "invalid",
                    "error": err
                })

    return render_template("check.html", results=results)


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


@app.route("/details", methods=["GET", "POST"])
def token_details():
    """Get full details of a token: UID, name, expiry"""
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    details = None
    error = None
    if request.method == "POST":
        token = request.form.get("token")

        # Get user info
        url = f"{FB_GRAPH_URL}/me"
        params = {"access_token": token, "fields": "id,name"}
        user_resp = requests.get(url, params=params)

        # Debug token info
        debug_url = f"{FB_GRAPH_URL}/debug_token"
        debug_params = {"input_token": token, "access_token": token}
        debug_resp = requests.get(debug_url, params=debug_params)

        if user_resp.status_code == 200 and debug_resp.status_code == 200:
            user = user_resp.json()
            debug = debug_resp.json().get("data", {})

            expiry = debug.get("expires_at")
            expiry_str = "Never" if not expiry else datetime.utcfromtimestamp(expiry).strftime("%Y-%m-%d %H:%M:%S UTC")

            details = {
                "id": user.get("id"),
                "name": user.get("name"),
                "token": token,
                "expires_at": expiry_str,
                "is_valid": debug.get("is_valid"),
                "scopes": debug.get("scopes", [])
            }
        else:
            error = f"Error: {user_resp.text} {debug_resp.text}"

    return render_template("details.html", details=details, error=error)


@app.route("/logout")
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for("login"))


# -----------------------------
# Keep Alive Feature
# -----------------------------
def keep_alive():
    """Prevent Render app from sleeping"""
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL")
            if url:
                requests.get(url)
        except Exception as e:
            print("Keep alive error:", e)
        time.sleep(600)  # every 10 minutes


# Start keep_alive thread
threading.Thread(target=keep_alive, daemon=True).start()


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
