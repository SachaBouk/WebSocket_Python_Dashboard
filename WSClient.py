import websocket
import threading
import base64

from Context import Context
from Message import Message, MessageType


class WSClient:
    def __init__(self, ctx, username="Client"):
        self.username = username
        self.connected = False
        self.ws = websocket.WebSocketApp(
            ctx.url(),
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

    def on_message(self, ws, message):
        received_msg = Message.from_json(message)

        # Répondre au ping du serveur
        if received_msg.message_type == MessageType.SYS_MESSAGE and received_msg.value == "ping":
            pong_msg = Message(MessageType.SYS_MESSAGE, emitter=self.username, receiver="", value="pong")
            ws.send(pong_msg.to_json())
            return

        # Affichage selon le type de message
        print(f"\n[{received_msg.emitter}] {received_msg.value}")
        print(f"[{self.username}] > ", end="", flush=True)

        # Accusé de réception pour les messages RECEPTION
        if received_msg.message_type in [MessageType.RECEPTION.TEXT, MessageType.RECEPTION.IMAGE, MessageType.RECEPTION.AUDIO, MessageType.RECEPTION.VIDEO]:
            ack_msg = Message(MessageType.SYS_MESSAGE, emitter=self.username, receiver="", value="MESSAGE OK")
            ws.send(ack_msg.to_json())

    def on_error(self, ws, error):
        print(f"\n[error] {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"\n[close] code={close_status_code} msg={close_msg}")
        self.connected = False

    def on_client_list(self):
        message = Message(MessageType.ENVOI.CLIENT_LIST, emitter=self.username, receiver="", value="")
        self.ws.send(message.to_json())

    def on_open(self, ws):
        print("[open] connecté")
        self.connected = True
        message = Message(MessageType.DECLARATION, emitter=self.username, receiver="", value="")
        ws.send(message.to_json())

        input_thread = threading.Thread(target=self.input_loop, daemon=True)
        input_thread.start()

    def input_loop(self):
        print(f"Chat démarré. Tapez 'dest:message' pour envoyer (ex: SERVER:bonjour)")
        print(f"Tapez 'img:dest:chemin' pour envoyer une image (ex: img:Client2:/path/image.png)")
        print(f"Tapez 'audio:dest:chemin' pour envoyer un audio (ex: audio:Client2:/path/audio.mp3)")
        print(f"Tapez 'disconnect' pour quitter.\n")
        while self.connected:
            try:
                print(f"[{self.username}] > ", end="", flush=True)
                user_input = input()
                if user_input.lower() == "disconnect":
                    disconnect_msg = Message(MessageType.SYS_MESSAGE, emitter=self.username, receiver="", value="Disconnect")
                    self.ws.send(disconnect_msg.to_json())
                    self.ws.close()
                    break
                if user_input.lower().startswith("img:"):
                    parts = user_input[4:].split(":", 1)
                    if len(parts) == 2:
                        dest, filepath = parts[0].strip(), parts[1].strip()
                        self.send_image(filepath, dest)
                        print(f"Image envoyée à {dest}")
                    else:
                        print("Format: img:dest:chemin")
                    continue
                if user_input.lower().startswith("audio:"):
                    parts = user_input[6:].split(":", 1)
                    if len(parts) == 2:
                        dest, filepath = parts[0].strip(), parts[1].strip()
                        self.send_audio(filepath, dest)
                        print(f"Audio envoyé à {dest}")
                    else:
                        print("Format: audio:dest:chemin")
                    continue
                if user_input.lower().startswith("video:"):
                    parts = user_input[6:].split(":", 1)
                    if len(parts) == 2:
                        dest, filepath = parts[0].strip(), parts[1].strip()
                        self.send_video(filepath, dest)
                        print(f"Vidéo envoyée à {dest}")
                    else:
                        print("Format: video:dest:chemin")
                    continue
                if ":" in user_input:
                    dest, content = user_input.split(":", 1)
                    self.send(content.strip(), dest.strip())
                else:
                    self.send(user_input, "SERVER")
            except EOFError:
                break

    def connect(self):
        self.ws.run_forever()

    def send(self, value, dest):
        message = Message(MessageType.ENVOI.TEXT, emitter=self.username, receiver=dest, value=value)
        self.ws.send(message.to_json())

    def send_image(self, filepath, dest):
        with open(filepath, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")
        value = f"IMG:{img_base64}"
        message = Message(MessageType.ENVOI.IMAGE, emitter=self.username, receiver=dest, value=value)
        self.ws.send(message.to_json())

    def send_audio(self, filepath, dest):
        with open(filepath, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        value = f"AUDIO:{audio_base64}"
        message = Message(MessageType.ENVOI.AUDIO, emitter=self.username, receiver=dest, value=value)
        self.ws.send(message.to_json())
    
    def send_video(self, filepath, dest):
        with open(filepath, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode("utf-8")
        value = f"VIDEO:{video_base64}"
        message = Message(MessageType.ENVOI.VIDEO, emitter=self.username, receiver=dest, value=value)
        self.ws.send(message.to_json())

    @staticmethod
    def dev(username="Client"):
        return WSClient(Context.dev(), username)

    @staticmethod
    def prod(username="Client"):
        return WSClient(Context.prod(), username)

if __name__ == "__main__":
    import sys
    username = sys.argv[1] if len(sys.argv) > 1 else "Client"
    client = WSClient.prod(username)
    client.connect()