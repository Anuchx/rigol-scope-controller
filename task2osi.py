"""
RIGOL Scope Controller - Python/Tkinter GUI
Software Development Practice 1 - Task 2

"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

try:
    import pyvisa
except ImportError:
    pyvisa = None


class ScopeController:
    """จัดการ VISA/SCPI communication ทั้งหมด ไม่มี GUI code"""

    def __init__(self, backend="@py", timeout=2000):
        self.backend = backend      # "@py" = pyvisa-py backend ไม่ต้องลง NI-VISA
        self.timeout = timeout      # timeout รอ response (ms)
        self.rm = None              # VISA ResourceManager
        self.scope = None           # instrument ที่เปิดอยู่ None = ยังไม่ connect

    def is_connected(self):
        return self.scope is not None

    def search(self):
        """คืน list ของ USB instruments ที่ต่ออยู่"""
        if pyvisa is None:
            raise RuntimeError("ยังไม่ได้ install pyvisa")

        if self.rm is None:
            self.rm = pyvisa.ResourceManager(self.backend)

        # list_resources() คืน TCPIP/ASRL มาด้วย filter เอาแค่ USB
        return [r for r in self.rm.list_resources() if r.startswith("USB")]

    def connect(self, resource):
        """เปิด connection ตาม resource string เช่น USB0::0x1AB1::0x0588::...::INSTR"""
        if pyvisa is None:
            raise RuntimeError("ยังไม่ได้ install pyvisa")

        if self.rm is None:
            self.rm = pyvisa.ResourceManager(self.backend)

        self.scope = self.rm.open_resource(resource)
        self.scope.timeout = self.timeout
        return resource

    def disconnect(self):
        """ปิด instrument และ release resource manager"""
        if self.scope is not None:
            self.scope.close()
            self.scope = None
        if self.rm is not None:
            self.rm.close()
            self.rm = None

    def write(self, command):
        """ส่ง command ไม่รอ response เช่น :RUN, :STOP"""
        if not self.is_connected():
            raise RuntimeError("ยังไม่ได้ connect")
        self.scope.write(command)

    def query(self, command):
        """ส่ง command แล้วรอ response เช่น *IDN?"""
        if not self.is_connected():
            raise RuntimeError("ยังไม่ได้ connect")
        return self.scope.query(command).strip()


class App:
    """GUI ด้วย Tkinter คุยกับ scope ผ่าน ScopeController เท่านั้น"""

    def __init__(self, root):
        self.root = root
        self.ctrl = ScopeController()

        root.title("Python/Tkinter Simple RIGOL Controller")
        root.geometry("760x620")
        root.minsize(680, 540)

        self._build_ui()
        self.log("พร้อมใช้งาน กด SEARCH เพื่อหา instruments")

    # ---------- สร้าง GUI ----------

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)   # Response resize ตาม window
        self.root.rowconfigure(3, weight=1)   # Log resize ด้วย

        self._build_connection_frame()
        self._build_command_frame()
        self._build_response_frame()
        self._build_log_frame()

    def _build_connection_frame(self):
        frame = ttk.LabelFrame(self.root, text="1. Instrument Connection",
                               padding=10)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        frame.columnconfigure(0, weight=1)

        # readonly = เลือกได้จาก list ที่ search เจอ พิมพ์เองไม่ได้
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(frame, textvariable=self.device_var,
                                         state="readonly", font=("Consolas", 9))
        self.device_combo.grid(row=0, column=0, columnspan=4, sticky="ew",
                               pady=(0, 8))

        ttk.Button(frame, text="SEARCH", width=11,
                   command=self.on_search).grid(row=1, column=0, sticky="w")

        self.btn_connect = ttk.Button(frame, text="CONNECT", width=11,
                                      command=self.on_connect)
        self.btn_connect.grid(row=1, column=1, padx=4)

        # เริ่มต้น disabled เพราะยังไม่มีอะไรให้ disconnect
        self.btn_disconnect = ttk.Button(frame, text="DISCONNECT", width=12,
                                         command=self.on_disconnect,
                                         state="disabled")
        self.btn_disconnect.grid(row=1, column=2, padx=4)

        self.status_label = ttk.Label(frame, text="DISCONNECTED",
                                      foreground="#a33",
                                      font=("Segoe UI", 9, "bold"))
        self.status_label.grid(row=1, column=3, sticky="e", padx=(8, 0))

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
        frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.response = scrolledtext.ScrolledText(frame, height=7,
                                                  font=("Consolas", 10),
                                                  bg="#1e2530", fg="#d8dee8",
                                                  insertbackground="#d8dee8")
        self.response.grid(row=0, column=0, sticky="nsew")

        ttk.Button(frame, text="CLEAR", width=10,
                   command=self.on_clear).grid(row=1, column=0, sticky="e",
                                               pady=(8, 0))

    def _build_log_frame(self):
        frame = ttk.LabelFrame(self.root, text="4. System Log", padding=10)
        frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # disabled = user แก้ไม่ได้ code จะ enable ชั่วคราวตอนเขียน
        self.log_box = scrolledtext.ScrolledText(frame, height=6,
                                                 font=("Consolas", 9),
                                                 state="disabled")
        self.log_box.grid(row=0, column=0, sticky="nsew")

    # ---------- helper ----------

    def log(self, message):
        """เขียน message ลง System Log พร้อม timestamp"""
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"[{stamp}] {message}\n")
        self.log_box.see("end")             # auto-scroll ไปบรรทัดล่าสุด
        self.log_box.config(state="disabled")

    def show_response(self, text):
        self.response.insert("end", text + "\n")
        self.response.see("end")

    def set_status(self, connected):
        """update status label และสลับว่าปุ่มไหน enable"""
        if connected:
            self.status_label.config(text="CONNECTED", foreground="#2e8043")
            self.btn_connect.config(state="disabled")
            self.btn_disconnect.config(state="normal")
        else:
            self.status_label.config(text="DISCONNECTED", foreground="#a33")
            self.btn_connect.config(state="normal")
            self.btn_disconnect.config(state="disabled")

    # ---------- event handlers ----------

    def on_search(self):
        self.log("กำลัง search VISA instruments...")
        try:
            devices = self.ctrl.search()
            if not devices:
                self.log("ไม่พบ USB instrument เช็คสาย USB และ libusb driver (Zadig)")
                return

            self.device_combo["values"] = devices
            self.device_combo.current(0)    # select ตัวแรกให้อัตโนมัติ
            self.log(f"พบ {len(devices)} devices: {devices[0]}")

        except Exception as e:
            self.log(f"Search ไม่สำเร็จ: {e}")

    def on_connect(self):
        resource = self.device_var.get()
        if not resource:
            self.log("ยังไม่ได้เลือก device กด SEARCH ก่อน")
            return

        try:
            self.ctrl.connect(resource)
            self.set_status(True)
            self.log(f"Connected: {resource}")

        except Exception as e:
            self.set_status(False)
            self.log(f"Connect ไม่สำเร็จ: {e}")

    def on_disconnect(self):
        try:
            self.ctrl.disconnect()
            self.set_status(False)
            self.log("Disconnected")

        except Exception as e:
            self.log(f"Disconnect error: {e}")

    def on_send(self):
        command = self.entry.get().strip()
        if not command:
            return

        self.show_response(f">>> {command}")
        self.log(f"TX > {command}")

        try:
            # command ที่มี ? คือ query ต้องรอ response นอกนั้น write อย่างเดียว
            # เช็ค "?" in ไม่ใช่ endswith เพราะบางคำสั่ง ? อยู่กลาง เช่น :MEAS:VPP? CHAN1
            if "?" in command:
                answer = self.ctrl.query(command)
                self.show_response(answer + "\n")
                self.log(f"RX < {answer}")
            else:
                self.ctrl.write(command)
                self.show_response("(sent)\n")

        except Exception as e:
            self.show_response(f"ERROR: {e}\n")
            self.log(f"Error: {e}")

    def on_clear(self):
        self.response.delete("1.0", "end")


def main():
    root = tk.Tk()
    app = App(root)

    # disconnect ให้เรียบร้อยก่อนปิด window
    def on_close():
        app.ctrl.disconnect()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()