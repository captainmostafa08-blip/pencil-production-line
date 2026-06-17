"""
Pencil Production Line Simulation
Advanced Programming Project - Applied Mechatronics

Product: Pencil
Main assembly components/stages:
1. Graphite core insertion
2. Wooden body assembly
3. Eraser attachment
4. Eraser holder/ferrule attachment
5. Final quality control

The program contains:
- Backend production logic in Python
- Frontend HMI using Tkinter with Start, Stop, Reset buttons
- Defect detection with clear defect reasons
- Optional InfluxDB telemetry for Grafana dashboard visualization

AI-use note: If AI tools were used to generate or improve this code, include the prompt,
AI output, corrections, and benefits in the appendix of the submitted report.
"""

from __future__ import annotations

import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except Exception:  # The app still works without InfluxDB installed.
    InfluxDBClient = None
    Point = None
    WritePrecision = None
    SYNCHRONOUS = None

try:
    import tkinter as tk
    from tkinter import ttk
except Exception as exc:
    raise RuntimeError("Tkinter is required for the HMI frontend.") from exc


# -----------------------------
# Backend model
# -----------------------------

STATIONS = [
    "Graphite core insertion",
    "Wooden body assembly",
    "Eraser attachment",
    "Eraser holder attachment",
    "Final quality control",
]

STATE_STOPPED = "STOPPED"
STATE_RUNNING = "RUNNING"
STATE_FAULTED = "FAULTED"

STATE_VALUE = {
    STATE_STOPPED: 0,
    STATE_RUNNING: 1,
    STATE_FAULTED: 2,
}


@dataclass
class Pencil:
    product_id: int
    graphite_core: bool = False
    wooden_body: bool = False
    eraser: bool = False
    eraser_holder: bool = False
    length_mm: float = 175.0
    diameter_mm: float = 7.0
    quality_pass: bool = True
    defect_reason: str = "None"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MachineSnapshot:
    state: str
    current_station: str
    current_station_index: int
    current_product_id: int
    produced_total: int
    good_total: int
    defective_total: int
    temperature_c: float
    last_defect_reason: str
    last_product_quality: str
    alarm_message: str
    influx_connected: bool


class InfluxWriter:
    """Small wrapper around InfluxDB so the simulator still runs if the database is offline."""

    def __init__(self) -> None:
        self.url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.token = os.getenv("INFLUXDB_TOKEN", "pencil-token")
        self.org = os.getenv("INFLUXDB_ORG", "srh")
        self.bucket = os.getenv("INFLUXDB_BUCKET", "pencil_line")
        self.client = None
        self.write_api = None
        self.connected = False
        self.last_error = ""

        if InfluxDBClient is None:
            self.last_error = "influxdb-client package is not installed"
            return

        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org, timeout=1500)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.connected = True
        except Exception as exc:
            self.last_error = str(exc)
            self.connected = False

    def write_snapshot(self, snapshot: MachineSnapshot) -> None:
        if not self.connected or Point is None:
            return
        try:
            point = (
                Point("pencil_line")
                .tag("machine", "Pencil_Line_01")
                .tag("station", snapshot.current_station)
                .field("state_value", STATE_VALUE.get(snapshot.state, -1))
                .field("produced_total", snapshot.produced_total)
                .field("good_total", snapshot.good_total)
                .field("defective_total", snapshot.defective_total)
                .field("temperature_c", float(snapshot.temperature_c))
                .field("current_station_index", snapshot.current_station_index)
                .field("current_product_id", snapshot.current_product_id)
                .time(datetime.now(timezone.utc), WritePrecision.NS)
            )
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)

    def close(self) -> None:
        if self.client is not None:
            self.client.close()


