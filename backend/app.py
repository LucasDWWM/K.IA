"""
K.IA - Serveur backend Flask + SocketIO
"""

import asyncio
import os
import threading
import traceback

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from KIA_Online import KIA
from memory import MemoryManager
from tts import TTSEngine

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

MEMORY_DIR          = os.getenv("MEMORY_DIR", os.path.join(os.path.dirname(__file__), "memory_store"))
TTS_PROVIDER        = os.getenv("TTS_PROVIDER", "browser")
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "") or os.getenv("VOICE_ID", "")

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Boucle asyncio dediee dans un thread daemon
loop = asyncio.new_event_loop()

def run_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=run_loop, daemon=True).start()

# Memoire + synthese vocale
memory_manager = MemoryManager(MEMORY_DIR)
tts_engine = TTSEngine(
    provider=TTS_PROVIDER,
    api_key=ELEVENLABS_API_KEY,
    voice_id=ELEVENLABS_VOICE_ID,
)

# Instance K.IA
kia = KIA(socketio, memory_manager=memory_manager, tts_engine=tts_engine)
memory_manager.kia_client = kia


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
    socketio.emit("tts_mode", {"provider": tts_engine.provider, "server_audio": tts_engine.enabled})
    socketio.emit("memory_stats", memory_manager.stats())


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


@socketio.on("end_session")
def handle_end_session(_data=None):
    """Consolide la session courante dans la memoire long terme."""
    print("[K.IA] Fin de session demandee")
    run_async(kia.end_session())


@socketio.on("get_memory")
def handle_get_memory(data=None):
    """Renvoie le bloc memoire courant (debug / affichage HUD)."""
    n_last = int((data or {}).get("n_last", 10))
    socketio.emit("memory_context", {
        "context": memory_manager.load_context(n_last=n_last),
        **memory_manager.stats(),
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  K.IA - Konect Intelligence Artefact")
    print("  Serveur sur http://localhost:5000")
    print(f"  Memoire : {memory_manager.memory_dir}")
    print("=" * 50)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)
