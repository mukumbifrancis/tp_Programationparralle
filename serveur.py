import base64
import json
import os
import queue
import socket
import struct
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

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
            raise ConnectionError("La connexion avec le serveur a été interrompue.")
        buf += chunk
    return buf

def recv_packet(sock: socket.socket) -> bytes:
    header = recv_exact(sock, 4)
    (size,) = struct.unpack("!I", header)
    return recv_exact(sock, size)

class ChatClientApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Client Chat Chiffré")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        secret = os.getenv("CHAT_SECRET", "changez-moi-rapidement-123456789")
        self.cipher = Fernet(derive_fernet_key(secret))

        self.sock = None
        self.connected = False
        self.username = ""

        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.IntVar(value=5000)
        self.username_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="broadcast")

        self.incoming_queue: "queue.Queue[dict]" = queue.Queue()

        self._apply_theme()
        self._build_ui()
        self.root.after(100, self._drain_incoming)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _apply_theme(self):
        # Palette claire moderne (identique au serveur)
        self.colors = {
            "bg": "#f8fafc",
            "surface": "#ffffff",
            "surface_light": "#f1f5f9",
            "text": "#0f172a",
            "text_secondary": "#475569",
            "accent": "#8b5cf6",
            "accent_hover": "#7c3aed",
            "success": "#22c55e",
            "warning": "#f97316",
            "danger": "#ef4444",
            "danger_hover": "#dc2626",
            "border": "#cbd5e1",
            "chat_bg": "#ffffff",
            "chat_text": "#0f172a",
            "my_message_bg": "#8b5cf6",
            "my_message_text": "#ffffff",
            "other_message_bg": "#f1f5f9",
            "other_message_text": "#0f172a",
            "private_message_bg": "#fef3c7",
            "private_message_text": "#92400e",
            "group_message_bg": "#ede9fe",
            "group_message_text": "#4c1d95",
            "group_message_border": "#8b5cf6",
            "timestamp": "#64748b",
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

        # Buttons
        style.configure("Accent.TButton",
                        background=self.colors["accent"],
                        foreground="#ffffff",
                        borderwidth=0,
                        focuscolor="none",
                        font=("Inter", 10, "bold"),
                        padding=(16, 8))
        style.map("Accent.TButton",
                  background=[("active", self.colors["accent_hover"]),
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

        # Radiobutton
        style.configure("TRadiobutton",
                        background=self.colors["surface"],
                        foreground=self.colors["text"],
                        focuscolor="none",
                        font=("Inter", 10))
        style.map("TRadiobutton",
                  background=[("active", self.colors["surface"])])

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
        ttk.Label(title_frame, text="🔐", style="Title.TLabel", font=("Inter", 20)).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(title_frame, text="SecureChat", style="Title.TLabel").pack(side=tk.LEFT)

        self.status_badge = tk.Label(
            header,
            text="● Hors ligne",
            bg=self.colors["surface"],
            fg=self.colors["text_secondary"],
            font=("Inter", 11),
        )
        self.status_badge.pack(side=tk.RIGHT)

        # Login frame
        self.login_frame = ttk.LabelFrame(self.root, text="Connexion", padding="20")
        self.login_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))

        login_grid = ttk.Frame(self.login_frame, style="Surface.TFrame")
        login_grid.pack(fill=tk.X)
        login_grid.columnconfigure(1, weight=2)
        login_grid.columnconfigure(3, weight=1)
        login_grid.columnconfigure(5, weight=3)

        ttk.Label(login_grid, text="Serveur", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        host_entry = ttk.Entry(login_grid, textvariable=self.host_var)
        host_entry.grid(row=0, column=1, padx=(0, 16), pady=5, sticky="ew")

        ttk.Label(login_grid, text="Port", style="Subtitle.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=5)
        port_entry = ttk.Entry(login_grid, textvariable=self.port_var)
        port_entry.grid(row=0, column=3, padx=(0, 16), pady=5, sticky="ew")

        ttk.Label(login_grid, text="Utilisateur", style="Subtitle.TLabel").grid(row=0, column=4, sticky="w", padx=(0, 8), pady=5)
        username_entry = ttk.Entry(login_grid, textvariable=self.username_var)
        username_entry.grid(row=0, column=5, pady=5, sticky="ew")

        button_frame = ttk.Frame(login_grid, style="Surface.TFrame")
        button_frame.grid(row=1, column=0, columnspan=6, pady=(12, 0), sticky="e")

        self.connect_btn = ttk.Button(
            button_frame,
            text="Se connecter",
            command=self.connect,
            style="Accent.TButton",
        )
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.disconnect_btn = ttk.Button(
            button_frame,
            text="Se déconnecter",
            command=self.disconnect,
            style="Danger.TButton",
        )
        self.disconnect_btn.pack(side=tk.LEFT)

        # Zone principale
        main_container = ttk.Frame(self.root, style="Surface.TFrame")
        main_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        main_container.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)

        main_pane = ttk.Panedwindow(main_container, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky="nsew")

        # Panneau gauche - Conversation
        left_panel = ttk.Frame(main_pane, style="Surface.TFrame")
        chat_frame = ttk.LabelFrame(left_panel, text="Conversation", padding="16")
        chat_frame.pack(fill=tk.BOTH, expand=True)
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        chat_area = ttk.Frame(chat_frame, style="Surface.TFrame")
        chat_area.grid(row=0, column=0, sticky="nsew")
        chat_area.columnconfigure(0, weight=1)
        chat_area.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            chat_area,
            bg=self.colors["chat_bg"],
            highlightthickness=0,
            bd=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(chat_area, command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.messages_frame = ttk.Frame(self.canvas, style="Surface.TFrame")
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")

        self.messages_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Zone d'envoi
        send_container = ttk.Frame(chat_frame, style="Surface.TFrame")
        send_container.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        send_container.columnconfigure(0, weight=1)

        self.message_entry = ttk.Entry(send_container)
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12), ipady=5)
        self.message_entry.bind("<Return>", lambda _: self.send_message())
        self.message_entry.configure(style="TEntry")

        self.send_btn = ttk.Button(
            send_container,
            text="Envoyer",
            command=self.send_message,
            style="Accent.TButton",
        )
        self.send_btn.grid(row=0, column=1, sticky="e")

        # Panneau droit - Routage
        right_panel = ttk.Frame(main_pane, style="Surface.TFrame")
        routing_frame = ttk.LabelFrame(right_panel, text="Routage", padding="16")
        routing_frame.pack(fill=tk.BOTH, expand=True)
        routing_frame.columnconfigure(0, weight=1)
        routing_frame.rowconfigure(3, weight=1)

        # Modes
        modes_frame = ttk.Frame(routing_frame, style="Surface.TFrame")
        modes_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        ttk.Radiobutton(
            modes_frame,
            text="📢 Broadcast",
            variable=self.mode_var,
            value="broadcast",
            style="TRadiobutton",
        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(
            modes_frame,
            text="🔒 Privé",
            variable=self.mode_var,
            value="private",
            style="TRadiobutton",
        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(
            modes_frame,
            text="👥 Groupe",
            variable=self.mode_var,
            value="group",
            style="TRadiobutton",
        ).pack(anchor="w", pady=2)

        separator = tk.Frame(routing_frame, height=1, bg=self.colors["border"])
        separator.grid(row=1, column=0, sticky="ew", pady=12)

        # Liste des clients
        client_header = ttk.Frame(routing_frame, style="Surface.TFrame")
        client_header.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(
            client_header,
            text="👤 Clients disponibles",
            style="Subtitle.TLabel",
            font=("Inter", 11, "bold"),
        ).pack(side=tk.LEFT)
        self.client_count = ttk.Label(client_header, text="(0)", style="Subtitle.TLabel")
        self.client_count.pack(side=tk.LEFT, padx=(4, 0))

        listbox_area = ttk.Frame(routing_frame, style="Surface.TFrame")
        listbox_area.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        listbox_area.columnconfigure(0, weight=1)
        listbox_area.rowconfigure(0, weight=1)

        self.targets_listbox = tk.Listbox(
            listbox_area,
            selectmode=tk.MULTIPLE,
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
        self.targets_listbox.grid(row=0, column=0, sticky="nsew")
        listbox_scroll = ttk.Scrollbar(listbox_area, command=self.targets_listbox.yview)
        listbox_scroll.grid(row=0, column=1, sticky="ns")
        self.targets_listbox.config(yscrollcommand=listbox_scroll.set)

        ttk.Label(
            routing_frame,
            text="💡 Mode privé: 1 sélection\n👥 Mode groupe: 2+ sélections",
            style="Subtitle.TLabel",
            justify=tk.LEFT,
        ).grid(row=4, column=0, sticky="w", pady=(8, 0))

        main_pane.add(left_panel, weight=4)
        main_pane.add(right_panel, weight=2)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _create_message_bubble(self, text, sender, timestamp, is_me, mode="broadcast"):
        message_container = ttk.Frame(self.messages_frame, style="Surface.TFrame")
        message_container.pack(fill=tk.X, pady=(0, 8))

        bubble_frame = ttk.Frame(message_container, style="Surface.TFrame")
        if is_me:
            bubble_frame.pack(side=tk.RIGHT, padx=(50, 10), anchor="e")
        else:
            bubble_frame.pack(side=tk.LEFT, padx=(10, 50), anchor="w")

        header_frame = ttk.Frame(bubble_frame, style="Surface.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 2))

        mode_icons = {
            "broadcast": "📢",
            "private": "🔒",
            "group": "👥",
            "system": "ℹ️",
            "error": "❌"
        }
        mode_labels = {
            "broadcast": "Broadcast",
            "private": "Privé",
            "group": "Groupe",
            "system": "Système",
            "error": "Erreur"
        }
        icon = mode_icons.get(mode, "💬")
        mode_label = mode_labels.get(mode, "Message")

        name_label = tk.Label(
            header_frame,
            text=f"{icon} {sender} · {mode_label}",
            bg=self.colors["surface"] if not is_me else self.colors["surface"],
            fg=self.colors["accent"] if not is_me else self.colors["accent"],
            font=("Inter", 9, "bold"),
            anchor="w"
        )
        name_label.pack(side=tk.LEFT, padx=(0, 8))

        time_label = tk.Label(
            header_frame,
            text=timestamp,
            bg=self.colors["surface"] if not is_me else self.colors["surface"],
            fg=self.colors["timestamp"],
            font=("Inter", 8)
        )
        time_label.pack(side=tk.RIGHT)

        border_color = None
        if mode == "group":
            bubble_bg = self.colors["group_message_bg"]
            bubble_fg = self.colors["group_message_text"]
            border_color = self.colors["group_message_border"]
        elif is_me:
            bubble_bg = self.colors["my_message_bg"]
            bubble_fg = self.colors["my_message_text"]
        else:
            if mode == "private":
                bubble_bg = self.colors["private_message_bg"]
                bubble_fg = self.colors["private_message_text"]
            else:
                bubble_bg = self.colors["other_message_bg"]
                bubble_fg = self.colors["other_message_text"]

        message_label = tk.Label(
            bubble_frame,
            text=text,
            bg=bubble_bg,
            fg=bubble_fg,
            font=("Inter", 11),
            wraplength=400,
            justify=tk.LEFT,
            padx=12,
            pady=8,
            highlightthickness=1 if border_color else 0,
            highlightbackground=border_color if border_color else bubble_bg,
            highlightcolor=border_color if border_color else bubble_bg
        )
        message_label.pack(fill=tk.X, pady=(0, 2))

        self.messages_frame.update_idletasks()

    def _update_client_count(self):
        count = self.targets_listbox.size()
        self.client_count.config(text=f"({count})")

    def _encrypt_payload(self, payload: dict) -> bytes:
        raw = json.dumps(payload).encode("utf-8")
        return self.cipher.encrypt(raw)

    def _send_payload(self, payload: dict):
        if not self.connected or not self.sock:
            raise ConnectionError("Vous n'êtes pas connecté au serveur.")
        send_packet(self.sock, self._encrypt_payload(payload))

    def connect(self):
        if self.connected:
            return

        host = self.host_var.get().strip()
        port = self.port_var.get()
        username = self.username_var.get().strip()

        if not username:
            messagebox.showerror("Erreur", "Vous devez spécifier un nom d'utilisateur.")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, int(port)))
            send_packet(self.sock, self._encrypt_payload({"type": "auth", "username": username}))

            auth_reply = json.loads(self.cipher.decrypt(recv_packet(self.sock)).decode("utf-8"))
            if auth_reply.get("type") == "auth_ok":
                self.connected = True
                self.username = username

                self.status_badge.config(text="● Connecté", fg=self.colors["success"])
                self._create_message_bubble(
                    f"Vous êtes connecté en tant que {username}",
                    "Système",
                    datetime.now().strftime("%H:%M"),
                    False,
                    "system"
                )

                threading.Thread(target=self._recv_loop, daemon=True).start()
            else:
                msg = auth_reply.get("message", "L'authentification a échoué.")
                self.sock.close()
                self.sock = None
                messagebox.showerror("Erreur", msg)
        except Exception as exc:
            messagebox.showerror("Erreur de connexion au serveur", str(exc))
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

    def disconnect(self):
        if not self.connected:
            return
        self.connected = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.status_badge.config(text="● Hors ligne", fg=self.colors["text_secondary"])
        self.targets_listbox.delete(0, tk.END)
        self._update_client_count()
        self._create_message_bubble(
            "Vous avez été déconnecté.",
            "Système",
            datetime.now().strftime("%H:%M"),
            False,
            "system"
        )

    def _recv_loop(self):
        try:
            while self.connected and self.sock:
                packet = recv_packet(self.sock)
                data = json.loads(self.cipher.decrypt(packet).decode("utf-8"))
                self.incoming_queue.put(data)
        except Exception as exc:
            self.incoming_queue.put({"type": "system", "message": f"Connexion au serveur perdue : {exc}"})
        finally:
            self.connected = False
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

    def _drain_incoming(self):
        while not self.incoming_queue.empty():
            data = self.incoming_queue.get_nowait()
            ptype = data.get("type")

            if ptype == "chat":
                sender = data.get("sender", "?")
                mode = data.get("mode", "broadcast")
                text = data.get("message", "")
                ts = data.get("timestamp", datetime.now().strftime("%H:%M"))

                is_me = (sender == self.username)
                self._create_message_bubble(text, sender, ts, is_me, mode)

            elif ptype == "clients":
                clients = data.get("clients", [])
                self.targets_listbox.delete(0, tk.END)
                for user in clients:
                    self.targets_listbox.insert(tk.END, user)
                self._update_client_count()

            elif ptype == "history":
                messages = data.get("messages", [])
                if messages:
                    self._create_message_bubble(
                        "Historique des messages chargé",
                        "Système",
                        datetime.now().strftime("%H:%M"),
                        False,
                        "system"
                    )
                    for item in messages:
                        ts = item.get("timestamp", "")
                        sender = item.get("sender", "?")
                        mode = item.get("mode", "broadcast")
                        text = item.get("message", "")
                        is_me = (sender == self.username)
                        self._create_message_bubble(text, sender, ts, is_me, mode)

            elif ptype == "error":
                self._create_message_bubble(
                    f"Erreur : {data.get('message', 'Erreur inconnue')}",
                    "Système",
                    datetime.now().strftime("%H:%M"),
                    False,
                    "error"
                )

            elif ptype == "system":
                self._create_message_bubble(
                    data.get('message', ''),
                    "Système",
                    datetime.now().strftime("%H:%M"),
                    False,
                    "system"
                )

            elif ptype == "pong":
                pass

        self.canvas.yview_moveto(1.0)
        self.root.after(100, self._drain_incoming)

    def send_message(self):
        if not self.connected:
            messagebox.showwarning("Info", "Veuillez vous connecter avant d'envoyer un message.")
            return

        text = self.message_entry.get().strip()
        if not text:
            return

        mode = self.mode_var.get()
        selected_indexes = self.targets_listbox.curselection()
        selected_users = [self.targets_listbox.get(i) for i in selected_indexes]

        if mode == "private" and len(selected_users) != 1:
            messagebox.showwarning("Routage", "Pour un message privé, veuillez sélectionner un seul destinataire.")
            return

        if mode == "group" and len(selected_users) < 2:
            messagebox.showwarning("Routage", "Pour un message de groupe, sélectionnez au moins deux destinataires.")
            return

        payload = {
            "type": "chat",
            "mode": mode,
            "targets": selected_users,
            "message": text,
        }

        try:
            self._send_payload(payload)

            self._create_message_bubble(
                text,
                self.username,
                datetime.now().strftime("%H:%M"),
                True,
                mode
            )

            self.message_entry.delete(0, tk.END)
            self.canvas.yview_moveto(1.0)

        except Exception as exc:
            messagebox.showerror("Échec de l'envoi du message", str(exc))

    def on_close(self):
        self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientApp(root)
    root.mainloop()
