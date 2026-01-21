# client_ws_blocking.py
import websocket

URL = "ws://127.0.0.1:8080"

if __name__ == "__main__":
    ws = websocket.create_connection(URL, timeout=5)
    print("Connecté")

    ws.send("hello")
    print("Réponse:", ws.recv())

    ws.send("ping")
    print("Réponse:", ws.recv())

    ws.close()
    print("Fermé")
