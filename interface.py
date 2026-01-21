import base64
import os
import sys
import threading
import time
import uuid

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    from PyQt5 import QtMultimedia
    from PyQt5.QtMultimediaWidgets import QVideoWidget
    QT_MULTIMEDIA_AVAILABLE = True
except Exception:
    QtMultimedia = None
    QVideoWidget = None
    QT_MULTIMEDIA_AVAILABLE = False

from Context import Context
from Message import Message, MessageType
from WSClient import WSClient


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}


def _guess_audio_ext(payload):
    if payload.startswith(b"RIFF") and payload[8:12] == b"WAVE":
        return "wav"
    if payload.startswith(b"ID3") or payload[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if payload.startswith(b"OggS"):
        return "ogg"
    if payload[4:8] == b"ftyp":
        return "m4a"
    return "bin"


def _timestamp():
    return time.strftime("%H:%M:%S")


class WSClientQt(QtCore.QObject):
    log_signal = QtCore.pyqtSignal(str)
    message_signal = QtCore.pyqtSignal(object)
    image_signal = QtCore.pyqtSignal(bytes, str)
    audio_signal = QtCore.pyqtSignal(bytes, str)
    video_signal = QtCore.pyqtSignal(bytes, str)
    status_signal = QtCore.pyqtSignal(bool, str)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, ctx, username="Client"):
        super().__init__()
        self._client = WSClient(ctx, username)
        self.ws = self._client.ws
        self.ws.on_open = self.on_open
        self.ws.on_message = self.on_message
        self.ws.on_error = self.on_error
        self.ws.on_close = self.on_close

    @property
    def connected(self):
        return self._client.connected

    def on_open(self, ws):
        self._client.connected = True
        message = Message(MessageType.DECLARATION, emitter=self._client.username, receiver="", value="")
        ws.send(message.to_json())
        self.status_signal.emit(True, "connected")
        self.log_signal.emit(f"[{_timestamp()}] connected as {self._client.username}")

    def on_close(self, ws, close_status_code, close_msg):
        self._client.connected = False
        self.status_signal.emit(False, "disconnected")
        self.log_signal.emit(f"[{_timestamp()}] disconnected")

    def on_error(self, ws, error):
        self.error_signal.emit(str(error))
        self.log_signal.emit(f"[{_timestamp()}] error: {error}")

    def on_message(self, ws, message):
        received_msg = Message.from_json(message)

        if received_msg.message_type == MessageType.SYS_MESSAGE and received_msg.value == "ping":
            pong_msg = Message(MessageType.SYS_MESSAGE, emitter=self._client.username, receiver="", value="pong")
            ws.send(pong_msg.to_json())
            return

        if received_msg.message_type in [
            MessageType.RECEPTION.TEXT,
            MessageType.RECEPTION.IMAGE,
            MessageType.RECEPTION.AUDIO,
            MessageType.RECEPTION.VIDEO,
        ]:
            ack_msg = Message(MessageType.SYS_MESSAGE, emitter=self._client.username, receiver="", value="MESSAGE OK")
            ws.send(ack_msg.to_json())

        payload = {
            "type": received_msg.message_type,
            "emitter": received_msg.emitter,
            "receiver": received_msg.receiver,
            "value": received_msg.value,
        }
        self.message_signal.emit(payload)

        if received_msg.message_type == MessageType.RECEPTION.IMAGE:
            raw = self._decode_media_payload(received_msg.value, "IMG:")
            if raw:
                self.image_signal.emit(raw, received_msg.emitter)
        elif received_msg.message_type == MessageType.RECEPTION.AUDIO:
            raw = self._decode_media_payload(received_msg.value, "AUDIO:")
            if raw:
                self.audio_signal.emit(raw, received_msg.emitter)
        elif received_msg.message_type == MessageType.RECEPTION.VIDEO:
            raw = self._decode_media_payload(received_msg.value, "VIDEO:")
            if raw:
                self.video_signal.emit(raw, received_msg.emitter)


    def disconnect(self):
        if self._client.connected:
            disconnect_msg = Message(MessageType.SYS_MESSAGE, emitter=self._client.username, receiver="", value="Disconnect")
            self._client.ws.send(disconnect_msg.to_json())
        self._client.ws.close()

    def connect(self):
        self._client.connect()

    def send(self, value, dest):
        self._client.send(value, dest)

    def send_image(self, filepath, dest):
        self._client.send_image(filepath, dest)

    def send_audio(self, filepath, dest):
        self._client.send_audio(filepath, dest)

    def send_video(self, filepath, dest):
        self._client.send_video(filepath, dest)

    @staticmethod
    def _decode_media_payload(value, prefix):
        if not isinstance(value, str):
            return None
        if value.startswith(prefix):
            value = value[len(prefix):]
        try:
            return base64.b64decode(value)
        except Exception:
            return None


