import threading
from bot import run_bot
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

def start_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # Start flask in a separate thread
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()

    # Start discord bot
    run_bot()
