import os
import threading
import webbrowser

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Open the login page once. The reloader starts a second process
    # that sets WERKZEUG_RUN_MAIN, so we skip it there to avoid two tabs.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5001/login")).start()
    app.run(debug=True, port=5001)
