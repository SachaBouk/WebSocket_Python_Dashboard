# WebSocket Chat Project – Server, Clients & Admin Dashboard

Projet complet de communication temps réel basé sur **WebSocket en Python**, comprenant :

- Un **serveur WebSocket**
- Des **clients CLI**
- Une **interface graphique**
- Un **dashboard administrateur web** (Flask)

Le projet permet l’échange de messages texte, images, audio et vidéo entre clients, avec supervision en temps réel côté admin.

## ⚙️ Installation

### 1. Cloner le dépôt :

```bash
git clone https://github.com/SachaBouk/WebSocket_Python_Dashboard.git

cd WebSocket_Python_Dashboard
```

### 2. Créer un environnement virtuel (recommandé) :

```bash
python -m venv venv
source venv/bin/activate  (Linux / Mac)
venv\Scripts\activate     (Windows)
```

### 3. Installer les dépendances :

```bash
pip install -r requirements.txt
```

## ✅ Lancement des composants : 
### Il est recommandé de lancer chaque composant dans un terminal séparé :

## Serveur WebSocket :

```bash
python3 WSServer.py
```

## Interface Graphique Login/Client chat (PyQT5):

```bash
python3 interface.py
```

## Dashboard Admin (Flask) :

```bash
python3 app.py
```

Le dashboard est accessible dans le navigateur à cette adresse : http://127.0.0.1:5001/

## 🧰 Configuration Contexte : 

### Pour changer d'environnement (Dev ou Prod) :

1. **Context.py** : Modifiez la classe `Context` dans `Context.py` si nécessaire pour ajuster les IPs et ports.

2. **WSServer.py** : Dans le bloc if `__name__ == "__main__":` à la fin du fichier, changez le mode d'initialisation :

- Pour le développement local : ``ws_server = WSServer.dev()``
- Pour la production : ``ws_server = WSServer.prod()``

3. **WSClient.py** : Dans le bloc if `__name__ == "__main__":` à la fin du fichier, changez le mode d'initialisation :

- Pour le développement local : ``client = WSClient.dev(username)``
- Pour la production : ``client = WSClient.prod(username)``

4. **app.py** : Dans `ctx = Context.prod()` au début du fichier, changez le mode d'initialisation :

- Pour le développement local : ``ctx = Context.dev()``
- Pour la production : ``ctx = Context.prod()``