class ImagePanel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setObjectName("imagePanel")
        self.setText("No image received")
        self.setMinimumHeight(260)

    def set_image(self, pixmap):
        self._pixmap = pixmap
        if self._pixmap:
            self.setText("")
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if not self._pixmap:
            return
        scaled = self._pixmap.scaled(
            self.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)


class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = None
        self.client_thread = None
        self.audio_index = 0
        self.media_dir = os.path.join(os.path.dirname(__file__), "received_media")

        self.setWindowTitle("CCI Chat")
        self.resize(1200, 760)

        self._build_ui()
        self._apply_style()

        self.video_player = QtMultimedia.QMediaPlayer()
        self.video_player.setVideoOutput(self.video_widget)
        self.video_play_btn.clicked.connect(self._toggle_video)


    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        header = QtWidgets.QFrame()
        header.setObjectName("panel")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        title = QtWidgets.QLabel("CCI Chat")
        title.setObjectName("title")
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        self.name_input = QtWidgets.QLineEdit("Client")
        self.name_input.setPlaceholderText("Name")
        self.name_input.setFixedWidth(140)
        header_layout.addWidget(self.name_input)

        self.host_input = QtWidgets.QLineEdit(Context.prod().host)
        self.host_input.setPlaceholderText("Host")
        self.host_input.setFixedWidth(160)
        header_layout.addWidget(self.host_input)

        self.port_input = QtWidgets.QLineEdit(str(Context.prod().port))
        self.port_input.setPlaceholderText("Port")
        self.port_input.setFixedWidth(80)
        header_layout.addWidget(self.port_input)

        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.setProperty("state", "disconnected")
        self.connect_button.clicked.connect(self._toggle_connection)
        header_layout.addWidget(self.connect_button)

        self.status_label = QtWidgets.QLabel("offline")
        self.status_label.setObjectName("status")
        header_layout.addWidget(self.status_label)

        outer.addWidget(header)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        outer.addWidget(splitter, 1)

        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Waiting for messages...")
        left_layout.addWidget(self.log_box, 1)

        input_card = QtWidgets.QFrame()
        input_card.setObjectName("panel")
        input_layout = QtWidgets.QGridLayout(input_card)
        input_layout.setContentsMargins(14, 10, 14, 10)
        input_layout.setSpacing(8)

        send_to_label = QtWidgets.QLabel("Send to")
        send_to_label.setObjectName("section")
        input_layout.addWidget(send_to_label, 0, 0)

        self.dest_select = QtWidgets.QComboBox()
        self.dest_select.setObjectName("destSelect")
        self.dest_select.addItems(["ALL", "SERVER"])
        input_layout.addWidget(self.dest_select, 0, 1, 1, 3)

        message_label = QtWidgets.QLabel("Message")
        message_label.setObjectName("section")
        input_layout.addWidget(message_label, 1, 0)

        self.message_input = QtWidgets.QLineEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.returnPressed.connect(self._send_text)
        input_layout.addWidget(self.message_input, 1, 1, 1, 3)

        self.attach_button = QtWidgets.QToolButton()
        self.attach_button.setObjectName("attachButton")
        self.attach_button.setText("+")
        self.attach_button.setFixedSize(32, 32)
        self.attach_button.clicked.connect(self._attach_file)
        input_layout.addWidget(self.attach_button, 2, 1)

        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.clicked.connect(self._send_text)
        input_layout.addWidget(self.send_button, 2, 2, 1, 2)

        left_layout.addWidget(input_card)

        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        image_card = QtWidgets.QFrame()
        image_card.setObjectName("panel")
        image_layout = QtWidgets.QVBoxLayout(image_card)
        image_layout.setContentsMargins(14, 10, 14, 10)
        image_layout.setSpacing(8)

        image_title = QtWidgets.QLabel("Images")
        image_title.setObjectName("section")
        image_layout.addWidget(image_title)

        self.image_panel = ImagePanel()
        image_layout.addWidget(self.image_panel, 1)

        right_layout.addWidget(image_card, 1)

        audio_card = QtWidgets.QFrame()
        audio_card.setObjectName("panel")
        audio_layout = QtWidgets.QVBoxLayout(audio_card)
        audio_layout.setContentsMargins(14, 10, 14, 10)
        audio_layout.setSpacing(8)

        audio_title = QtWidgets.QLabel("Audio")
        audio_title.setObjectName("section")
        audio_layout.addWidget(audio_title)

        self.audio_list = QtWidgets.QListWidget()
        audio_layout.addWidget(self.audio_list, 1)

        self.audio_status = QtWidgets.QLabel("")
        audio_layout.addWidget(self.audio_status)

        controls = QtWidgets.QHBoxLayout()
        self.play_button = QtWidgets.QPushButton("Play")
        self.play_button.clicked.connect(self._play_audio)
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self._stop_audio)
        controls.addWidget(self.play_button)
        controls.addWidget(self.stop_button)
        audio_layout.addLayout(controls)

        right_layout.addWidget(audio_card, 1)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        if not QT_MULTIMEDIA_AVAILABLE:
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.audio_status.setText("Audio playback requires PyQt5 QtMultimedia.")

        video_card = QtWidgets.QFrame()
        video_card.setObjectName("panel")
        video_layout = QtWidgets.QVBoxLayout(video_card)

        video_title = QtWidgets.QLabel("Video")
        video_title.setObjectName("section")
        video_layout.addWidget(video_title)

        self.video_widget = QVideoWidget()
        video_layout.addWidget(self.video_widget, 1)

        video_controls = QtWidgets.QHBoxLayout()
        self.video_play_btn = QtWidgets.QPushButton("Play / Pause")
        video_controls.addWidget(self.video_play_btn)
        video_layout.addLayout(video_controls)

        right_layout.addWidget(video_card, 1)


    def _apply_style(self):
        font = QtGui.QFont("Trebuchet MS", 10)
        QtWidgets.QApplication.instance().setFont(font)

        self.setStyleSheet(
    """
    
    QMainWindow {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #eef2f7, stop:1 #f8fbff);
    }

    QFrame#panel {
        background: #ffffff;
        border: 1px solid #e1e5ee;
        border-radius: 12px;
    }

    
    QLabel#title {
        font-size: 18px;
        font-weight: 600;
        color: #1d2633;
    }
    QLabel#section {
        font-size: 12px;
        font-weight: 600;
        color: #5a6b85;
    }
    QLabel#status {
        color: #5a6b85;
    }

    
    QTextEdit, QLineEdit {
        background: #f6f8fc;
        border: 1px solid #dbe1ec;
        border-radius: 8px;
        padding: 6px;
        color: #1d2633;  
    }
    QLineEdit::placeholder {
        color: #a0aabc;  
    }

    
    QListWidget {
        background: #f6f8fc;
        border: 1px solid #dbe1ec;
        border-radius: 8px;
        padding: 4px;
        color: #1d2633;
    }

    
    QPushButton {
        background: #1f6feb;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 6px 14px;
    }
    QPushButton:hover {
        background: #1b5fd4;
    }
    QPushButton[state="connected"] {
        background: #e74c3c;
    }
    QPushButton[state="connected"]:hover {
        background: #cf3b2f;
    }

    
    QToolButton#attachButton {
        background: #f0f3f8;
        border: 1px solid #dbe1ec;
        border-radius: 16px;
        font-size: 18px;
        color: #1f6feb;
    }
    QToolButton#attachButton:hover {
        background: #e6ebf3;
    }

    
    QLabel#imagePanel {
        color: #8b98ad;
    }

    
    QSplitter::handle {
        background: #dbe1ec;
    }

    QComboBox#destSelect {
    background: #f6f8fc;
    border: 2px solid #1f6feb;
    border-radius: 10px;
    padding: 6px 36px 6px 10px;
    color: #1d2633;
    font-weight: 600;
    min-height: 34px;
    }


    QComboBox#destSelect::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 30px;
        border-left: 1px solid #dbe1ec;
        background: transparent;
    }

    QComboBox#destSelect::down-arrow {
        width: 10px;
        height: 10px;
        image: none;
        border-left: 2px solid #1f6feb;
        border-bottom: 2px solid #1f6feb;
        margin-right: 8px;
    }


    QComboBox#destSelect:hover {
        background: #eef3ff;
    }

    QComboBox#destSelect:focus {
        border-color: #1b5fd4;
        background: #eef3ff;
    }

    
    QComboBox#destSelect QAbstractItemView {
        background: white;
        border: 1px solid #dbe1ec;
        border-radius: 8px;
        padding: 4px;
        selection-background-color: #1f6feb;
        selection-color: white;
    }

    """
)


    def _toggle_connection(self):
        if self.client and self.client.connected:
            self._disconnect_client()
        else:
            self._connect_client()

    def _connect_client(self):
        username = self.name_input.text().strip() or "Client"
        host = self.host_input.text().strip()
        port_text = self.port_input.text().strip()
        if not host:
            self._append_log("Host is required.")
            return
        if not port_text.isdigit():
            self._append_log("Port must be a number.")
            return
        port = int(port_text)

        ctx = Context(host, port)
        self.client = WSClientQt(ctx, username=username)
        self.client.log_signal.connect(self._append_log)
        self.client.message_signal.connect(self._handle_message)
        self.client.image_signal.connect(self._handle_image)
        self.client.audio_signal.connect(self._handle_audio)
        self.client.video_signal.connect(self._handle_video)
        self.client.status_signal.connect(self._set_connected)
        self.client.error_signal.connect(self._append_log)

        self.client_thread = threading.Thread(target=self.client.connect, daemon=True)
        self.client_thread.start()
        self._append_log(f"[{_timestamp()}] connecting to {host}:{port}...")

    def _disconnect_client(self):
        if not self.client:
            return
        try:
            self.client.disconnect()
        except Exception as exc:
            self._append_log(f"[{_timestamp()}] disconnect failed: {exc}")

    def _set_connected(self, connected, reason):
        if connected:
            self.connect_button.setText("Disconnect")
            self.connect_button.setProperty("state", "connected")
            self.status_label.setText("online")
            self.name_input.setEnabled(False)
            self.host_input.setEnabled(False)
            self.port_input.setEnabled(False)
        else:
            self.connect_button.setText("Connect")
            self.connect_button.setProperty("state", "disconnected")
            self.status_label.setText("offline")
            self.name_input.setEnabled(True)
            self.host_input.setEnabled(True)
            self.port_input.setEnabled(True)
        self.connect_button.style().polish(self.connect_button)

    def _handle_message(self, payload):
        msg_type = payload.get("type", "")
        if msg_type == MessageType.RECEPTION.CLIENT_LIST:
            self._update_client_list(payload.get("value", []))
            return
        emitter = payload.get("emitter", "unknown")
        receiver = payload.get("receiver", "") or "-"
        value = payload.get("value", "")
        if msg_type in (MessageType.RECEPTION.IMAGE, MessageType.ENVOI.IMAGE):
            content = "[image]"
        elif msg_type in (MessageType.RECEPTION.AUDIO, MessageType.ENVOI.AUDIO):
            content = "[audio]"
        elif msg_type in (MessageType.RECEPTION.VIDEO, MessageType.ENVOI.VIDEO):
            content = "[video]"
        elif msg_type in (MessageType.RECEPTION.CLIENT_LIST):
            content = "[client list]"
        else:
            content = value
        self._append_log(f"[{_timestamp()}] {emitter} -> {receiver}: {content} ")

    def _handle_image(self, raw, emitter):
        pixmap = QtGui.QPixmap()
        if pixmap.loadFromData(raw):
            self.image_panel.set_image(pixmap)
            self._append_log(f"[{_timestamp()}] image received from {emitter}")
        else:
            self._append_log(f"[{_timestamp()}] image decode failed")

    def _handle_audio(self, raw, emitter):
        os.makedirs(self.media_dir, exist_ok=True)
        ext = _guess_audio_ext(raw)
        name = f"audio_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{ext}"
        path = os.path.join(self.media_dir, name)
        with open(path, "wb") as handle:
            handle.write(raw)

        self.audio_index += 1
        label = f"{self.audio_index}. {emitter} - audio"
        item = QtWidgets.QListWidgetItem(label)
        item.setData(QtCore.Qt.UserRole, path)
        self.audio_list.addItem(item)
        self._append_log(f"[{_timestamp()}] audio received from {emitter}")

    def _handle_video(self, raw, emitter):
        os.makedirs(self.media_dir, exist_ok=True)
        name = f"video_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.mp4"
        path = os.path.join(self.media_dir, name)

        with open(path, "wb") as f:
            f.write(raw)

        # Charger le fichier vidéo dans le player
        self.video_player.setMedia(
            QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(path))
        )

        # Lancer automatiquement la lecture
        self.video_player.play()

        self._append_log(f"[{_timestamp()}] video received from {emitter} and playing")


    def _send_text(self):
        if not self.client or not self.client.connected:
            self._append_log(f"[{_timestamp()}] not connected")
            return
        dest = self.dest_select.currentText()
        text = self.message_input.text().strip()
        if not text:
            return
        self.client.send(text, dest)
        self._append_log(f"[{_timestamp()}] me -> {dest}: {text}")
        self.message_input.clear()

    def _update_client_list(self, clients):
        current = self.dest_select.currentText()

        self.dest_select.blockSignals(True)
        self.dest_select.clear()
        self.dest_select.addItems(["ALL", "SERVER"])

        for client in sorted(clients):
            self.dest_select.addItem(client)

        if current in clients or current in ("ALL", "SERVER"):
            self.dest_select.setCurrentText(current)

        self.dest_select.blockSignals(False)


    def _attach_file(self):
        if not self.client or not self.client.connected:
            self._append_log(f"[{_timestamp()}] not connected")
            return
        dest = self.dest_select.currentText()
        filters = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;" \
        "Audio (*.mp3 *.wav *.ogg *.m4a);;" \
        "Video (*.mp4 *.avi *.mov *.mkv);;" \
        "All files (*.*)"
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select media", "", filters)
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTS:
            self.client.send_image(path, dest)
            self._append_log(f"[{_timestamp()}] image sent to {dest}")
        elif ext in AUDIO_EXTS:
            self.client.send_audio(path, dest)
            self._append_log(f"[{_timestamp()}] audio sent to {dest}")
        elif ext in VIDEO_EXTS:
            self.client.send_video(path, dest)
            self._append_log(f"[{_timestamp()}] video sent to {dest}")
        else:
            self._append_log(f"[{_timestamp()}] unsupported file type: {ext}")

    def _play_audio(self):
        if not QT_MULTIMEDIA_AVAILABLE:
            self._append_log(f"[{_timestamp()}] audio playback not available")
            return
        item = self.audio_list.currentItem()
        if not item:
            return
        path = item.data(QtCore.Qt.UserRole)
        if not path or not os.path.exists(path):
            self._append_log(f"[{_timestamp()}] audio file missing")
            return
        if not hasattr(self, "player"):
            self.player = QtMultimedia.QMediaPlayer()
        url = QtCore.QUrl.fromLocalFile(path)
        self.player.setMedia(QtMultimedia.QMediaContent(url))
        self.player.play()
        self.audio_status.setText(f"Playing: {os.path.basename(path)}")

    def _stop_audio(self):
        if hasattr(self, "player"):
            self.player.stop()
            self.audio_status.setText("")
    
    def _toggle_video(self):
        if self.video_player.state() == QtMultimedia.QMediaPlayer.PlayingState:
            self.video_player.pause()
        else:
            self.video_player.play()


    def _append_log(self, text):
        self.log_box.append(text)

    def closeEvent(self, event):
        if self.client and self.client.connected:
            try:
                self.client.disconnect()
            except Exception:
                pass
        super().closeEvent(event)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