class PencilProductionLine:
    """Backend logic for a pencil assembly line."""

    def __init__(self, on_update: Optional[Callable[[MachineSnapshot], None]] = None) -> None:
        self.on_update = on_update
        self.state = STATE_STOPPED
        self.current_station_index = -1
        self.current_product_id = 0
        self.produced_total = 0
        self.good_total = 0
        self.defective_total = 0
        self.last_defect_reason = "None"
        self.last_product_quality = "No product yet"
        self.alarm_message = ""
        self.temperature_c = 24.0
        self.running_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.influx = InfluxWriter()

    def start(self) -> None:
        with self.lock:
            if self.state == STATE_RUNNING:
                return
            self.state = STATE_RUNNING
            self.alarm_message = ""
            self.stop_event.clear()
        self.running_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.running_thread.start()
        self._notify()

    def stop(self) -> None:
        with self.lock:
            self.state = STATE_STOPPED
            self.alarm_message = "Machine stopped by operator"
            self.stop_event.set()
        self._notify()

    def reset(self) -> None:
        with self.lock:
            self.state = STATE_STOPPED
            self.current_station_index = -1
            self.current_product_id = 0
            self.produced_total = 0
            self.good_total = 0
            self.defective_total = 0
            self.last_defect_reason = "None"
            self.last_product_quality = "No product yet"
            self.alarm_message = "Counters reset"
            self.temperature_c = 24.0
            self.stop_event.set()
        self._notify()

    def acknowledge_fault(self) -> None:
        with self.lock:
            if self.state == STATE_FAULTED:
                self.state = STATE_STOPPED
                self.alarm_message = "Fault acknowledged. Press Start to continue."
        self._notify()

    def _run_loop(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                if self.state != STATE_RUNNING:
                    break
                self.current_product_id += 1
                product = Pencil(product_id=self.current_product_id)

            self._process_product(product)

            # Short delay between pencils to make the HMI easier to observe.
            time.sleep(0.35)

    def _process_product(self, product: Pencil) -> None:
        for station_index, station_name in enumerate(STATIONS):
            if self.stop_event.is_set():
                return

            with self.lock:
                if self.state != STATE_RUNNING:
                    return
                self.current_station_index = station_index
                self.temperature_c = self._simulate_temperature()
            self._notify()
            time.sleep(0.55)

            if station_name == "Graphite core insertion":
                self._station_graphite_core(product)
            elif station_name == "Wooden body assembly":
                self._station_wooden_body(product)
            elif station_name == "Eraser attachment":
                self._station_eraser(product)
            elif station_name == "Eraser holder attachment":
                self._station_eraser_holder(product)
            elif station_name == "Final quality control":
                self._station_quality_control(product)

            if not product.quality_pass:
                with self.lock:
                    self.defective_total += 1
                    self.produced_total += 1
                    self.last_defect_reason = product.defect_reason
                    self.last_product_quality = "DEFECTIVE"
                    # Only critical defects fault the machine. Non-critical defects are rejected and line continues.
                    if "jam" in product.defect_reason.lower() or "temperature" in product.defect_reason.lower():
                        self.state = STATE_FAULTED
                        self.alarm_message = product.defect_reason
                        self.stop_event.set()
                    else:
                        self.alarm_message = f"Rejected pencil {product.product_id}: {product.defect_reason}"
                self._notify()
                return

        with self.lock:
            self.produced_total += 1
            self.good_total += 1
            self.last_defect_reason = "None"
            self.last_product_quality = "GOOD"
            self.alarm_message = ""
        self._notify()

    def _station_graphite_core(self, product: Pencil) -> None:
        product.graphite_core = random.random() > 0.04
        if not product.graphite_core:
            self._mark_defective(product, "Missing or broken graphite core")

    def _station_wooden_body(self, product: Pencil) -> None:
        if not product.quality_pass:
            return
        product.wooden_body = random.random() > 0.03
        product.length_mm = random.normalvariate(175.0, 1.2)
        product.diameter_mm = random.normalvariate(7.0, 0.15)
        if not product.wooden_body:
            self._mark_defective(product, "Cracked or incomplete wooden body")
        elif random.random() < 0.015:
            self._mark_defective(product, "Wood body jam at assembly station")

    def _station_eraser(self, product: Pencil) -> None:
        if not product.quality_pass:
            return
        product.eraser = random.random() > 0.035
        if not product.eraser:
            self._mark_defective(product, "Missing or misaligned eraser")

    def _station_eraser_holder(self, product: Pencil) -> None:
        if not product.quality_pass:
            return
        product.eraser_holder = random.random() > 0.03
        if not product.eraser_holder:
            self._mark_defective(product, "Loose or missing eraser holder")

    def _station_quality_control(self, product: Pencil) -> None:
        if not product.quality_pass:
            return
        if not (173.0 <= product.length_mm <= 177.0):
            self._mark_defective(product, f"Length out of tolerance: {product.length_mm:.1f} mm")
        elif not (6.6 <= product.diameter_mm <= 7.4):
            self._mark_defective(product, f"Diameter out of tolerance: {product.diameter_mm:.2f} mm")
        elif self.temperature_c > 42.0:
            self._mark_defective(product, f"Machine temperature too high: {self.temperature_c:.1f} °C")

    @staticmethod
    def _mark_defective(product: Pencil, reason: str) -> None:
        product.quality_pass = False
        product.defect_reason = reason

    def _simulate_temperature(self) -> float:
        # Temperature rises slowly during production and may create a fault if it becomes too high.
        trend = 0.03 if self.state == STATE_RUNNING else -0.05
        noise = random.uniform(-0.15, 0.20)
        temp = self.temperature_c + trend + noise
        return max(22.0, min(temp, 45.0))

    def _snapshot(self) -> MachineSnapshot:
        station = "Idle" if self.current_station_index < 0 else STATIONS[self.current_station_index]
        return MachineSnapshot(
            state=self.state,
            current_station=station,
            current_station_index=self.current_station_index,
            current_product_id=self.current_product_id,
            produced_total=self.produced_total,
            good_total=self.good_total,
            defective_total=self.defective_total,
            temperature_c=round(self.temperature_c, 2),
            last_defect_reason=self.last_defect_reason,
            last_product_quality=self.last_product_quality,
            alarm_message=self.alarm_message,
            influx_connected=self.influx.connected,
        )

    def _notify(self) -> None:
        snapshot = self._snapshot()
        self.influx.write_snapshot(snapshot)
        if self.on_update:
            self.on_update(snapshot)


# -----------------------------
# Frontend HMI
# -----------------------------

class PencilLineHMI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Pencil Production Line HMI")
        self.geometry("980x620")
        self.resizable(False, False)

        self.snapshot_queue: List[MachineSnapshot] = []
        self.machine = PencilProductionLine(on_update=self.receive_snapshot)

        self.status_var = tk.StringVar(value="STOPPED")
        self.station_var = tk.StringVar(value="Idle")
        self.product_var = tk.StringVar(value="0")
        self.produced_var = tk.StringVar(value="0")
        self.good_var = tk.StringVar(value="0")
        self.defective_var = tk.StringVar(value="0")
        self.temp_var = tk.StringVar(value="24.0 °C")
        self.quality_var = tk.StringVar(value="No product yet")
        self.defect_var = tk.StringVar(value="None")
        self.alarm_var = tk.StringVar(value="")
        self.influx_var = tk.StringVar(value="Connected" if self.machine.influx.connected else "Offline")

        self.station_items: Dict[int, int] = {}
        self.product_dot: Optional[int] = None

        self._build_ui()
        self.after(200, self._poll_updates)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def receive_snapshot(self, snapshot: MachineSnapshot) -> None:
        self.snapshot_queue.append(snapshot)

    def _build_ui(self) -> None:
        header = ttk.Label(self, text="Pencil Production Line Simulation", font=("Arial", 18, "bold"))
        header.pack(pady=10)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=5)

        ttk.Button(button_frame, text="START", command=self.machine.start).grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="STOP", command=self.machine.stop).grid(row=0, column=1, padx=10)
        ttk.Button(button_frame, text="RESET", command=self.machine.reset).grid(row=0, column=2, padx=10)
        ttk.Button(button_frame, text="ACK FAULT", command=self.machine.acknowledge_fault).grid(row=0, column=3, padx=10)

        info_frame = ttk.Frame(self)
        info_frame.pack(pady=8)

        self._add_info(info_frame, "Machine State", self.status_var, 0, 0)
        self._add_info(info_frame, "Current Station", self.station_var, 0, 2)
        self._add_info(info_frame, "Product ID", self.product_var, 0, 4)
        self._add_info(info_frame, "Produced", self.produced_var, 1, 0)
        self._add_info(info_frame, "Good", self.good_var, 1, 2)
        self._add_info(info_frame, "Defective", self.defective_var, 1, 4)
        self._add_info(info_frame, "Temperature", self.temp_var, 2, 0)
        self._add_info(info_frame, "Last Quality", self.quality_var, 2, 2)
        self._add_info(info_frame, "InfluxDB", self.influx_var, 2, 4)

        self.canvas = tk.Canvas(self, width=930, height=260, bg="white", highlightthickness=1, highlightbackground="gray")
        self.canvas.pack(pady=10)
        self._draw_line()

        alarm_frame = ttk.LabelFrame(self, text="Alarm / Defect Information")
        alarm_frame.pack(fill="x", padx=20, pady=5)
        ttk.Label(alarm_frame, textvariable=self.alarm_var, font=("Arial", 11, "bold"), foreground="red").pack(anchor="w", padx=10, pady=4)
        ttk.Label(alarm_frame, textvariable=self.defect_var, font=("Arial", 10)).pack(anchor="w", padx=10, pady=4)

        footer = ttk.Label(
            self,
            text="Telemetry sent to InfluxDB measurement: pencil_line | Suggested Grafana parameters: produced_total, defective_total, state_value, temperature_c",
            font=("Arial", 9),
        )
        footer.pack(pady=5)

    @staticmethod
    def _add_info(parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, col: int) -> None:
        ttk.Label(parent, text=f"{label}:", font=("Arial", 10, "bold")).grid(row=row, column=col, sticky="e", padx=6, pady=4)
        ttk.Label(parent, textvariable=variable, width=22).grid(row=row, column=col + 1, sticky="w", padx=6, pady=4)

    def _draw_line(self) -> None:
        self.canvas.delete("all")
        x_positions = [80, 260, 440, 620, 800]
        y = 110
        for i, (x, station) in enumerate(zip(x_positions, STATIONS)):
            rect = self.canvas.create_rectangle(x - 65, y - 45, x + 65, y + 45, fill="lightgray", outline="black", width=2)
            self.station_items[i] = rect
            self.canvas.create_text(x, y - 10, text=f"S{i + 1}", font=("Arial", 16, "bold"))
            self.canvas.create_text(x, y + 15, text=station, width=120, font=("Arial", 8))
            if i < len(x_positions) - 1:
                self.canvas.create_line(x + 65, y, x_positions[i + 1] - 65, y, arrow=tk.LAST, width=3)

        self.product_dot = self.canvas.create_oval(35, 185, 65, 215, fill="black")
        self.canvas.create_text(50, 230, text="Pencil", font=("Arial", 8))

    def _poll_updates(self) -> None:
        if self.snapshot_queue:
            snapshot = self.snapshot_queue[-1]
            self.snapshot_queue.clear()
            self._update_hmi(snapshot)
        self.after(150, self._poll_updates)

    def _update_hmi(self, snapshot: MachineSnapshot) -> None:
        self.status_var.set(snapshot.state)
        self.station_var.set(snapshot.current_station)
        self.product_var.set(str(snapshot.current_product_id))
        self.produced_var.set(str(snapshot.produced_total))
        self.good_var.set(str(snapshot.good_total))
        self.defective_var.set(str(snapshot.defective_total))
        self.temp_var.set(f"{snapshot.temperature_c:.1f} °C")
        self.quality_var.set(snapshot.last_product_quality)
        self.defect_var.set(f"Last defect reason: {snapshot.last_defect_reason}")
        self.alarm_var.set(snapshot.alarm_message)
        self.influx_var.set("Connected" if snapshot.influx_connected else "Offline")

        for i, item in self.station_items.items():
            color = "lightgray"
            if snapshot.state == STATE_FAULTED:
                color = "tomato" if i == snapshot.current_station_index else "lightgray"
            elif i == snapshot.current_station_index and snapshot.state == STATE_RUNNING:
                color = "lightgreen"
            self.canvas.itemconfig(item, fill=color)

        if self.product_dot is not None:
            if snapshot.current_station_index >= 0:
                x_positions = [80, 260, 440, 620, 800]
                x = x_positions[snapshot.current_station_index]
                self.canvas.coords(self.product_dot, x - 15, 185, x + 15, 215)
            else:
                self.canvas.coords(self.product_dot, 35, 185, 65, 215)

    def _on_close(self) -> None:
        self.machine.stop()
        self.machine.influx.close()
        self.destroy()


if __name__ == "__main__":
    app = PencilLineHMI()
    app.mainloop()
