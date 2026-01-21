# server_ws.py
from websocket_server import WebsocketServer

HOST = "127.0.0.1"
PORT = 8765

def on_new_client(client, server):
    print(f"[+] Client connecté: id={client['id']} addr={client['address']}")
    server.send_message(client, "Bienvenue !")

def on_client_left(client, server):
    print(f"[-] Client déconnecté: id={client['id']}")

def on_message_received(client, server, message):
    print(f"[{client['id']}] {message}")
    # Echo + broadcast
    server.send_message(client, f"echo: {message}")
    # server.send_message_to_all(f"[{client['id']}] {message}")

if __name__ == "__main__":
    server = WebsocketServer(host=HOST, port=PORT, loglevel=1)
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message_received)

    print(f"Serveur WS sur ws://{HOST}:{PORT}")
    server.run_forever()
