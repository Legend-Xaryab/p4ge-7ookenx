from flask import Flask, request, render_template, redirect, url_for, session
import requests
import os
import threading
import time

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# Facebook Graph API Base URL
FB_GRAPH_URL = "https://graph.facebook.com"

# ----------------------------
# LOGIN (No username/password needed)
# ----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # Automatically log in any visitor
    session["logged_in"] = True
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ----------------------------
# HOME PAGE
# ----------------------------
@app.route("/")
def index():
    if "logged_in" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

# ----------------------------
# Example Facebook API Call
# ----------------------------
@app.route("/send_message", methods=["POST"])
def send_message():
    if "logged_in" not in session:
        return redirect(url_for("login"))

    page_access_token = os.environ.get("PAGE_ACCESS_TOKEN", "")
    recipient_id = request.form.get("recipient_id")
    message_text = request.form.get("message")

    url = f"{FB_GRAPH_URL}/me/messages?access_token={page_access_token}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)

    return {"status": response.status_code, "response": response.json()}

# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
