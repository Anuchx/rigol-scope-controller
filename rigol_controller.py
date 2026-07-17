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

# time/div ของ MSO1000Z: 5 ns/div ถึง 50 s/div
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
    1: "#e8c547",   # เหลือง
    2: "#3fc4c4",   # ฟ้า
    3: "#e0559e",   # ชมพู
    4: "#5b8fe0",   # น้ำเงิน
}

# ---------- palette ของ GUI ----------
BG = "#f2f4f8"
CARD = "#ffffff"
INK = "#1f2937"
MUTED = "#6b7280"
LINE = "#d9dee7"
TERM_BG = "#161b26"
TERM_FG = "#d5dbe8"
OK = "#2e8043"
BAD = "#b3453f"


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

    # ---------- measurements ----------

    def measure(self, channel="CHAN1"):
        """
        อ่านค่าวัดพื้นฐานของ channel ที่ระบุ คืนเป็น dict
        9.9E+37 คือค่าที่ scope คืนมาเมื่อวัดไม่ได้ (ไม่มีสัญญาณ)
        """
        if not self.is_connected():
            raise RuntimeError("ยังไม่ได้ connect")

        items = [
            ("Vpp", ":MEAS:VPP?", "V"),
            ("Vmax", ":MEAS:VMAX?", "V"),
            ("Vmin", ":MEAS:VMIN?", "V"),
            ("Vavg", ":MEAS:VAVG?", "V"),
            ("Vrms", ":MEAS:VRMS?", "V"),
            ("Freq", ":MEAS:FREQ?", "Hz"),
            ("Period", ":MEAS:PER?", "s"),
            ("Duty", ":MEAS:PDUT?", "%"),
        ]

        results = {}
        for name, cmd, unit in items:
            try:
                value = float(self.query(f"{cmd} {channel}"))

                # scope คืน 9.9E+37 เมื่อวัดค่านั้นไม่ได้
                if value >= 9.9e37:
                    results[name] = ("---", unit)
                elif unit == "%":
                    # scope คืน 0.5 = 50% ไม่ต้องเติม prefix
                    results[name] = (f"{value * 100:.2f}", unit)
                else:
                    results[name] = (fmt_value(value), unit)

            except Exception:
                results[name] = ("error", unit)

        return results


def fmt_value(v):
    """แปลงเลขให้อ่านง่าย เติม prefix m/u/n/k/M ตามขนาด"""
    a = abs(v)
    if a == 0:
        return "0"
    if a >= 1e6:
        return f"{v / 1e6:.3f} M"
    if a >= 1e3:
        return f"{v / 1e3:.3f} k"
    if a >= 1:
        return f"{v:.3f} "
    if a >= 1e-3:
        return f"{v * 1e3:.3f} m"
    if a >= 1e-6:
        return f"{v * 1e6:.3f} u"
    return f"{v * 1e9:.3f} n"


def nearest_step(value, steps):
    """หา step ที่ใกล้ค่าที่ให้มาที่สุด คืน label ของ step นั้น"""
    return min(steps, key=lambda s: abs(s[1] - value))[0]


