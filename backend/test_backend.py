"""
K.IA - Test rapide du backend
Lance d'abord : python app.py
Puis dans un autre terminal : python test_backend.py
"""

import socketio
import time

sio = socketio.Client()

@sio.on("connect")
def on_connect():
    print("[OK] Connecte au serveur K.IA !")

@sio.on("status")
def on_status(data):
    print(f"[STATUS] {data.get('message')}")

@sio.on("receive_text_chunk")
def on_chunk(data):
    print(data.get("text", ""), end="", flush=True)

@sio.on("disconnect")
def on_disconnect():
    print("\n[INFO] Deconnecte.")

sio.connect("http://localhost:5000")
time.sleep(1)

print("\n--- Envoi du message test ---")
sio.emit("send_text_message", {"message": "Bonjour K.IA, presente-toi en une phrase !"})

time.sleep(10)   # attendre la reponse streamee
sio.disconnect()