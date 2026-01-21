sequenceDiagram
    participant C1 as Client1
    participant S as Serveur
    participant C2 as Client2

    %% Connexion Client1
    C1->>S: Connexion WebSocket
    S->>C1: RECEPTION "Bienvenue"
    C1->>S: DECLARATION (username=Client1)
    S->>C1: RECEPTION "Declaration recue"

    %% Connexion Client2
    C2->>S: Connexion WebSocket
    S->>C2: RECEPTION "Bienvenue"
    C2->>S: DECLARATION (username=Client2)
    S->>C2: RECEPTION "Declaration recue"
