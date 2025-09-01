from flask import Flask, request, render_template, redirect, url_for, session
import requests
import os
import threading
import time

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


@app.route("/refresh", methods=["GET", "POST"])
def refresh_token():
    """Refresh or debug a token"""
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    result = None
    if request.method == "POST":
        token = request.form.get("token")

        try:
            # Step 1: Get user info
            user_url = f"{FB_GRAPH_URL}/me"
            user_params = {"access_token": token, "fields": "id,name"}
            user_resp = requests.get(user_url, params=user_params)

            if user_resp.status_code != 200:
                result = {"mode": "error", "error": user_resp.json().get("error", "Invalid token")}
            else:
                user_data = user_resp.json()

                # Step 2: Debug token for expiry info
                debug_url = f"{FB_GRAPH_URL}/debug_token"
                debug_params = {
                    "input_token": token,
                    "access_token": token  # using same token for self-check
                }
                debug_resp = requests.get(debug_url, params=debug_params)

                if debug_resp.status_code != 200:
                    result = {"mode": "error", "error": debug_resp.json().get("error", "Could not debug token")}
                else:
                    debug_data = debug_resp.json()

                    result = {
                        "mode": "debug",
                        "data": debug_data,
                        "user": user_data
                    }

        except Exception as e:
            result = {"mode": "error", "error": str(e)}

    return render_template("refresh.html", result=result)


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
