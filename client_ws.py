# client_ws.py
import time
import websocket

URL = "ws://127.0.0.1:8765"

def on_message(ws, message):
    print(f"[server] {message}")

def on_error(ws, error):
    print(f"[error] {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"[close] code={close_status_code} msg={close_msg}")

def on_open(ws):
    print("[open] connecté")


