"""
K.IA - Serveur backend Flask + SocketIO
"""

import asyncio
import threading
import traceback
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from KIA_Online import KIA

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Boucle asyncio dediee dans un thread daemon
loop = asyncio.new_event_loop()

def run_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=run_loop, daemon=True).start()

# Instance K.IA
kia = KIA(socketio)


def run_async(coro):
    """Lance une coroutine dans la boucle asyncio et logue les erreurs."""
    def callback(future):
        exc = future.exception()
        if exc:
            print(f"[K.IA][ERREUR async] {exc}")
            traceback.print_exception(type(exc), exc, exc.__traceback__)
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    future.add_done_callback(callback)


@socketio.on("connect")
def handle_connect():
    print("[K.IA] Client connecte")
    socketio.emit("status", {"message": "connected"})


@socketio.on("disconnect")
def handle_disconnect():
    print("[K.IA] Client deconnecte")


@socketio.on("send_text_message")
def handle_text_message(data):
    message = data.get("message", "").strip()
    if not message:
        return
    print(f"[K.IA] Message : {message}")
    run_async(kia.process_input(message))


@socketio.on("send_transcribed_text")
def handle_transcribed_text(data):
    text = data.get("text", "").strip()
    if not text:
        return
    print(f"[K.IA] Voix : {text}")
    run_async(kia.process_input(text, use_camera=True))


@socketio.on("send_video_frame")
def handle_video_frame(data):
    kia.set_video_frame(data.get("frame"))


if __name__ == "__main__":
    print("=" * 50)
    print("  K.IA - Konect Intelligence Artefact")
    print("  Serveur sur http://localhost:5000")
    print("=" * 50)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)