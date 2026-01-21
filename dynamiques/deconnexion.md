sequenceDiagram
    participant C1 as Client1
    participant S as Serveur
    participant C2 as Client2

    %% DeConnexion volontaire Client1
    C1->>S: ENVOI (message_type="SYS_MESSAGE", receiver="", value="Disconnect")
    S->>S: remove Client1

