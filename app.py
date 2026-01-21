# app.py
from flask import Flask, render_template, Response
import threading
import time
import json

from Context import Context
from Message import MessageType, Message
from WSClient import WSClient

app = Flask(__name__)

# ----------------------------
# Stockage global
# ----------------------------
clients = set()
messages = []
message_seq = 0
MAX_MESSAGES = 500

# ----------------------------
# WebSocket Client ADMIN
# ----------------------------
ctx = Context.prod()
admin_client = WSClient(ctx, username="ADMIN")

def ws_listener():
    """Thread qui écoute le serveur principal et met à jour clients/messages"""
    def is_admin_client(name):
        return isinstance(name, str) and name.upper().startswith("ADMIN")

    def summarize_kind(message_type, value):
        if isinstance(value, dict) and value.get("kind"):
            return value["kind"]
        if message_type in (MessageType.ENVOI.IMAGE, MessageType.RECEPTION.IMAGE):
            return "image"
        if message_type in (MessageType.ENVOI.AUDIO, MessageType.RECEPTION.AUDIO):
            return "audio"
        if message_type in (MessageType.ENVOI.VIDEO, MessageType.RECEPTION.VIDEO):
            return "video"
        if message_type in (
            MessageType.ADMIN.CLIENT_CONNECTED,
            MessageType.ADMIN.CLIENT_DISCONNECTED,
        ):
            return "event"
        return "text"

    def summarize_value(message_type, value):
        if isinstance(value, dict) and value.get("kind"):
            return f"[{value['kind']}]"
        if not isinstance(value, str):
            return value
        if value.startswith("IMG:"):
            return "[image]"
        if value.startswith("AUDIO:"):
            return "[audio]"
        if value.startswith("VIDEO:"):
            return "[video]"
        return value

    def append_message(entry):
        global messages, message_seq
        message_seq += 1
        entry["id"] = message_seq
        messages.append(entry)
        if len(messages) > MAX_MESSAGES:
            messages = messages[-MAX_MESSAGES:]

    def on_message_override(ws, message):
        global clients, messages
        # Appel de la fonction originale pour les prints etc
        admin_client.on_message(ws, message)

        try:
            data = json.loads(message)
        except:
            return

        msg_type = data.get("message_type")
        payload = data.get("data") or {}
        emitter = payload.get("emitter")
        receiver = payload.get("receiver")
        value = payload.get("value") if "value" in payload else None

        # Mise à jour liste clients
        if msg_type == MessageType.RECEPTION.CLIENT_LIST:
            raw_clients = value or []
            clients = {name for name in raw_clients if not is_admin_client(name)}

        # Nouveau message
        elif msg_type == MessageType.ADMIN.ROUTING_LOG:
            log_payload = value if isinstance(value, dict) else {}
            msg_type = log_payload.get("message_type", msg_type)
            msg_value = log_payload.get("value")
            timestamp = log_payload.get("timestamp", time.time())
            if emitter == "SERVER" and msg_value in ("Bienvenue", "Bienvenue !"):
                return
            append_message({
                "timestamp": timestamp,
                "message_type": msg_type,
                "kind": summarize_kind(msg_type, msg_value),
                "emitter": emitter,
                "receiver": receiver,
                "value": summarize_value(msg_type, msg_value),
            })
        elif msg_type in (MessageType.ADMIN.CLIENT_CONNECTED, MessageType.ADMIN.CLIENT_DISCONNECTED):
            timestamp = time.time()
            append_message({
                "timestamp": timestamp,
                "message_type": msg_type,
                "kind": summarize_kind(msg_type, value),
                "emitter": emitter,
                "receiver": receiver,
                "value": summarize_value(msg_type, value),
            })
        elif msg_type in (
            MessageType.RECEPTION.TEXT,
            MessageType.RECEPTION.IMAGE,
            MessageType.RECEPTION.AUDIO,
            MessageType.RECEPTION.VIDEO,
        ):
            # Ignore le message d'accueil répété
            if emitter == "SERVER" and value in ("Bienvenue", "Bienvenue !"):
                return
            append_message({
                "timestamp": time.time(),
                "message_type": msg_type,
                "kind": summarize_kind(msg_type, value),
                "emitter": emitter,
                "receiver": receiver,
                "value": summarize_value(msg_type, value),
            })

    # Override la méthode on_message
    admin_client.ws.on_message = on_message_override
    admin_client.connect()

# Lancement du thread WS
threading.Thread(target=ws_listener, daemon=True).start()

# ----------------------------
# Route principale
# ----------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ----------------------------
# SSE Endpoint
# ----------------------------
@app.route("/stream")
def stream():
    def event_stream():
        last_clients = set()
        last_messages_len = 0
        while True:
            global clients, messages
            time.sleep(0.5)

            # Envoi clients si changement
            if clients != last_clients:
                data = json.dumps({"type": "clients", "clients": list(clients)})
                yield f"data: {data}\n\n"
                last_clients = set(clients)

            # Envoi messages si changement
            if len(messages) != last_messages_len:
                for msg in messages[last_messages_len:]:
                    data = json.dumps({"type": "message", **msg})
                    yield f"data: {data}\n\n"
                last_messages_len = len(messages)

    return Response(event_stream(), mimetype="text/event-stream")

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    print(f"Admin Dashboard running at http://127.0.0.1:5001")
    print(f"WebSocket server expected at {ctx.url()}")
    app.run(debug=True, port=5001)
