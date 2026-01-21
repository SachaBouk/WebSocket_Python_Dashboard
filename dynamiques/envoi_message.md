sequenceDiagram
    participant C1 as Client1
    participant S as Serveur
    participant C2 as Client2
    
    %% Message entre clients
    C1->>S: ENVOI (message_type="ENVOI" ,receiver=Client2, value="Salut!")
    S->>S: search_receiver()
    alt Receiver not found
        S->>C1: ENVOI(message_type="WARNING",emitter=SERVER, value="E40: Receiver not found")
    else
        S->>C2: ENVOIE (message_type="RECEPTION", emitter=Client1, value="Salut!")
        S->>C1: ENVOIE (message_type="SYS_MESSAGE", emitter="", value="OK")
        C2->> S: ENVOIE (message_type="SYS_MESSAGE", emitter="", value="MESSAGE OK")
        S->>S: MESS_receiver()
        alt MESS_Receiver not found
            S->>C1: ENVOIE (message_type="SYS_MESSAGE", emitter="S", value="message non reçu")
            
        else
            
            S->>C1: ENVOIE (message_type="SYS_MESSAGE", emitter="S", value="message reçu")
        end
    end
   


    %% Reponse
    %%C2->>S: ENVOI (receiver=Client1, value="Hello!")
    %%S->>C1: RECEPTION (emitter=Client2, value="Hello!")

    %% Broadcast serveur
    %%S->>C1: RECEPTION (emitter=SERVER, value="Annonce")
    %%S->>C2: RECEPTION (emitter=SERVER, value="Annonce")

    %% Erreur destinataire inconnu
    %%C1->>S: ENVOI (receiver=Inconnu, value="Test")
    %%S->>C1: RECEPTION "Erreur: destinataire non trouve"



    %% Message au serveur
    %%C1->>S: ENVOI (receiver=SERVER, value="Hello")
    %%Note over S: Affiche le message
