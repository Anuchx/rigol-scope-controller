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


# ---------- ค่าคงที่ของ scope ----------
# V/div ของ RIGOL เป็น step แบบ 1-2-5 ไม่ใช่ค่าต่อเนื่อง
# ป้อนค่ามั่วไม่ได้ scope จะปัดเป็น step ที่ใกล้ที่สุดเอง
VDIV_STEPS = [
    ("1 mV", 0.001), ("2 mV", 0.002), ("5 mV", 0.005),
    ("10 mV", 0.01), ("20 mV", 0.02), ("50 mV", 0.05),
    ("100 mV", 0.1), ("200 mV", 0.2), ("500 mV", 0.5),
    ("1 V", 1.0), ("2 V", 2.0), ("5 V", 5.0), ("10 V", 10.0),
]

# time/div ของ MSO1000Z: 5 ns/div ถึง 10 s/div
TDIV_STEPS = [
    ("5 ns", 5e-9), ("10 ns", 1e-8), ("20 ns", 2e-8), ("50 ns", 5e-8),
    ("100 ns", 1e-7), ("200 ns", 2e-7), ("500 ns", 5e-7),
    ("1 us", 1e-6), ("2 us", 2e-6), ("5 us", 5e-6),
    ("10 us", 1e-5), ("20 us", 2e-5), ("50 us", 5e-5),
    ("100 us", 1e-4), ("200 us", 2e-4), ("500 us", 5e-4),
    ("1 ms", 1e-3), ("2 ms", 2e-3), ("5 ms", 5e-3),
    ("10 ms", 0.01), ("20 ms", 0.02), ("50 ms", 0.05),
    ("100 ms", 0.1), ("200 ms", 0.2), ("500 ms", 0.5),
    ("1 s", 1.0), ("2 s", 2.0), ("5 s", 5.0), ("10 s", 10.0),
]

COUPLING_MODES = ["DC", "AC", "GND"]

# สีประจำ channel ตามหน้าจอ scope จริง
CHANNEL_COLORS = {
    1: "#c9a227",   # เหลือง
    2: "#2e9e9e",   # ฟ้า
    3: "#c04585",   # ชมพู
    4: "#4a76c4",   # น้ำเงิน
}


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

    # ---------- channel control ----------

    def set_channel_display(self, ch, on):
        """เปิด/ปิดการแสดง channel บนหน้าจอ scope"""
        self.write(f":CHAN{ch}:DISP {'ON' if on else 'OFF'}")

    def get_channel_display(self, ch):
        """อ่านว่า channel เปิดอยู่หรือไม่ scope คืน 1/0"""
        return self.query(f":CHAN{ch}:DISP?") in ("1", "ON")

    def set_vdiv(self, ch, volts):
        """ตั้ง V/div ของ channel scope จะปัดเป็น step 1-2-5 ที่ใกล้สุดเอง"""
        self.write(f":CHAN{ch}:SCAL {volts}")

    def get_vdiv(self, ch):
        return float(self.query(f":CHAN{ch}:SCAL?"))

    def set_offset(self, ch, volts):
        """ตั้ง vertical offset ของ channel"""
        self.write(f":CHAN{ch}:OFFS {volts}")

    def get_offset(self, ch):
        return float(self.query(f":CHAN{ch}:OFFS?"))

    def set_coupling(self, ch, mode):
        """ตั้ง coupling DC/AC/GND"""
        self.write(f":CHAN{ch}:COUP {mode}")

    def get_coupling(self, ch):
        return self.query(f":CHAN{ch}:COUP?")

    # ---------- horizontal (timebase) ----------

    def set_tdiv(self, seconds):
        """ตั้ง time/div ของแกนนอน"""
        self.write(f":TIM:SCAL {seconds}")

    def get_tdiv(self):
        return float(self.query(":TIM:SCAL?"))

    def set_time_offset(self, seconds):
        """ตั้งตำแหน่งแกนเวลา (trigger position)"""
        self.write(f":TIM:OFFS {seconds}")

    def get_time_offset(self):
        return float(self.query(":TIM:OFFS?"))


