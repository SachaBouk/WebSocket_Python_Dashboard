sequenceDiagram
    participant C1 as Client1
    participant S as Serveur
    participant C2 as Client2

    %% DeConnexion volontaire Client1
    S->>C1: ENVOIE (message_type="SYS_MESSAGE", emitter="", value="ping")

    alt NOpong
        S-->S: Remove Client1
    else
        C1->>S: ENVOI (message_type="SYS_MESSAGE", receiver="", value="pong")
    end