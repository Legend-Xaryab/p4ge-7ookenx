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
# HOME PAGE (direct access, no login needed)
# ----------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ----------------------------
# Example Facebook API Call
# ----------------------------
@app.route("/send_message", methods=["POST"])
def send_message():
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