def nearest_step(value, steps):
    """หา step ที่ใกล้ค่าที่ให้มาที่สุด คืน label ของ step นั้น"""
    return min(steps, key=lambda s: abs(s[1] - value))[0]


class ChannelPanel(ttk.LabelFrame):
    """
    การ์ดควบคุม 1 channel มีปุ่มเปิด/ปิด, V/div, offset, coupling
    แยกเป็นคลาสเพราะต้องสร้าง 4 ชุดเหมือนกัน
    """

    def __init__(self, parent, app, ch):
        super().__init__(parent, text=f"CH{ch}", padding=8)
        self.app = app
        self.ch = ch
        self._build()

    def _build(self):
        self.columnconfigure(1, weight=1)

        # checkbox เปิด/ปิดการแสดงผลบนหน้าจอ scope
        self.on_var = tk.BooleanVar(value=(self.ch == 1))
        ttk.Checkbutton(self, text="Display", variable=self.on_var,
                        command=self.on_toggle).grid(row=0, column=0,
                                                     columnspan=2, sticky="w",
                                                     pady=(0, 4))

        # V/div เป็น combobox เพราะ scope รับเฉพาะ step 1-2-5
        ttk.Label(self, text="V/div").grid(row=1, column=0, sticky="w")
        self.vdiv_var = tk.StringVar(value="1 V")
        vdiv = ttk.Combobox(self, textvariable=self.vdiv_var, width=8,
                            state="readonly", values=[s[0] for s in VDIV_STEPS])
        vdiv.grid(row=1, column=1, sticky="ew", pady=1)
        vdiv.bind("<<ComboboxSelected>>", lambda e: self.on_vdiv())

        # Offset ป้อนค่าเองได้เพราะเป็นค่าต่อเนื่อง ไม่ใช่ step
        ttk.Label(self, text="Offset").grid(row=2, column=0, sticky="w")
        self.offset_var = tk.StringVar(value="0")
        offs = ttk.Entry(self, textvariable=self.offset_var, width=8)
        offs.grid(row=2, column=1, sticky="ew", pady=1)
        offs.bind("<Return>", lambda e: self.on_offset())

        # Coupling
        ttk.Label(self, text="Coupling").grid(row=3, column=0, sticky="w")
        self.coup_var = tk.StringVar(value="DC")
        coup = ttk.Combobox(self, textvariable=self.coup_var, width=8,
                            state="readonly", values=COUPLING_MODES)
        coup.grid(row=3, column=1, sticky="ew", pady=1)
        coup.bind("<<ComboboxSelected>>", lambda e: self.on_coupling())

    # ---------- event ของ channel นี้ ----------

    def on_toggle(self):
        on = self.on_var.get()
        self.app.safe_call(
            lambda: self.app.ctrl.set_channel_display(self.ch, on),
            f"CH{self.ch} display {'ON' if on else 'OFF'}")

    def on_vdiv(self):
        volts = dict(VDIV_STEPS)[self.vdiv_var.get()]
        self.app.safe_call(
            lambda: self.app.ctrl.set_vdiv(self.ch, volts),
            f"CH{self.ch} V/div = {self.vdiv_var.get()}")

    def on_offset(self):
        try:
            volts = float(self.offset_var.get())
        except ValueError:
            self.app.log(f"CH{self.ch} offset ต้องเป็นตัวเลข")
            return
        self.app.safe_call(
            lambda: self.app.ctrl.set_offset(self.ch, volts),
            f"CH{self.ch} offset = {volts} V")

    def on_coupling(self):
        mode = self.coup_var.get()
        self.app.safe_call(
            lambda: self.app.ctrl.set_coupling(self.ch, mode),
            f"CH{self.ch} coupling = {mode}")

    def sync_from_scope(self):
        """อ่านค่าจริงจาก scope มาใส่ใน widget ให้ตรงกัน"""
        ctrl = self.app.ctrl
        self.on_var.set(ctrl.get_channel_display(self.ch))
        self.vdiv_var.set(nearest_step(ctrl.get_vdiv(self.ch), VDIV_STEPS))
        self.offset_var.set(f"{ctrl.get_offset(self.ch):g}")
        self.coup_var.set(ctrl.get_coupling(self.ch))


