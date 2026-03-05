import base64
import json
import os
import queue
import socket
import struct
import threading
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, ttk

from cryptography.fernet import Fernet

def derive_fernet_key(secret: str) -> bytes:
    raw = secret.encode("utf-8")
    padded = (raw * ((32 // len(raw)) + 1))[:32] if raw else b"default-secret-chat-key-32-bytes!!"
    return base64.urlsafe_b64encode(padded)

def send_packet(sock: socket.socket, data: bytes) -> None:
    sock.sendall(struct.pack("!I", len(data)) + data)

def recv_exact(sock: socket.socket, size: int) -> bytes:
    buf = b""
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise ConnectionError("La connexion au client a été fermée.")
        buf += chunk
    return buf

def recv_packet(sock: socket.socket) -> bytes:
    header = recv_exact(sock, 4)
    (size,) = struct.unpack("!I", header)
    return recv_exact(sock, size)

class ChatServerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Serveur de Chat - Administration")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        self.host_var = tk.StringVar(value="0.0.0.0")
        self.port_var = tk.IntVar(value=5000)
        self.status_var = tk.StringVar(value="Serveur arrêté")

        secret = os.getenv("CHAT_SECRET", "changez-moi-rapidement-123456789")
        self.cipher = Fernet(derive_fernet_key(secret))

        self.server_socket = None
        self.running = False
        self.clients = {}  # username -> socket
        self.client_locks = {}  # username -> lock for socket write
        self.clients_lock = threading.Lock()

        self.log_queue: "queue.Queue[str]" = queue.Queue()

        self._apply_theme()
        self._build_ui()
        self.root.after(100, self._drain_logs)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _apply_theme(self):
        # Palette claire moderne
        self.colors = {
            "bg": "#f8fafc",           # fond général très clair
            "surface": "#ffffff",       # surface blanche
            "surface_light": "#f1f5f9", # gris très clair
            "text": "#0f172a",          # bleu nuit (texte principal)
            "text_secondary": "#475569",# gris bleuté (texte secondaire)
            "accent": "#8b5cf6",        # violet (accent)
            "accent_hover": "#7c3aed",  # violet foncé
            "success": "#22c55e",       # vert
            "warning": "#f97316",       # orange
            "danger": "#ef4444",        # rouge
            "danger_hover": "#dc2626",  # rouge foncé
            "border": "#cbd5e1",        # gris clair pour bordures
            "log_bg": "#ffffff",        # fond journal blanc
            "log_text": "#0f172a",      # texte journal sombre
        }

        self.root.configure(bg=self.colors["bg"])

        style = ttk.Style()
        style.theme_use("clam")

        # Configuration globale
        style.configure(".",
                        background=self.colors["surface"],
                        foreground=self.colors["text"],
                        font=("Inter", 10),
                        relief="flat",
                        borderwidth=0)

        # Frames
        style.configure("Surface.TFrame",
                        background=self.colors["surface"])
        style.configure("Header.TFrame",
                        background=self.colors["surface"])

        # Labels
        style.configure("Title.TLabel",
                        background=self.colors["surface"],
                        foreground=self.colors["text"],
                        font=("Inter", 16, "bold"))

        style.configure("Subtitle.TLabel",
                        background=self.colors["surface"],
                        foreground=self.colors["text_secondary"],
                        font=("Inter", 11))

        style.configure("Status.TLabel",
                        background=self.colors["surface"],
                        foreground=self.colors["text_secondary"],
                        font=("Inter", 11))

        # Buttons
        style.configure("Success.TButton",
                        background=self.colors["success"],
                        foreground="#ffffff",
                        borderwidth=0,
                        focuscolor="none",
                        font=("Inter", 10, "bold"),
                        padding=(16, 8))
        style.map("Success.TButton",
                  background=[("active", "#16a34a"),
                              ("disabled", self.colors["border"])])

        style.configure("Danger.TButton",
                        background=self.colors["danger"],
                        foreground="#ffffff",
                        borderwidth=0,
                        focuscolor="none",
                        font=("Inter", 10, "bold"),
                        padding=(16, 8))
        style.map("Danger.TButton",
                  background=[("active", self.colors["danger_hover"])])

        # Entry
        style.configure("TEntry",
                        fieldbackground=self.colors["surface_light"],
                        foreground=self.colors["text"],
                        insertcolor=self.colors["text"],
                        borderwidth=0,
                        focuscolor=self.colors["accent"],
                        padding=(10, 8))
        style.map("TEntry",
                  fieldbackground=[("focus", self.colors["surface_light"])])

        # Labelframe
        style.configure("TLabelframe",
                        background=self.colors["surface"],
                        foreground=self.colors["text"],
                        bordercolor=self.colors["border"],
                        borderwidth=1,
                        relief="solid")
        style.configure("TLabelframe.Label",
                        background=self.colors["surface"],
                        foreground=self.colors["accent"],
                        font=("Inter", 11, "bold"))

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        # Header
        header_container = ttk.Frame(self.root, style="Header.TFrame")
        header_container.grid(row=0, column=0, sticky="ew")
        header = ttk.Frame(header_container, style="Surface.TFrame", padding="16 20")
        header.pack(fill=tk.X)

        title_frame = ttk.Frame(header, style="Surface.TFrame")
        title_frame.pack(side=tk.LEFT)
        ttk.Label(title_frame, text="🖥️", style="Title.TLabel", font=("Inter", 20)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(title_frame, text="SecureChat Server", style="Title.TLabel").pack(side=tk.LEFT)

        self.status_badge = tk.Label(
            header,
            text="⛔ Arrêté",
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"],
            font=("Inter", 11, "bold"),
        )
        self.status_badge.pack(side=tk.RIGHT)

        # Panneau de contrôle
        control_frame = ttk.LabelFrame(self.root, text="Contrôle du serveur", padding="20")
        control_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        control_grid = ttk.Frame(control_frame, style="Surface.TFrame")
        control_grid.pack(fill=tk.X)
        control_grid.columnconfigure(0, weight=1)

        # Configuration réseau
        network_frame = ttk.Frame(control_grid, style="Surface.TFrame")
        network_frame.grid(row=0, column=0, sticky="ew")
        network_frame.columnconfigure(1, weight=2)
        network_frame.columnconfigure(3, weight=1)

        ttk.Label(network_frame, text="🌐 Interface", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        host_entry = ttk.Entry(network_frame, textvariable=self.host_var)
        host_entry.grid(row=0, column=1, padx=(0, 16), pady=5, sticky="ew")

        ttk.Label(network_frame, text="🔌 Port", style="Subtitle.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=5)
        port_entry = ttk.Entry(network_frame, textvariable=self.port_var)
        port_entry.grid(row=0, column=3, padx=(0, 16), pady=5, sticky="ew")

        # Boutons
        button_frame = ttk.Frame(control_grid, style="Surface.TFrame")
        button_frame.grid(row=0, column=1, sticky="e", padx=(20, 0))

        self.start_btn = ttk.Button(
            button_frame,
            text="▶️ Démarrer",
            command=self.start_server,
            style="Success.TButton",
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹️ Arrêter",
            command=self.stop_server,
            style="Danger.TButton",
        )
        self.stop_btn.pack(side=tk.LEFT)

        # Zone principale
        main_container = ttk.Frame(self.root, style="Surface.TFrame")
        main_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_container.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)

        main_pane = ttk.Panedwindow(main_container, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky="nsew")

        # Panneau gauche - Clients connectés
        left_panel = ttk.Frame(main_pane, style="Surface.TFrame")
        clients_frame = ttk.LabelFrame(left_panel, text="👥 Clients connectés", padding="16")
        clients_frame.pack(fill=tk.BOTH, expand=True)
        clients_frame.columnconfigure(0, weight=1)
        clients_frame.rowconfigure(1, weight=1)

        clients_header = ttk.Frame(clients_frame, style="Surface.TFrame")
        clients_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.client_count = ttk.Label(
            clients_header,
            text="0 connecté",
            style="Subtitle.TLabel",
            font=("Inter", 11, "bold"),
        )
        self.client_count.pack(side=tk.LEFT)

        clients_list_area = ttk.Frame(clients_frame, style="Surface.TFrame")
        clients_list_area.grid(row=1, column=0, sticky="nsew")
        clients_list_area.columnconfigure(0, weight=1)
        clients_list_area.rowconfigure(0, weight=1)

        self.clients_listbox = tk.Listbox(
            clients_list_area,
            bg=self.colors["surface_light"],
            fg=self.colors["text"],
            selectbackground=self.colors["accent"],
            selectforeground=self.colors["text"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            borderwidth=0,
            font=("Inter", 11),
            activestyle="none",
            relief="flat",
        )
        self.clients_listbox.grid(row=0, column=0, sticky="nsew")
        clients_scroll = ttk.Scrollbar(clients_list_area, command=self.clients_listbox.yview)
        clients_scroll.grid(row=0, column=1, sticky="ns")
        self.clients_listbox.config(yscrollcommand=clients_scroll.set)

        # Panneau droit - Journal serveur
        right_panel = ttk.Frame(main_pane, style="Surface.TFrame")
        log_frame = ttk.LabelFrame(right_panel, text="📋 Journal serveur", padding="16")
        log_frame.pack(fill=tk.BOTH, expand=True)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        log_area = ttk.Frame(log_frame, style="Surface.TFrame")
        log_area.grid(row=0, column=0, sticky="nsew")
        log_area.columnconfigure(0, weight=1)
        log_area.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_area,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=self.colors["log_bg"],
            fg=self.colors["log_text"],
            insertbackground=self.colors["text"],
            borderwidth=0,
            font=("JetBrains Mono", 11),
            padx=12,
            pady=12,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_area, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_scroll.set)

        main_pane.add(left_panel, weight=2)
        main_pane.add(right_panel, weight=5)

        # Barre d'état (sans DB)
        status_bar = ttk.Frame(self.root, style="Surface.TFrame", relief="flat")
        status_bar.grid(row=3, column=0, sticky="ew")
        self.status_label = tk.Label(
            status_bar,
            text="✅ Serveur prêt",
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"],
            font=("Inter", 10),
            padx=16,
            pady=8,
        )
        self.status_label.pack(side=tk.LEFT)

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")

    def _drain_logs(self):
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, line + "\n")
            self.log_text.config(state=tk.DISABLED)
            self.log_text.see(tk.END)
        self.root.after(100, self._drain_logs)

    def _refresh_clients_ui(self):
        self.clients_listbox.delete(0, tk.END)
        with self.clients_lock:
            for user in sorted(self.clients.keys()):
                self.clients_listbox.insert(tk.END, f"👤 {user}")

        count = len(self.clients)
        if count == 0:
            self.client_count.config(text="Aucun client connecté")
        elif count == 1:
            self.client_count.config(text="1 client connecté")
        else:
            self.client_count.config(text=f"{count} clients connectés")

    def start_server(self):
        if self.running:
            return

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host_var.get(), self.port_var.get()))
            self.server_socket.listen(50)
            self.running = True

            host = self.host_var.get()
            port = self.port_var.get()
            display_host = "0.0.0.0" if host == "0.0.0.0" else host

            self.status_var.set(f"Serveur actif sur {display_host}:{port}")
            self.status_badge.config(text="🟢 En ligne", fg=self.colors["success"])

            threading.Thread(target=self._accept_loop, daemon=True).start()
            self._log(f"🚀 Serveur démarré sur {display_host}:{port}")
        except Exception as exc:
            self._log(f"❌ Impossible de démarrer le serveur : {exc}")

    def stop_server(self):
        if not self.running:
            return

        self.running = False

        host = self.host_var.get()
        port = self.port_var.get()
        display_host = "0.0.0.0" if host == "0.0.0.0" else host

        try:
            if self.server_socket:
                self.server_socket.close()
        except Exception:
            pass

        with self.clients_lock:
            for username, sock in list(self.clients.items()):
                try:
                    self._send_plain(sock, {"type": "system", "message": "Le serveur a été arrêté."}, username)
                    sock.close()
                except Exception:
                    pass
            self.clients.clear()
            self.client_locks.clear()

        self._refresh_clients_ui()
        self.status_var.set("Serveur arrêté")
        self.status_badge.config(text="⛔ Arrêté", fg=self.colors["text_secondary"])
        self._log(f"🛑 Serveur arrêté sur {display_host}:{port}")

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True).start()
            except OSError:
                break
            except Exception as exc:
                self._log(f"❌ Erreur lors de l'acceptation de connexion : {exc}")

    def _send_plain(self, sock: socket.socket, payload: dict, username: str | None = None):
        encoded = json.dumps(payload).encode("utf-8")
        encrypted = self.cipher.encrypt(encoded)
        if username and username in self.client_locks:
            with self.client_locks[username]:
                send_packet(sock, encrypted)
        else:
            send_packet(sock, encrypted)

    def _broadcast_clients_list(self):
        with self.clients_lock:
            usernames = sorted(self.clients.keys())
            snapshot = list(self.clients.items())
        for user, sock in snapshot:
            try:
                self._send_plain(sock, {"type": "clients", "clients": [u for u in usernames if u != user]}, user)
            except Exception as exc:
                self._log(f"❌ Impossible d'envoyer la liste des clients à {user} : {exc}")

    def _disconnect(self, username: str):
        with self.clients_lock:
            sock = self.clients.pop(username, None)
            self.client_locks.pop(username, None)
        if sock:
            try:
                sock.close()
            except Exception:
                pass
        self._refresh_clients_ui()
        self._broadcast_clients_list()
        self._log(f"👋 {username} s'est déconnecté.")

    def _route_message(self, sender: str, mode: str, targets: list, text: str):
        delivered_to = []
        with self.clients_lock:
            clients_snapshot = dict(self.clients)

        if mode == "broadcast":
            recipients = [u for u in clients_snapshot if u != sender]
        elif mode == "private":
            recipients = targets[:1]
        elif mode == "group":
            recipients = [u for u in targets if u != sender]
        else:
            recipients = []

        message = {
            "type": "chat",
            "sender": sender,
            "mode": mode,
            "targets": recipients,
            "message": text,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

        for user in recipients:
            sock = clients_snapshot.get(user)
            if not sock:
                continue
            try:
                self._send_plain(sock, message, user)
                delivered_to.append(user)
            except Exception as exc:
                self._log(f"❌ Échec de l'envoi du message à {user} : {exc}")

        # La persistance des messages a été retirée (MySQL supprimé)

    def _handle_client(self, client_sock: socket.socket, addr):
        username = None
        try:
            raw = recv_packet(client_sock)
            auth = json.loads(self.cipher.decrypt(raw).decode("utf-8"))
            if auth.get("type") != "auth":
                raise ValueError("Le paquet d'authentification est invalide.")
            username = auth.get("username", "").strip()
            if not username:
                raise ValueError("Le nom d'utilisateur ne peut pas être vide.")

            with self.clients_lock:
                if username in self.clients:
                    self._send_plain(client_sock, {"type": "error", "message": "Ce nom d'utilisateur est déjà pris."})
                    client_sock.close()
                    return
                self.clients[username] = client_sock
                self.client_locks[username] = threading.Lock()

            self._send_plain(client_sock, {"type": "auth_ok", "message": f"Bienvenue, {username} !"}, username)

            # Plus d'envoi d'historique (DB supprimée)

            self._log(f"🔌 {username} s'est connecté depuis {addr[0]}:{addr[1]}")
            self._refresh_clients_ui()
            self._broadcast_clients_list()

            while self.running:
                raw = recv_packet(client_sock)
                payload = json.loads(self.cipher.decrypt(raw).decode("utf-8"))
                ptype = payload.get("type")

                if ptype == "chat":
                    mode = payload.get("mode", "broadcast")
                    targets = payload.get("targets", [])
                    text = payload.get("message", "").strip()
                    if text:
                        self._route_message(username, mode, targets, text)
                elif ptype == "ping":
                    self._send_plain(client_sock, {"type": "pong"}, username)
                else:
                    self._log(f"⚠️ Type de message inconnu reçu de {username} : {ptype}")

        except ConnectionError:
            pass
        except Exception as exc:
            self._log(f"❌ Erreur avec le client {username or addr} : {exc}")
            try:
                self._send_plain(client_sock, {"type": "error", "message": str(exc)}, username)
            except Exception:
                pass
        finally:
            if username:
                self._disconnect(username)
            else:
                try:
                    client_sock.close()
                except Exception:
                    pass

    def on_close(self):
        self.stop_server()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatServerApp(root)
    root.mainloop()