class ChannelPanel(ttk.Frame):
    """
    การ์ดควบคุม 1 channel มีปุ่มเปิด/ปิด, V/div, offset, coupling
    แยกเป็นคลาสเพราะต้องสร้าง 4 ชุดเหมือนกัน
    """

    def __init__(self, parent, app, ch):
        super().__init__(parent, style="Card.TFrame", padding=(10, 8))
        self.app = app
        self.ch = ch
        self.color = CHANNEL_COLORS[ch]
        self._build()

    def _build(self):
        self.columnconfigure(1, weight=1)

        # แถบสีประจำ channel ทางซ้าย ทำให้แยก channel ออกจากกันได้ด้วยสายตา
        stripe = tk.Frame(self, bg=self.color, width=4)
        stripe.grid(row=0, column=0, rowspan=4, sticky="ns", padx=(0, 10))

        # หัวการ์ด: ชื่อ channel + สวิตช์เปิด/ปิด
        head = ttk.Frame(self, style="Card.TFrame")
        head.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        head.columnconfigure(1, weight=1)

        tk.Label(head, text=f"CH{self.ch}", bg=CARD, fg=self.color,
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")

        self.on_var = tk.BooleanVar(value=(self.ch == 1))
        ttk.Checkbutton(head, text="Display", variable=self.on_var,
                        command=self.on_toggle,
                        style="Switch.TCheckbutton").grid(row=0, column=2, sticky="e")

        # V/div
        row = ttk.Frame(self, style="Card.TFrame")
        row.grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Label(row, text="V/div", width=7,
                  style="Small.TLabel").pack(side="left")
        self.vdiv_var = tk.StringVar(value="1 V")
        vdiv = ttk.Combobox(row, textvariable=self.vdiv_var, width=9,
                            state="readonly", values=[s[0] for s in VDIV_STEPS])
        vdiv.pack(side="left", fill="x", expand=True)
        vdiv.bind("<<ComboboxSelected>>", lambda e: self.on_vdiv())

        # Offset - ป้อนค่าเองได้เพราะเป็นค่าต่อเนื่อง ไม่ใช่ step
        row = ttk.Frame(self, style="Card.TFrame")
        row.grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Label(row, text="Offset", width=7,
                  style="Small.TLabel").pack(side="left")
        self.offset_var = tk.StringVar(value="0")
        offs = ttk.Entry(row, textvariable=self.offset_var, width=8)
        offs.pack(side="left", fill="x", expand=True)
        offs.bind("<Return>", lambda e: self.on_offset())
        ttk.Label(row, text="V", style="Small.TLabel").pack(side="left", padx=(4, 0))

        # Coupling
        row = ttk.Frame(self, style="Card.TFrame")
        row.grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Label(row, text="Coupling", width=7,
                  style="Small.TLabel").pack(side="left")
        self.coup_var = tk.StringVar(value="DC")
        coup = ttk.Combobox(row, textvariable=self.coup_var, width=9,
                            state="readonly", values=COUPLING_MODES)
        coup.pack(side="left", fill="x", expand=True)
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
        root.geometry("1020x720")
        root.minsize(940, 660)
        root.configure(bg=BG)

        self._setup_style()
        self._build_ui()
        self.log("พร้อมใช้งาน กด SEARCH เพื่อหา instruments")

    def _setup_style(self):
        """ตั้งธีมกลางไว้ที่เดียว จะได้ไม่ต้องใส่สีซ้ำทุก widget"""
        st = ttk.Style()
        st.theme_use("clam")

        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=CARD, relief="flat")
        st.configure("TLabel", background=BG, foreground=INK)
        st.configure("Card.TLabel", background=CARD, foreground=INK)
        st.configure("Small.TLabel", background=CARD, foreground=MUTED,
                     font=("Segoe UI", 9))
        st.configure("Head.TLabel", background=BG, foreground=MUTED,
                     font=("Segoe UI", 9, "bold"))
        st.configure("Title.TLabel", background=BG, foreground=INK,
                     font=("Segoe UI", 15, "bold"))

        st.configure("TButton", padding=(10, 5))
        st.configure("Accent.TButton", padding=(10, 5),
                     background="#3b6fd4", foreground="#ffffff",
                     borderwidth=0, focuscolor="none")
        st.map("Accent.TButton", background=[("active", "#2f5cb0")])

        st.configure("Switch.TCheckbutton", background=CARD, foreground=INK)
        st.configure("TCheckbutton", background=CARD)
        st.configure("Treeview", rowheight=24, fieldbackground=CARD,
                     background=CARD)
        st.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", padding=(14, 7))

    # ---------- โครงหลัก ----------

    def _build_ui(self):
        self.root.columnconfigure(0, weight=3)   # ฝั่งซ้ายกว้างกว่า
        self.root.columnconfigure(1, weight=0)   # ฝั่งขวาความกว้างคงที่
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        self._build_left()
        self._build_right()

    def _build_header(self):
        bar = ttk.Frame(self.root, padding=(14, 10, 14, 6))
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.columnconfigure(1, weight=1)

        ttk.Label(bar, text="RIGOL Scope Controller",
                  style="Title.TLabel").grid(row=0, column=0, sticky="w")

        # จุดสถานะ + ข้อความ อยู่มุมขวาบน เห็นได้ตลอดเวลา
        badge = ttk.Frame(bar)
        badge.grid(row=0, column=2, sticky="e")
        self.dot = tk.Canvas(badge, width=10, height=10, bg=BG,
                             highlightthickness=0)
        self.dot_id = self.dot.create_oval(1, 1, 9, 9, fill=BAD, outline="")
        self.dot.pack(side="left", padx=(0, 6))
        self.status_label = ttk.Label(badge, text="DISCONNECTED",
                                      foreground=BAD,
                                      font=("Segoe UI", 9, "bold"))
        self.status_label.pack(side="left")

    def _build_left(self):
        left = ttk.Frame(self.root, padding=(14, 0, 7, 12))
        left.grid(row=1, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        left.rowconfigure(3, weight=1)

        self._build_connection(left)
        self._build_command(left)
        self._build_tabs(left)
        self._build_log(left)

    def _build_connection(self, parent):
        ttk.Label(parent, text="CONNECTION",
                  style="Head.TLabel").grid(row=0, column=0, sticky="w",
                                            pady=(0, 4))
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        card.columnconfigure(0, weight=1)

        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(card, textvariable=self.device_var,
                                         state="readonly",
                                         font=("Consolas", 9))
        self.device_combo.grid(row=0, column=0, columnspan=3, sticky="ew",
                               pady=(0, 8))

        ttk.Button(card, text="SEARCH", width=11,
                   command=self.on_search).grid(row=1, column=0, sticky="w")
        self.btn_connect = ttk.Button(card, text="CONNECT", width=11,
                                      style="Accent.TButton",
                                      command=self.on_connect)
        self.btn_connect.grid(row=1, column=1, padx=6)
        self.btn_disconnect = ttk.Button(card, text="DISCONNECT", width=12,
                                         command=self.on_disconnect,
                                         state="disabled")
        self.btn_disconnect.grid(row=1, column=2)

    def _build_command(self, parent):
        ttk.Label(parent, text="SCPI CONSOLE",
                  style="Head.TLabel").grid(row=2, column=0, sticky="sw",
                                            pady=(0, 4))
        card = ttk.Frame(parent, style="Card.TFrame", padding=10)
        card.grid(row=2, column=0, sticky="nsew", pady=(18, 10))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        row = ttk.Frame(card, style="Card.TFrame")
        row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        row.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(row, font=("Consolas", 10))
        self.entry.insert(0, "*IDN?")   # default value ให้เห็น format
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda e: self.on_send())   # Enter = SEND

        ttk.Button(row, text="SEND", width=8, style="Accent.TButton",
                   command=self.on_send).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(row, text="CLEAR", width=8,
                   command=self.on_clear).grid(row=0, column=2, padx=(6, 0))

        self.response = scrolledtext.ScrolledText(card, height=5,
                                                  font=("Consolas", 9),
                                                  bg=TERM_BG, fg=TERM_FG,
                                                  insertbackground=TERM_FG,
                                                  relief="flat", bd=0)
        self.response.grid(row=1, column=0, sticky="nsew")

    def _build_tabs(self, parent):
        nb = ttk.Notebook(parent)
        nb.grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        tab = ttk.Frame(nb, style="Card.TFrame", padding=10)
        nb.add(tab, text="  Measurements  ")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        top = ttk.Frame(tab, style="Card.TFrame")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(top, text="Channel", style="Small.TLabel").pack(side="left",
                                                                  padx=(0, 6))
        self.chan_var = tk.StringVar(value="CHAN1")
        ttk.Combobox(top, textvariable=self.chan_var, width=8, state="readonly",
                     values=["CHAN1", "CHAN2", "CHAN3", "CHAN4"]).pack(
            side="left", padx=(0, 10))
        ttk.Button(top, text="MEASURE", width=11, style="Accent.TButton",
                   command=self.on_measure).pack(side="left")

        # Treeview เหมาะกับข้อมูลเป็นคู่ชื่อ-ค่า
        self.meas_tree = ttk.Treeview(tab, columns=("value", "unit"),
                                      show="tree headings", height=7)
        self.meas_tree.heading("#0", text="Parameter")
        self.meas_tree.heading("value", text="Value")
        self.meas_tree.heading("unit", text="Unit")
        self.meas_tree.column("#0", width=130, anchor="w")
        self.meas_tree.column("value", width=130, anchor="e")
        self.meas_tree.column("unit", width=60, anchor="w")
        self.meas_tree.grid(row=1, column=0, sticky="nsew")

        # scrollbar เผื่อพื้นที่ไม่พอแสดงครบ 8 รายการ
        sb = ttk.Scrollbar(tab, orient="vertical", command=self.meas_tree.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.meas_tree.configure(yscrollcommand=sb.set)

    def _build_log(self, parent):
        ttk.Label(parent, text="SYSTEM LOG",
                  style="Head.TLabel").grid(row=4, column=0, sticky="w",
                                            pady=(0, 4))
        # disabled = user แก้ไม่ได้ code จะ enable ชั่วคราวตอนเขียน
        self.log_box = scrolledtext.ScrolledText(parent, height=6,
                                                 font=("Consolas", 8),
                                                 state="disabled",
                                                 relief="flat", bd=0,
                                                 bg=CARD, fg=INK)
        self.log_box.grid(row=5, column=0, sticky="ew")

    # ---------- ฝั่งขวา: channel + timebase ----------

    def _build_right(self):
        right = ttk.Frame(self.root, padding=(7, 0, 14, 12))
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="VERTICAL",
                  style="Head.TLabel").grid(row=0, column=0, sticky="w",
                                            pady=(0, 4))

        # การ์ด channel 4 ใบเรียงลงมา
        for i, ch in enumerate((1, 2, 3, 4), start=1):
            panel = ChannelPanel(right, self, ch)
            panel.grid(row=i, column=0, sticky="ew", pady=(0, 6))
            self.channels[ch] = panel

        ttk.Label(right, text="HORIZONTAL",
                  style="Head.TLabel").grid(row=5, column=0, sticky="w",
                                            pady=(6, 4))
        self._build_timebase(right)

        ttk.Label(right, text="ACQUISITION",
                  style="Head.TLabel").grid(row=7, column=0, sticky="w",
                                            pady=(6, 4))
        self._build_acquisition(right)

    def _build_timebase(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        card.grid(row=6, column=0, sticky="ew")
        card.columnconfigure(1, weight=1)

        # time/div เป็น step เหมือน V/div เลยใช้ combobox
        ttk.Label(card, text="Time/div", width=8,
                  style="Small.TLabel").grid(row=0, column=0, sticky="w", pady=2)
        self.tdiv_var = tk.StringVar(value="1 ms")
        tdiv = ttk.Combobox(card, textvariable=self.tdiv_var, width=9,
                            state="readonly", values=[s[0] for s in TDIV_STEPS])
        tdiv.grid(row=0, column=1, sticky="ew", pady=2)
        tdiv.bind("<<ComboboxSelected>>", lambda e: self.on_tdiv())

        # offset เป็นค่าต่อเนื่อง ป้อนเองได้
        ttk.Label(card, text="Offset", width=8,
                  style="Small.TLabel").grid(row=1, column=0, sticky="w", pady=2)
        self.toffs_var = tk.StringVar(value="0")
        toffs = ttk.Entry(card, textvariable=self.toffs_var, width=9)
        toffs.grid(row=1, column=1, sticky="ew", pady=2)
        toffs.bind("<Return>", lambda e: self.on_time_offset())
        ttk.Label(card, text="s", style="Small.TLabel").grid(row=1, column=2,
                                                             padx=(4, 0))

    def _build_acquisition(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=(10, 8))
        card.grid(row=8, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        self.btn_runstop = ttk.Button(card, text="RUN / STOP",
                                      style="Accent.TButton",
                                      command=self.on_run_stop)
        self.btn_runstop.grid(row=0, column=0, columnspan=2, sticky="ew",
                              pady=(0, 6))

        ttk.Button(card, text="AUTO", command=self.on_autoscale).grid(
            row=1, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(card, text="SYNC", command=self.on_sync).grid(
            row=1, column=1, sticky="ew", padx=(3, 0))

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
        """update status badge และสลับว่าปุ่มไหน enable"""
        if connected:
            self.status_label.config(text="CONNECTED", foreground=OK)
            self.dot.itemconfig(self.dot_id, fill=OK)
            self.btn_connect.config(state="disabled")
            self.btn_disconnect.config(state="normal")
        else:
            self.status_label.config(text="DISCONNECTED", foreground=BAD)
            self.dot.itemconfig(self.dot_id, fill=BAD)
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
        """อ่านค่าจริงทั้งหมดจาก scope มาใส่ widget ให้ตรงกัน"""
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

    def on_measure(self):
        """อ่านค่าวัดทั้งหมดจาก channel ที่เลือก มาใส่ตาราง"""
        channel = self.chan_var.get()
        self.log(f"กำลังวัดค่าจาก {channel}...")
        self.root.update()      # ให้ log แสดงก่อน GUI ค้างระหว่างรอ

        try:
            results = self.ctrl.measure(channel)

            # ล้างตารางเดิมก่อนใส่ค่าใหม่
            for item in self.meas_tree.get_children():
                self.meas_tree.delete(item)

            for name, (value, unit) in results.items():
                self.meas_tree.insert("", "end", text=name, values=(value, unit))

            self.log(f"วัดค่าเสร็จ {len(results)} รายการ")

        except Exception as e:
            self.log(f"วัดค่าไม่สำเร็จ: {e}")

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