class App:
    """GUI ด้วย Tkinter คุยกับ scope ผ่าน ScopeController เท่านั้น"""

    def __init__(self, root):
        self.root = root
        self.ctrl = ScopeController()
        self.is_running = True      # เก็บ state RUN/STOP ไว้ให้ปุ่ม toggle
        self.channels = {}          # เก็บ ChannelPanel ทั้ง 4

        root.title("RIGOL Scope Controller")
        root.geometry("940x680")
        root.minsize(880, 620)

        self._build_ui()
        self.log("พร้อมใช้งาน กด SEARCH เพื่อหา instruments")

    # ---------- โครงหลัก ----------

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)   # ฝั่งซ้ายยืดได้
        self.root.rowconfigure(0, weight=1)

        left = ttk.Frame(self.root, padding=(10, 10, 5, 10))
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        left.rowconfigure(2, weight=1)

        right = ttk.Frame(self.root, padding=(5, 10, 10, 10))
        right.grid(row=0, column=1, sticky="ns")

        self._build_connection(left)
        self._build_command(left)
        self._build_log(left)

        self._build_channels(right)
        self._build_timebase(right)
        self._build_acquisition(right)

    def _build_connection(self, parent):
        frame = ttk.LabelFrame(parent, text="Instrument Connection", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure(0, weight=1)

        # readonly = เลือกได้จาก list ที่ search เจอ พิมพ์เองไม่ได้
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(frame, textvariable=self.device_var,
                                         state="readonly", font=("Consolas", 9))
        self.device_combo.grid(row=0, column=0, columnspan=4, sticky="ew",
                               pady=(0, 6))

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

    def _build_command(self, parent):
        frame = ttk.LabelFrame(parent, text="SCPI Command", padding=8)
        frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        row = ttk.Frame(frame)
        row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        row.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(row, font=("Consolas", 10))
        self.entry.insert(0, "*IDN?")   # default value ให้เห็น format
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda e: self.on_send())   # Enter = SEND

        ttk.Button(row, text="SEND", width=8,
                   command=self.on_send).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(row, text="CLEAR", width=8,
                   command=self.on_clear).grid(row=0, column=2, padx=(4, 0))

        self.response = scrolledtext.ScrolledText(frame, height=8,
                                                  font=("Consolas", 9),
                                                  bg="#1e2530", fg="#d8dee8",
                                                  insertbackground="#d8dee8")
        self.response.grid(row=1, column=0, sticky="nsew")

    def _build_log(self, parent):
        frame = ttk.LabelFrame(parent, text="System Log", padding=8)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # disabled = user แก้ไม่ได้ code จะ enable ชั่วคราวตอนเขียน
        self.log_box = scrolledtext.ScrolledText(frame, height=8,
                                                 font=("Consolas", 8),
                                                 state="disabled")
        self.log_box.grid(row=0, column=0, sticky="nsew")

    # ---------- ฝั่งขวา: channel + timebase ----------

    def _build_channels(self, parent):
        """สร้างการ์ดควบคุม 4 channel วนลูปเพราะหน้าตาเหมือนกันหมด"""
        for ch in (1, 2, 3, 4):
            panel = ChannelPanel(parent, self, ch)
            panel.grid(row=ch - 1, column=0, sticky="ew", pady=(0, 6))
            self.channels[ch] = panel

    def _build_timebase(self, parent):
        frame = ttk.LabelFrame(parent, text="Horizontal", padding=8)
        frame.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        frame.columnconfigure(1, weight=1)

        # time/div เป็น step เหมือน V/div เลยใช้ combobox
        ttk.Label(frame, text="Time/div").grid(row=0, column=0, sticky="w")
        self.tdiv_var = tk.StringVar(value="1 ms")
        tdiv = ttk.Combobox(frame, textvariable=self.tdiv_var, width=8,
                            state="readonly", values=[s[0] for s in TDIV_STEPS])
        tdiv.grid(row=0, column=1, sticky="ew", pady=1)
        tdiv.bind("<<ComboboxSelected>>", lambda e: self.on_tdiv())

        # offset เป็นค่าต่อเนื่อง ป้อนเองได้
        ttk.Label(frame, text="Offset").grid(row=1, column=0, sticky="w")
        self.toffs_var = tk.StringVar(value="0")
        toffs = ttk.Entry(frame, textvariable=self.toffs_var, width=8)
        toffs.grid(row=1, column=1, sticky="ew", pady=1)
        toffs.bind("<Return>", lambda e: self.on_time_offset())

    def _build_acquisition(self, parent):
        frame = ttk.LabelFrame(parent, text="Acquisition", padding=8)
        frame.grid(row=5, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Button(frame, text="RUN / STOP",
                   command=self.on_run_stop).grid(row=0, column=0, columnspan=2,
                                                  sticky="ew", pady=(0, 4))
        ttk.Button(frame, text="AUTO",
                   command=self.on_autoscale).grid(row=1, column=0, sticky="ew",
                                                   padx=(0, 2))
        ttk.Button(frame, text="SYNC",
                   command=self.on_sync).grid(row=1, column=1, sticky="ew",
                                              padx=(2, 0))

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

    def safe_call(self, fn, success_msg):
        """
        เรียก fn ที่คุยกับ scope พร้อมจับ error ให้
        ใช้ร่วมกันได้ทุกปุ่ม จะได้ไม่ต้องเขียน try/except ซ้ำ
        """
        if not self.ctrl.is_connected():
            self.log("ยังไม่ได้ connect")
            return False
        try:
            fn()
            self.log(success_msg)
            return True
        except Exception as e:
            self.log(f"ผิดพลาด: {e}")
            return False

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
            self.on_sync()      # ดึงค่าปัจจุบันจาก scope มาแสดงทันที

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

    def on_run_stop(self):
        """toggle RUN/STOP ตาม state ที่เก็บไว้"""
        cmd = ":STOP" if self.is_running else ":RUN"
        if self.safe_call(lambda: self.ctrl.write(cmd), f"TX > {cmd}"):
            self.is_running = not self.is_running

    def on_autoscale(self):
        """สั่ง scope ปรับ scale ให้พอดีสัญญาณเอง แล้ว sync ค่ากลับมา"""
        if self.safe_call(lambda: self.ctrl.write(":AUT"), "TX > :AUT (autoscale)"):
            self.root.after(2000, self.on_sync)   # รอ scope ปรับเสร็จก่อน sync

    def on_tdiv(self):
        seconds = dict(TDIV_STEPS)[self.tdiv_var.get()]
        self.safe_call(lambda: self.ctrl.set_tdiv(seconds),
                       f"Time/div = {self.tdiv_var.get()}")

    def on_time_offset(self):
        try:
            seconds = float(self.toffs_var.get())
        except ValueError:
            self.log("Time offset ต้องเป็นตัวเลข")
            return
        self.safe_call(lambda: self.ctrl.set_time_offset(seconds),
                       f"Time offset = {seconds} s")

    def on_sync(self):
        """
        อ่านค่าจริงจาก scope มาใส่ widget ให้ตรงกัน
        จำเป็นเพราะถ้าไปหมุนปุ่มที่ตัว scope เอง GUI จะไม่รู้
        """
        if not self.ctrl.is_connected():
            self.log("ยังไม่ได้ connect")
            return

        try:
            for panel in self.channels.values():
                panel.sync_from_scope()

            self.tdiv_var.set(nearest_step(self.ctrl.get_tdiv(), TDIV_STEPS))
            self.toffs_var.set(f"{self.ctrl.get_time_offset():g}")
            self.log("Sync ค่าจาก scope เรียบร้อย")

        except Exception as e:
            self.log(f"Sync ไม่สำเร็จ: {e}")

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