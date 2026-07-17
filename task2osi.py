"""
RIGOL Scope Controller - Python/Tkinter GUI
Software Development Practice 1 - Task 2
"""

import tkinter as tk
from tkinter import ttk, scrolledtext


class ScopeController:
    """จัดการ VISA/SCPI communication ทั้งหมด ไม่มี GUI code"""

    def __init__(self):
        self.scope = None           # instrument ที่เปิดอยู่ None = ยังไม่ connect

    def is_connected(self):
        return self.scope is not None

    def connect(self, resource):
        """เปิด connection - ยังไม่ implement รอใส่ pyvisa"""
        pass

    def disconnect(self):
        """ปิด connection - ยังไม่ implement"""
        pass

    def write(self, command):
        """ส่ง command ไม่รอ response เช่น :RUN, :STOP"""
        pass

    def query(self, command):
        """ส่ง command แล้วรอ response เช่น *IDN?"""
        return f"(simulated) response to {command}"


class App:
    """GUI ด้วย Tkinter คุยกับ scope ผ่าน ScopeController เท่านั้น"""

    def __init__(self, root):
        self.root = root
        self.ctrl = ScopeController()

        root.title("Python/Tkinter Simple RIGOL Controller")
        root.geometry("720x520")
        root.minsize(640, 460)

        self._build_ui()

    # ---------- สร้าง GUI ----------

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)   # Response resize ตาม window

        self._build_connection_frame()
        self._build_command_frame()
        self._build_response_frame()

    def _build_connection_frame(self):
        frame = ttk.LabelFrame(self.root, text="1. Instrument Connection",
                               padding=10)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        frame.columnconfigure(2, weight=1)

        self.btn_connect = ttk.Button(frame, text="CONNECT", width=12,
                                      command=self.on_connect)
        self.btn_connect.grid(row=0, column=0)

        # เริ่มต้น disabled เพราะยังไม่มีอะไรให้ disconnect
        self.btn_disconnect = ttk.Button(frame, text="DISCONNECT", width=12,
                                         command=self.on_disconnect,
                                         state="disabled")
        self.btn_disconnect.grid(row=0, column=1, padx=8)

        self.status_label = ttk.Label(frame, text="Status: DISCONNECTED",
                                      foreground="#a33")
        self.status_label.grid(row=0, column=2, sticky="e")

    def _build_command_frame(self):
        frame = ttk.LabelFrame(self.root, text="2. SCPI Command", padding=10)
        frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Command:").grid(row=0, column=0, padx=(0, 8))

        self.entry = ttk.Entry(frame, font=("Consolas", 10))
        self.entry.insert(0, "*IDN?")   # default value ให้เห็น format
        self.entry.grid(row=0, column=1, sticky="ew")
        self.entry.bind("<Return>", lambda e: self.on_send())   # Enter = SEND

        ttk.Button(frame, text="SEND", width=10,
                   command=self.on_send).grid(row=0, column=2, padx=(8, 0))

    def _build_response_frame(self):
        frame = ttk.LabelFrame(self.root, text="3. Response", padding=10)
        frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.response = scrolledtext.ScrolledText(frame, height=10,
                                                  font=("Consolas", 10),
                                                  bg="#1e2530", fg="#d8dee8",
                                                  insertbackground="#d8dee8")
        self.response.grid(row=0, column=0, sticky="nsew")

        ttk.Button(frame, text="CLEAR", width=10,
                   command=self.on_clear).grid(row=1, column=0, sticky="e",
                                               pady=(8, 0))

    # ---------- helper ----------

    def show_response(self, text):
        self.response.insert("end", text + "\n")
        self.response.see("end")

    def set_status(self, connected):
        """update status label และสลับว่าปุ่มไหน enable"""
        if connected:
            self.status_label.config(text="Status: CONNECTED",
                                     foreground="#2e8043")
            self.btn_connect.config(state="disabled")
            self.btn_disconnect.config(state="normal")
        else:
            self.status_label.config(text="Status: DISCONNECTED",
                                     foreground="#a33")
            self.btn_connect.config(state="normal")
            self.btn_disconnect.config(state="disabled")

    # ---------- event handlers ----------

    def on_connect(self):
        self.ctrl.connect(None)
        self.set_status(True)

    def on_disconnect(self):
        self.ctrl.disconnect()
        self.set_status(False)

    def on_send(self):
        command = self.entry.get().strip()
        if not command:
            return

        self.show_response(f">>> {command}")
        answer = self.ctrl.query(command)
        self.show_response(answer + "\n")

    def on_clear(self):
        self.response.delete("1.0", "end")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()