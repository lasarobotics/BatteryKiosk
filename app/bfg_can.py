"""
Python port of the Playing With Fusion Battery Fuel Gauge (BFG) CAN code.

Source: https://github.com/PlayingWithFusion/BattFuelGauge-DesktopApp (MIT,
Copyright (c) 2026 Playing With Fusion, Inc.)

The HTTP server, web UI, firmware flashing and Venom motor code from the
original project are not included.


Quick start
-----------

    import time
    from app.bfg_can import PWFCanBus

    with PWFCanBus() as bus:              # finds a CAN adapter, or raises RuntimeError
        bfg = bus.get_bfg(1)              # 1 = the BFG's CAN ID (srcaddr)
        while True:
            state = bfg.update()          # decode the latest CAN messages into a snapshot
            print(state.get_voltage(), state.get_remaining_charge_pct(), state.get_num_cycles())
            time.sleep(1)

To see it working, run `uv run python -m app.bfg_can`. It prints every BFG
on the bus once a second.


How it works: update() and snapshots
------------------------------------

A background thread receives CAN messages all the time and keeps the newest
message for each CAN ID. Nothing gets decoded until you ask for it:

    state = bfg.update()

update() decodes the newest messages, saves every value into a new BfgState
object, and returns it. The latest one is also kept in `bfg.state`.

A BfgState is a snapshot:

  * Its getters just return the saved values. They never touch the CAN bus,
    so they're cheap and you can call them as often as you like.
  * All its values come from the same update() call, so they agree with
    each other (handy when you refresh a whole screen).
  * It never changes. Each update() returns a separate copy, so you can keep
    an old snapshot around, or hand it to another thread, while new ones are
    being made.

To get newer data, call update() again. The BFG sends live values (voltage,
current, charge) about every 10 ms and statistics about once a second, so
calling update() a few times a second is plenty for a UI.

Threading: call update() and the commands from one thread (for example the
Tk main loop via `after()`). Snapshots are safe to pass to other threads.


API overview
------------

PWFCanBus: opens the adapter and gives you BFG objects.
    open() / close(), or use it as a context manager (`with PWFCanBus() as bus`)
    get_bfg(sensor_id)       the BattFuelGauge for that CAN ID (the same object every time)
    discovered_bfgs()        PWFController entries (.id, .serialNumber,
                             .firmwareVersion) for BFGs whose heartbeat
                             arrived in the last 4 s
    can.driver               "gs_usb", "pcan", "custom" or None

BattFuelGauge: one BFG on the bus. Handles the CAN side only.
    update() -> BfgState     decode the latest messages and return a snapshot
    state                    the most recent snapshot
    is_connected()           live check: Power message received in the last 2 s
    identify_sensor()        make the BFG identify itself
    set_nickname(name)       up to 11 characters
    set_manufacturer(BattMfg.X)
    set_battery_age(capacity_Ah, age_s, num_cycles)
    set_display(inverted)
    reset_all_battery_stats()
    set_calibration_vals(offset, gain)
    initiate_current_offset_calibration() / initiate_current_gain_calibration()
    get_bfg_state_json(...)  runs update(), returns the same JSON as upstream
    save_log(filename=None)  writes that JSON to ./logs/BFGSnapshot_*.json

    Commands send an unlock message first, the same as upstream. Values you
    set show up in a snapshot once the BFG reports them back, which takes up
    to about a second.

BfgState: a snapshot. Every getter returns a saved value.
    Live:       get_voltage() [V], get_current() [A, negative = discharging],
                get_remaining_charge_pct() [0-100], get_soc_ah(),
                get_dod_ah(), get_dod_wh(), get_effective_capacity_ah(),
                get_battery_state() -> ChargeState, get_charge_state_string()
    Battery:    get_capacity_ah(), get_rated_capacity_ah(), get_num_cycles(),
                get_battery_age_days(), get_battery_age_s()
    Identity:   get_nickname(), get_manufacturer() -> BattMfg,
                get_manufacturer_string(), get_serial_number(),
                get_firmware_version(), is_connected() (as of the snapshot)
    Calibration: get_current_offset_cal(), get_current_gain_cal()
    Last charge cycle:  get_cycle_*  (rms_discharge_current, min/max_current,
                min/max_voltage, min/max_dod_ah, min/max_dod_wh,
                charge_time, discharge_time, starting_voltage)
    Last match: get_match_*  (rms_discharge_current, min/max_current,
                min/max_voltage, min/max_dod_ah, charge_time, discharge_time,
                starting_voltage, starting/ending_energy,
                starting/ending_charge, duration)
    to_json()   the same JSON and hash as upstream's GetBfgStateJSON
    You can also read the fields directly, e.g. state.voltage_V or
    state.cycle_stats.maxCurrent_A.

    Times are in seconds. Before the BFG has sent anything, most values are 0
    (the defaults are manufacturer = MK Powered and state = INIT, which
    reads as "Discharging", the same as upstream). get_remaining_charge_pct()
    returns 0 until the capacity arrives (about once a second).


Hardware / setup
----------------

Adapters are tried in the same order as the C++ app, at 1 Mbit/s:
  1. a candlelight (gs_usb) device such as a CANable. On Windows we use the
     libusb-1.0.dll that comes with the `libusb-package` dependency.
  2. a PEAK PCAN adapter on PCAN_USBBUS1. This needs PEAK's driver
     (PCANBasic.dll) installed.

Safety (from upstream): if the BFG is also connected to a battery charger,
use a galvanically isolated CAN adapter.

To test without hardware, pass in any python-can bus:

    bus = PWFCanBus(can.Bus(interface="virtual", channel="test"))


What maps to what (C++ -> Python)
---------------------------------

    halCAN.c + the CANSessionMux shim in main.cpp  ->  CanInterface
    FusionFlashUtil (heartbeat / identify / unlock)  ->  PWFDeviceTracker
    BattFuelGaugeImpl (CAN decode + commands)        ->  BattFuelGauge
    BattFuelGaugeApi.h getters + GetBfgStateJSON     ->  BfgState (snapshot)
    XxHash32                                         ->  xxhash32()
    all of the above wired together                  ->  PWFCanBus

Where this differs from upstream:
  * Upstream's getters each re-read the bus. Here update() reads it once and
    the getters return the saved values.
  * update() doesn't rate-limit decoding (upstream decodes at most every
    10 ms / 1 s). Decoding a saved message is cheap.
  * Device and connection timeouts are measured in wall time instead of loop
    ticks. The thresholds are the same: 4 s for heartbeats, 2 s for connected.
  * get_cycle_min_dod_wh() returns the Wh value. Upstream returns minDOD_Ah
    by mistake.
  * The heartbeat filter masks both IDs. Upstream compares against the
    unmasked 0x1F0501FF, which can never match (this only affects Venom
    devices).
"""

from __future__ import annotations

import copy
import logging
import os
import struct
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path

import can

log = logging.getLogger(__name__)

CAN_BITRATE = 1_000_000

# Placeholder secret used by the upstream code unless BFG_HASH_SECRET is defined
# when it's compiled.
BFG_HASH_SECRET = 0x12345678


# --------------------------------------------------------------------------- #
# Types  (PWFController.h, BattFuelGaugeApiTypes.h)
# --------------------------------------------------------------------------- #


class DeviceType(IntEnum):
    TOF_SENSOR = 0x110
    TOF_SENSOR_CK128 = 0x111
    TOF_SENSOR_CK256 = 0x112
    VENOM_MOTOR_CONTROLLER_PROTO = 0x123
    VENOM_MOTOR_CONTROLLER = 0x124
    ANALOG_TOF_SENSOR_CK128 = 0x311
    BFG_SENSOR = 0x130


class ChargeState(IntEnum):
    INIT = 0
    DISCHARGE = 1
    CONST_I_CHARGE = 2
    CONST_V_CHARGE = 3
    TRICKLE_CHARGE = 4
    IDLE = 5
    MEASURE_OCV = 6


class BattMfg(IntEnum):
    DURACELL = 0
    ENERGIZER = 1
    INTERSTATE = 2
    MIGHTY_MAX = 3
    MK_POWERED = 4
    POWER_SONIC = 5


class CANMsgApiId(IntEnum):
    """CAN arbitration IDs. For per-sensor messages, OR in the sensor ID."""

    POWER = 0x0A0B0000
    BATTERY_HEALTH = 0x0A0B0100
    MATCH_CURRENT = 0x0A0B0200
    MATCH_CHARGE = 0x0A0B0300
    MATCH_TIME = 0x0A0B0500
    RMS_CURRENT = 0x0A0B0600
    STATE_OF_CHARGE = 0x0A0B0700
    CYCLE_CURRENT = 0x0A0B0800
    CYCLE_CHARGE = 0x0A0B0900
    CYCLE_TIME = 0x0A0B0A00
    CALIBRATION = 0x0A0B0B00
    CYCLE_ENERGY = 0x0A0B0C00
    MATCH_DELTA_ENERGY = 0x0A0B0D00
    MATCH_DELTA_CHARGE = 0x0A0B0E00
    NICKNAME1 = 0x0A0B0F00
    NICKNAME2 = 0x0A0B1000
    SET_NICKNAME1 = 0x0A0B2000
    SET_NICKNAME2 = 0x0A0B2100
    SET_HEALTH = 0x0A0B2200
    SET_CALIBRATION = 0x0A0B2300
    HEARTBEAT = 0x1F0B0100
    REPROG = 0x1F0B03FF


_CHARGE_STATE_STRINGS = {
    ChargeState.DISCHARGE: "Discharging",
    ChargeState.CONST_I_CHARGE: "Charging",
    ChargeState.CONST_V_CHARGE: "Charging",
    ChargeState.TRICKLE_CHARGE: "Charging",
    ChargeState.IDLE: "Idle",
    ChargeState.MEASURE_OCV: "Open Circuit",
}

_MANUFACTURER_STRINGS = {
    BattMfg.DURACELL: "Duracell",
    BattMfg.ENERGIZER: "Energizer",
    BattMfg.INTERSTATE: "Interstate",
    BattMfg.MIGHTY_MAX: "MightyMax",
    BattMfg.MK_POWERED: "MK Powered",
    BattMfg.POWER_SONIC: "Power-Sonic",
}

_DEVICE_NAMES = {
    DeviceType.VENOM_MOTOR_CONTROLLER: "Venom Motor",
    DeviceType.VENOM_MOTOR_CONTROLLER_PROTO: "Venom Motor",
    DeviceType.TOF_SENSOR: "Time-of-Flight",
    DeviceType.TOF_SENSOR_CK128: "Time-of-Flight",
    DeviceType.ANALOG_TOF_SENSOR_CK128: "Time-of-Flight",
    DeviceType.TOF_SENSOR_CK256: "Time-of-Flight",
    DeviceType.BFG_SENSOR: "Battery Fuel Gauge",
}


@dataclass
class Stats:
    minVoltage_V: float = 0.0
    maxVoltage_V: float = 0.0
    minCurrent_A: float = 0.0
    maxCurrent_A: float = 0.0
    startingVoltage_V: float = 0.0
    rmsDischargeCurrent_A: float = 0.0
    minDOD_Ah: float = 0.0
    maxDOD_Ah: float = 0.0
    chargeTime_s: int = 0
    dischargeTime_s: int = 0


@dataclass
class CycleStats(Stats):
    minDOD_Wh: float = 0.0
    maxDOD_Wh: float = 0.0


@dataclass
class MatchStats(Stats):
    activeTime_s: int = 0
    startDOD_Ah: float = 0.0
    startDOD_Wh: float = 0.0
    endDOD_Ah: float = 0.0
    endDOD_Wh: float = 0.0


@dataclass
class PWFController:
    """A PWF device we've seen on the bus via its heartbeat."""

    id: int
    device: int
    serialNumber: int
    firmwareVersion: int
    lastHeartbeat: float = field(default_factory=time.monotonic)

    # The C++ code counts 100 ms ticks while idle and gives up after 40. Here we
    # just compare against wall time, which works out the same.
    HEARTBEAT_TIMEOUT_S = 4.0

    @property
    def activeOnBus(self) -> bool:
        return (time.monotonic() - self.lastHeartbeat) < self.HEARTBEAT_TIMEOUT_S

    @property
    def deviceName(self) -> str:
        try:
            return _DEVICE_NAMES[DeviceType(self.device)]
        except ValueError:
            return f"0x{self.device:X}"


@dataclass
class _Frame:
    data: bytes
    timestamp: float  # time.monotonic() when it arrived


# --------------------------------------------------------------------------- #
# Byte helpers (all fields are little-endian)
# --------------------------------------------------------------------------- #


def _u16(d: bytes, i: int) -> int:
    return d[i] | (d[i + 1] << 8)


def _s16(d: bytes, i: int) -> int:
    return struct.unpack_from("<h", d, i)[0]


def _u32(d: bytes, i: int) -> int:
    return struct.unpack_from("<I", d, i)[0]


def _s32(d: bytes, i: int) -> int:
    return struct.unpack_from("<i", d, i)[0]


def _u24(d: bytes, i: int) -> int:
    return d[i] | (d[i + 1] << 8) | (d[i + 2] << 16)


# --------------------------------------------------------------------------- #
# XXHash32 (XxHash32.cpp)
# --------------------------------------------------------------------------- #

_P1, _P2, _P3, _P4, _P5 = 2654435761, 2246822519, 3266489917, 668265263, 374761393
_M32 = 0xFFFFFFFF


def _rotl(x: int, r: int) -> int:
    return ((x << r) | (x >> (32 - r))) & _M32


def xxhash32(data: bytes, seed: int = 0) -> int:
    """Standard XXH32. Gives the same output as XXHash32::Hash on little-endian hosts."""
    n = len(data)
    i = 0
    if n >= 16:
        v1 = (seed + _P1 + _P2) & _M32
        v2 = (seed + _P2) & _M32
        v3 = seed & _M32
        v4 = (seed - _P1) & _M32
        while i + 16 <= n:
            a, b, c, d = struct.unpack_from("<4I", data, i)
            v1 = (_rotl((v1 + a * _P2) & _M32, 13) * _P1) & _M32
            v2 = (_rotl((v2 + b * _P2) & _M32, 13) * _P1) & _M32
            v3 = (_rotl((v3 + c * _P2) & _M32, 13) * _P1) & _M32
            v4 = (_rotl((v4 + d * _P2) & _M32, 13) * _P1) & _M32
            i += 16
        h = (_rotl(v1, 1) + _rotl(v2, 7) + _rotl(v3, 12) + _rotl(v4, 18)) & _M32
    else:
        h = (seed + _P5) & _M32

    h = (h + n) & _M32
    while i + 4 <= n:
        (k,) = struct.unpack_from("<I", data, i)
        h = (_rotl((h + k * _P3) & _M32, 17) * _P4) & _M32
        i += 4
    while i < n:
        h = (_rotl((h + data[i] * _P5) & _M32, 11) * _P1) & _M32
        i += 1

    h ^= h >> 15
    h = (h * _P2) & _M32
    h ^= h >> 13
    h = (h * _P3) & _M32
    h ^= h >> 16
    return h


def _fmt(v) -> str:
    """Format a number the same way fmt::format("{}", v) does, so the JSON (and its hash) matches the C++ output."""
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    if v.is_integer() and abs(v) < 1e16:
        return str(int(v))
    return repr(v)


# --------------------------------------------------------------------------- #
# CAN transport  (halCAN.c + CANSessionMux shim from main.cpp)
# --------------------------------------------------------------------------- #


def _ensure_libusb_on_path() -> None:
    """gs_usb talks to the device through pyusb/libusb. On Windows there's
    usually no libusb-1.0.dll installed, so we use the one that ships with the
    `libusb-package` wheel."""
    try:
        import libusb_package
    except ImportError:
        return
    lib = libusb_package.get_library_path()
    if lib is not None:
        d = str(Path(lib).parent)
        if d not in os.environ.get("PATH", ""):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


class CanInterface:
    """Opens the adapter and runs a background receive thread. It keeps the
    most recent frame for each arbitration ID, which is what
    FRC_NetworkCommunication_CANSessionMux_receiveMessage does on the desktop
    build. You can also register listeners to see every frame (the C++ code
    uses a stream session for this, mainly for heartbeats)."""

    def __init__(self, bus: can.BusABC | None = None):
        self._bus: can.BusABC | None = bus
        self.driver: str | None = "custom" if bus is not None else None
        self._latest: dict[int, _Frame] = {}
        self._lock = threading.Lock()
        self._listeners: list = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # HalCAN_Open
    def open(self) -> bool:
        if self._bus is None:
            _ensure_libusb_on_path()
            try:
                self._bus = can.Bus(interface="gs_usb", channel=0, index=0, bitrate=CAN_BITRATE)
                self.driver = "gs_usb"
                log.info("Found Candle compatible CAN device")
            except Exception as e:  # noqa: BLE001 - any failure means "try next driver"
                log.debug("gs_usb open failed: %s", e)

        if self._bus is None:
            try:
                self._bus = can.Bus(interface="pcan", channel="PCAN_USBBUS1", bitrate=CAN_BITRATE)
                self.driver = "pcan"
                log.info("Found PEAK PCAN compatible CAN device")
            except Exception as e:  # noqa: BLE001
                log.debug("pcan open failed: %s", e)

        if self._bus is None:
            self.driver = None
            log.warning("No compatible CAN interface detected")
            return False

        self._stop.clear()
        self._thread = threading.Thread(target=self._rx_loop, name="pwf-can-rx", daemon=True)
        self._thread.start()
        return True

    # HalCAN_Close
    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._bus is not None:
            try:
                self._bus.shutdown()
            finally:
                self._bus = None

    @property
    def is_open(self) -> bool:
        return self._bus is not None

    def add_listener(self, fn) -> None:
        """Register fn(msg: can.Message). It's called from the receive thread for every frame."""
        self._listeners.append(fn)

    def _rx_loop(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self._bus.recv(timeout=0.1)
            except Exception as e:  # noqa: BLE001
                log.error("CAN receive error: %s", e)
                time.sleep(0.1)
                continue
            if msg is None or msg.is_error_frame or msg.is_remote_frame:
                continue
            frame = _Frame(bytes(msg.data[: msg.dlc]), time.monotonic())
            with self._lock:
                self._latest[msg.arbitration_id] = frame
            for fn in self._listeners:
                try:
                    fn(msg)
                except Exception:  # noqa: BLE001
                    log.exception("CAN listener raised")

    # FRC_NetworkCommunication_CANSessionMux_sendMessage
    def send(self, arbitration_id: int, data: bytes | bytearray | list[int]) -> None:
        if self._bus is None:
            return
        msg = can.Message(arbitration_id=arbitration_id, data=bytes(data), is_extended_id=True)
        try:
            self._bus.send(msg, timeout=1.0)
        except can.CanError as e:
            log.warning("CAN send failed (0x%08X): %s", arbitration_id, e)

    # FRC_NetworkCommunication_CANSessionMux_receiveMessage
    def receive_latest(self, arbitration_id: int) -> _Frame | None:
        with self._lock:
            return self._latest.get(arbitration_id)


# --------------------------------------------------------------------------- #
# Device discovery / admin commands  (FusionFlashUtil, minus flashing)
# --------------------------------------------------------------------------- #


class PWFDeviceTracker:
    # Heartbeat IDs from IdentifyHeartbeatTask, low byte (device ID) masked off.
    # Upstream compares (id & 0x1FFFFF00) against the unmasked 0x1F0501FF, which
    # can never match. We mask both, which is clearly what was intended.
    _HEARTBEAT_IDS = (0x1F0501FF & 0x1FFFFF00, 0x1F0B0100 & 0x1FFFFF00)

    def __init__(self, can_if: CanInterface):
        self._can = can_if
        self._controllers: list[PWFController] = []
        self._lock = threading.Lock()
        can_if.add_listener(self._on_frame)

    def _on_frame(self, msg: can.Message) -> None:
        if msg.dlc != 8 or (msg.arbitration_id & 0x1FFFFF00) not in self._HEARTBEAT_IDS:
            return
        d = msg.data
        ctrl = PWFController(
            id=msg.arbitration_id & 0xFF,
            device=_u16(d, 4),
            serialNumber=_u24(d, 1),
            firmwareVersion=_u16(d, 6),
        )
        with self._lock:
            for i, c in enumerate(self._controllers):
                if c.device == ctrl.device and c.serialNumber == ctrl.serialNumber:
                    self._controllers[i] = ctrl
                    return
            self._controllers.append(ctrl)
        log.info("Found PWF Device: %s, serial number:%d", ctrl.deviceName, ctrl.serialNumber)

    def get_controller_list(self) -> list[PWFController]:
        with self._lock:
            return list(self._controllers)

    def get_controller_by_id(self, device: int, id_: int) -> PWFController | None:
        with self._lock:
            for c in self._controllers:
                if c.device == device and c.id == id_ and c.activeOnBus:
                    return c
        return None

    @staticmethod
    def _cmd(sub: int, device: int, serial: int) -> list[int]:
        return [sub, serial & 0xFF, (serial >> 8) & 0xFF, (serial >> 16) & 0xFF, device & 0xFF, (device >> 8) & 0xFF]

    def set_controller_id(self, device: int, serial_number: int, id_: int) -> None:
        with self._lock:
            for c in self._controllers:
                if c.device == device and c.serialNumber == serial_number:
                    c.id = id_
                    break
            else:
                return
        self._can.send(CANMsgApiId.REPROG, self._cmd(0x0C, device, serial_number) + [id_ & 0xFF])

    def identify_controller(self, device: int, serial_number: int) -> None:
        self._can.send(CANMsgApiId.REPROG, self._cmd(0x0D, device, serial_number))

    def unlock_controller(self, device: int, serial_number: int) -> None:
        self._can.send(CANMsgApiId.REPROG, self._cmd(0x0A, device, serial_number))


# --------------------------------------------------------------------------- #
# Battery Fuel Gauge  (BattFuelGaugeImpl)
# --------------------------------------------------------------------------- #


@dataclass
class BfgState:
    """A snapshot of every value a BFG reports, taken when
    BattFuelGauge.update() was called.

    The getters just return the values that were saved, so they don't touch
    the CAN bus and they always agree with each other. The snapshot never
    changes after it's created; call update() again to get a newer one.

    The getter names follow the BattFuelGauge_Get* functions in upstream's
    BattFuelGaugeApi.h. You can also read the fields directly."""

    sensor_id: int = 0
    timestamp: float = 0.0  # time.monotonic() when the snapshot was taken
    connected: bool = False

    firmware_version: int = 0
    serial_number: int = 0

    meas_current_offset: int = 0
    meas_current_gain: int = 0

    nickname: str = ""
    batt_manufacturer: int = int(BattMfg.MK_POWERED)
    batt_age_s: int = 0
    batt_num_cycles: int = 0
    rated_capacity_Ah: float = 0.0

    charge_state: int = int(ChargeState.INIT)
    capacity_Ah: float = 0.0
    effective_capacity_Ah: float = 0.0
    voltage_V: float = 0.0
    current_A: float = 0.0
    dod_Ah: float = 0.0
    dod_Wh: float = 0.0
    soc_Ah: float = 0.0

    cycle_stats: CycleStats = field(default_factory=CycleStats)
    match_stats: MatchStats = field(default_factory=MatchStats)

    # Connection / identification

    def is_connected(self) -> bool:
        """Whether the BFG had sent a Power message in the 2 s before this snapshot."""
        return self.connected

    def get_firmware_version(self) -> int:
        return self.firmware_version

    def get_serial_number(self) -> int:
        return self.serial_number

    # Core real-time / state values

    def get_battery_state(self) -> ChargeState | int:
        """Charge state. Returns the raw int if the BFG sends a value we don't know."""
        try:
            return ChargeState(self.charge_state)
        except ValueError:
            return self.charge_state

    def get_charge_state_string(self) -> str:
        """Human readable charge state: "Discharging", "Charging", "Idle" or "Open Circuit"."""
        try:
            return _CHARGE_STATE_STRINGS.get(ChargeState(self.charge_state), "Discharging")
        except ValueError:
            return "Discharging"

    def get_current(self) -> float:
        """Battery current in A (negative = discharging)."""
        return self.current_A

    def get_voltage(self) -> float:
        """Battery terminal voltage in V."""
        return self.voltage_V

    def get_dod_ah(self) -> float:
        """Current depth of discharge in Ah."""
        return self.dod_Ah

    def get_dod_wh(self) -> float:
        """Current depth of discharge energy in Wh."""
        return self.dod_Wh

    def get_soc_ah(self) -> float:
        """Remaining charge (state of charge) in Ah. Upstream has no getter for this one."""
        return self.soc_Ah

    def get_remaining_charge_pct(self) -> float:
        """Remaining charge as a percentage of the battery's current capacity (usually 0-100).
        Returns 0 until the capacity is known."""
        if self.capacity_Ah > 0:
            return 100.0 * self.soc_Ah / self.capacity_Ah
        return 0.0

    def get_effective_capacity_ah(self) -> float:
        """Effective (usable) capacity in Ah."""
        return self.effective_capacity_Ah

    # Battery age, capacity & cycle information

    def get_battery_age_days(self) -> float:
        """Battery age in days."""
        return self.batt_age_s / (3600.0 * 24.0)

    def get_battery_age_s(self) -> int:
        """Battery age in seconds."""
        return self.batt_age_s

    def get_capacity_ah(self) -> float:
        """Current estimated battery capacity in Ah."""
        return self.capacity_Ah

    def get_rated_capacity_ah(self) -> float:
        """Rated capacity of the battery when new, in Ah."""
        return self.rated_capacity_Ah

    def get_num_cycles(self) -> int:
        """Total number of charge/discharge cycles."""
        return self.batt_num_cycles

    # Identification

    def get_nickname(self) -> str:
        """Battery nickname (up to 11 characters). Empty string if it hasn't been set."""
        return self.nickname

    def get_manufacturer(self) -> BattMfg | int:
        """Battery manufacturer. Returns the raw int if the BFG sends a value we don't know."""
        try:
            return BattMfg(self.batt_manufacturer)
        except ValueError:
            return self.batt_manufacturer

    def get_manufacturer_string(self) -> str:
        """Human readable manufacturer name, or "Unknown"."""
        try:
            return _MANUFACTURER_STRINGS[BattMfg(self.batt_manufacturer)]
        except (ValueError, KeyError):
            return "Unknown"

    # Calibration (upstream only exposes these through the JSON)

    def get_current_offset_cal(self) -> int:
        """Raw current offset calibration value."""
        return self.meas_current_offset

    def get_current_gain_cal(self) -> int:
        """Raw current gain calibration value."""
        return self.meas_current_gain

    # Last full charge cycle statistics

    def get_cycle_rms_discharge_current(self) -> float:
        """RMS discharge current during the last charge cycle, in A."""
        return self.cycle_stats.rmsDischargeCurrent_A

    def get_cycle_max_current(self) -> float:
        """Max (charging) current during the last charge cycle, in A."""
        return self.cycle_stats.maxCurrent_A

    def get_cycle_min_current(self) -> float:
        """Min (most negative) current during the last charge cycle, in A."""
        return self.cycle_stats.minCurrent_A

    def get_cycle_min_voltage(self) -> float:
        """Min voltage during the last charge cycle, in V."""
        return self.cycle_stats.minVoltage_V

    def get_cycle_max_voltage(self) -> float:
        """Max voltage during the last charge cycle, in V."""
        return self.cycle_stats.maxVoltage_V

    def get_cycle_min_dod_ah(self) -> float:
        """Min depth of discharge during the last charge cycle, in Ah."""
        return self.cycle_stats.minDOD_Ah

    def get_cycle_max_dod_ah(self) -> float:
        """Max depth of discharge during the last charge cycle, in Ah."""
        return self.cycle_stats.maxDOD_Ah

    def get_cycle_min_dod_wh(self) -> float:
        """Min depth of discharge energy during the last charge cycle, in Wh.
        (Upstream returns minDOD_Ah here by mistake.)"""
        return self.cycle_stats.minDOD_Wh

    def get_cycle_max_dod_wh(self) -> float:
        """Max depth of discharge energy during the last charge cycle, in Wh."""
        return self.cycle_stats.maxDOD_Wh

    def get_cycle_charge_time(self) -> int:
        """Time spent charging during the last charge cycle, in s."""
        return self.cycle_stats.chargeTime_s

    def get_cycle_discharge_time(self) -> int:
        """Time spent discharging during the last charge cycle, in s."""
        return self.cycle_stats.dischargeTime_s

    def get_cycle_starting_voltage(self) -> float:
        """Voltage at the start of the last charge cycle, in V."""
        return self.cycle_stats.startingVoltage_V

    # Last robot match statistics

    def get_match_rms_discharge_current(self) -> float:
        """RMS discharge current during the last match, in A."""
        return self.match_stats.rmsDischargeCurrent_A

    def get_match_max_current(self) -> float:
        """Max current during the last match, in A."""
        return self.match_stats.maxCurrent_A

    def get_match_min_current(self) -> float:
        """Min (most negative) current during the last match, in A."""
        return self.match_stats.minCurrent_A

    def get_match_min_voltage(self) -> float:
        """Min voltage during the last match, in V."""
        return self.match_stats.minVoltage_V

    def get_match_max_voltage(self) -> float:
        """Max voltage during the last match, in V."""
        return self.match_stats.maxVoltage_V

    def get_match_min_dod_ah(self) -> float:
        """Min depth of discharge during the last match, in Ah."""
        return self.match_stats.minDOD_Ah

    def get_match_max_dod_ah(self) -> float:
        """Max depth of discharge during the last match, in Ah."""
        return self.match_stats.maxDOD_Ah

    def get_match_charge_time(self) -> int:
        """Time spent charging during the last match, in s."""
        return self.match_stats.chargeTime_s

    def get_match_discharge_time(self) -> int:
        """Time spent discharging during the last match, in s."""
        return self.match_stats.dischargeTime_s

    def get_match_starting_voltage(self) -> float:
        """Voltage at the start of the last match, in V."""
        return self.match_stats.startingVoltage_V

    def get_match_starting_energy(self) -> float:
        """Depth of discharge energy at the start of the last match, in Wh."""
        return self.match_stats.startDOD_Wh

    def get_match_ending_energy(self) -> float:
        """Depth of discharge energy at the end of the last match, in Wh."""
        return self.match_stats.endDOD_Wh

    def get_match_starting_charge(self) -> float:
        """Depth of discharge at the start of the last match, in Ah."""
        return self.match_stats.startDOD_Ah

    def get_match_ending_charge(self) -> float:
        """Depth of discharge at the end of the last match, in Ah."""
        return self.match_stats.endDOD_Ah

    def get_match_duration(self) -> int:
        """Length of the last match, in s."""
        return self.match_stats.activeTime_s

    # JSON

    def to_json(self, event_name: str = "", match_number: int = 0, team_number: int = 0) -> str:
        """Same JSON as the C++ GetBfgStateJSON, byte for byte, so the hash
        matches too. The desktop build always reports an empty event name and
        match/team 0, which is why those are the defaults here."""
        cs, ms = self.cycle_stats, self.match_stats
        f = _fmt

        fields: list[tuple[str, str]] = [
            ("nickname", f'"{self.nickname}"'),
            ("bfg_serial", f(self.serial_number)),
            ("bfg_firmware", f(self.firmware_version)),
            ("batt_capacity", f(self.capacity_Ah)),
            ("batt_rated_capacity", f(self.rated_capacity_Ah)),
            ("batt_mfg", f'"{self.get_manufacturer_string()}"'),
            ("batt_mfg_id", f(int(self.batt_manufacturer))),
            ("bat_age", f(self.batt_age_s)),
            ("bat_num_cycles", f(self.batt_num_cycles)),
            ("bfg_state", f'"{self.get_charge_state_string()}"'),
            ("cal_current_offset", f(self.meas_current_offset)),
            ("cal_current_gain", f(self.meas_current_gain)),
            ("voltage", f(self.voltage_V)),
            ("current", f(self.current_A)),
            ("dod_ah", f(self.dod_Ah)),
            ("dod_wh", f(self.dod_Wh)),
            ("soc_ah", f(self.soc_Ah)),
            ("effective_cap_ah", f(self.effective_capacity_Ah)),
            ("cycle_min_v", f(cs.minVoltage_V)),
            ("cycle_max_v", f(cs.maxVoltage_V)),
            ("cycle_min_i", f(cs.minCurrent_A)),
            ("cycle_max_i", f(cs.maxCurrent_A)),
            ("cycle_starting_v", f(cs.startingVoltage_V)),
            ("cycle_rms_i", f(cs.rmsDischargeCurrent_A)),
            ("cycle_min_dod_ah", f(cs.minDOD_Ah)),
            ("cycle_min_dod_wh", f(cs.minDOD_Wh)),
            ("cycle_max_dod_ah", f(cs.maxDOD_Ah)),
            ("cycle_max_dod_wh", f(cs.maxDOD_Wh)),
            ("cycle_charge_time", f(cs.chargeTime_s)),
            ("cycle_discharge_time", f(cs.dischargeTime_s)),
            ("match_min_v", f(ms.minVoltage_V)),
            ("match_max_v", f(ms.maxVoltage_V)),
            ("match_min_i", f(ms.minCurrent_A)),
            ("match_max_i", f(ms.maxCurrent_A)),
            ("match_starting_v", f(ms.startingVoltage_V)),
            ("match_rms_i", f(ms.rmsDischargeCurrent_A)),
            ("match_min_dod_ah", f(ms.minDOD_Ah)),
            ("match_max_dod_ah", f(ms.maxDOD_Ah)),
            ("match_charge_time", f(ms.chargeTime_s)),
            ("match_discharge_time", f(ms.dischargeTime_s)),
            ("match_active_time", f(ms.activeTime_s)),
            ("match_start_dod_ah", f(ms.startDOD_Ah)),
            ("match_start_dod_wh", f(ms.startDOD_Wh)),
            ("match_end_dod_ah", f(ms.endDOD_Ah)),
            ("match_end_dod_wh", f(ms.endDOD_Wh)),
        ]
        bfg_json = "{\n" + ",\n".join(f'"{k}":{v}' for k, v in fields) + "\n}"

        h = xxhash32(bfg_json.encode("latin-1", errors="replace"), BFG_HASH_SECRET)
        return (
            "{"
            f'"event_name":"{event_name}",\n'
            f'"match_number":{match_number},\n'
            f'"team_number":{team_number},\n'
            f'"bfg_data":{bfg_json},"hash":"{h:08x}"}}'
        )


class BattFuelGauge:
    """A single BFG on the bus, identified by its CAN ID (srcaddr). This class
    only deals with CAN: decoding received messages and sending commands.

    Call update() to decode the latest messages. It returns a BfgState
    snapshot, which is where the getters live:

        state = bfg.update()
        state.get_voltage()
        state.get_remaining_charge_pct()

    The most recent snapshot is also kept in bfg.state."""

    CONNECTED_TIMEOUT_S = 2.0

    def __init__(self, can_if: CanInterface, tracker: PWFDeviceTracker, sensor_id: int):
        self._can = can_if
        self._tracker = tracker
        self.sensor_id = sensor_id & 0xFF

        # Identity from the heartbeat. Commands need these to unlock the device.
        self.firmware_version = 0
        self.serial_number = 0
        self.device_id = int(DeviceType.BFG_SENSOR)

        # The nickname comes in over two messages, so we build it up in a buffer
        self._nickname = bytearray(12)
        # Working copy that update() decodes into. Snapshots are copies of it.
        self._s = BfgState(sensor_id=self.sensor_id)
        self.state = copy.deepcopy(self._s)

    # ---- controller info ---------------------------------------------------

    def _refresh_controller_info(self) -> None:
        c = self._tracker.get_controller_by_id(DeviceType.BFG_SENSOR, self.sensor_id)
        if c is not None:
            self.device_id = c.device
            self.firmware_version = c.firmwareVersion
            self.serial_number = c.serialNumber

    def identify_sensor(self) -> None:
        """Tell the BFG to identify itself (e.g. flash its display)."""
        self._refresh_controller_info()
        self._tracker.identify_controller(self.device_id, self.serial_number)

    def is_connected(self) -> bool:
        """Live check: has a Power message arrived in the last 2 s?"""
        f = self._can.receive_latest(CANMsgApiId.POWER | self.sensor_id)
        return f is not None and (time.monotonic() - f.timestamp) < self.CONNECTED_TIMEOUT_S

    # ---- commands ----------------------------------------------------------

    def _unlock(self) -> None:
        self._refresh_controller_info()
        self._tracker.unlock_controller(self.device_id, self.serial_number)

    def set_nickname(self, name: str) -> None:
        self._unlock()
        enc = name.encode("latin-1", errors="replace")[:11]
        self._nickname = bytearray(enc.ljust(12, b"\x00"))
        self._can.send(CANMsgApiId.SET_NICKNAME1 | self.sensor_id, self._nickname[0:8])
        self._can.send(CANMsgApiId.SET_NICKNAME2 | self.sensor_id, self._nickname[8:11])

    def set_manufacturer(self, mfg_id: int) -> None:
        self._unlock()
        self._can.send(CANMsgApiId.SET_NICKNAME2 | self.sensor_id, [0xFF, 0xFF, 0xFF, int(mfg_id) & 0xFF])

    def set_calibration_vals(self, current_offset: int, current_gain: int) -> None:
        self._unlock()
        data = struct.pack("<II", current_offset & _M32, current_gain & _M32)
        self._can.send(CANMsgApiId.SET_CALIBRATION | self.sensor_id, data)

    def set_battery_age(self, capacity_Ah: float, age_s: int, num_cycles: int) -> None:
        self._unlock()
        capacity_mAh = int(capacity_Ah * 1000.0) & 0xFFFF
        data = struct.pack("<IHH", age_s & _M32, capacity_mAh, num_cycles & 0xFFFF)
        self._can.send(CANMsgApiId.SET_HEALTH | self.sensor_id, data)

    def reset_all_battery_stats(self) -> None:
        self._unlock()
        # 0x69 is the magic number that tells the BFG to reset
        self._can.send(CANMsgApiId.SET_NICKNAME2 | self.sensor_id, [0xFF, 0xFF, 0xFF, 0xFF, 0x69])

    def _factory_cal(self, kind: int) -> None:
        self._unlock()
        data = PWFDeviceTracker._cmd(0x0B, self.device_id, self.serial_number) + [kind]
        self._can.send(CANMsgApiId.REPROG, data)

    def initiate_current_offset_calibration(self) -> None:
        self._factory_cal(1)

    def initiate_current_gain_calibration(self) -> None:
        self._factory_cal(2)

    def set_display(self, inverted: bool) -> None:
        self._unlock()
        self._can.send(CANMsgApiId.SET_NICKNAME2 | self.sensor_id, [0xFF] * 5 + [1 if inverted else 0])

    # ---- receive / decode --------------------------------------------------

    def _rx(self, api: CANMsgApiId) -> bytes | None:
        f = self._can.receive_latest(api | self.sensor_id)
        if f is None or len(f.data) != 8:
            return None
        return f.data

    def update(self) -> BfgState:
        """Decode the latest messages (ExecuteTask, i.e. RxFastMsgs +
        RxSlowMsgs) and return a new BfgState snapshot. The snapshot is also
        saved as self.state.

        The C++ code rate-limits this to 10 ms / 1000 ms. That was only there
        to save work on the roboRIO, and decoding a cached frame is cheap, so
        here we just decode everything on every call."""
        self._rx_fast()
        self._rx_slow()
        self._refresh_controller_info()

        s = self._s
        s.firmware_version = self.firmware_version
        s.serial_number = self.serial_number
        s.nickname = bytes(self._nickname[:11]).split(b"\x00", 1)[0].decode("latin-1")
        s.connected = self.is_connected()
        s.timestamp = time.monotonic()

        self.state = copy.deepcopy(s)
        return self.state

    def _rx_fast(self) -> None:
        s = self._s
        if (d := self._rx(CANMsgApiId.POWER)) is not None:
            s.current_A = _s32(d, 0) / 1000.0
            s.voltage_V = _u16(d, 4) / 1000.0
            s.dod_Ah = _s16(d, 6) / 1000.0

        if (d := self._rx(CANMsgApiId.STATE_OF_CHARGE)) is not None:
            s.soc_Ah = _s16(d, 0) / 1000.0
            s.effective_capacity_Ah = _s16(d, 2) / 1000.0
            s.charge_state = d[4]
            s.dod_Wh = _u24(d, 5) / 3600.0

    def _rx_slow(self) -> None:
        s = self._s
        cs, ms = s.cycle_stats, s.match_stats

        if (d := self._rx(CANMsgApiId.CYCLE_CURRENT)) is not None:
            cs.minCurrent_A = _s32(d, 0) / 1000.0
            cs.maxCurrent_A = _s32(d, 4) / 1000.0

        if (d := self._rx(CANMsgApiId.CYCLE_CHARGE)) is not None:
            cs.minVoltage_V = _u16(d, 0) / 1000.0
            cs.maxVoltage_V = _u16(d, 2) / 1000.0
            cs.minDOD_Ah = _s16(d, 4) / 1000.0
            cs.maxDOD_Ah = _s16(d, 6) / 1000.0

        if (d := self._rx(CANMsgApiId.CYCLE_TIME)) is not None:
            cs.chargeTime_s = _u32(d, 0) // 1000
            cs.dischargeTime_s = _u32(d, 4) // 1000

        if (d := self._rx(CANMsgApiId.BATTERY_HEALTH)) is not None:
            s.batt_age_s = _u32(d, 0)
            s.capacity_Ah = _u16(d, 4) / 1000.0
            s.batt_num_cycles = _u16(d, 6)

        if (d := self._rx(CANMsgApiId.MATCH_CURRENT)) is not None:
            ms.minCurrent_A = _s32(d, 0) / 1000.0
            ms.maxCurrent_A = _s32(d, 4) / 1000.0

        if (d := self._rx(CANMsgApiId.MATCH_CHARGE)) is not None:
            ms.minVoltage_V = _u16(d, 0) / 1000.0
            ms.maxVoltage_V = _u16(d, 2) / 1000.0
            ms.minDOD_Ah = _s16(d, 4) / 1000.0
            ms.maxDOD_Ah = _s16(d, 6) / 1000.0

        if (d := self._rx(CANMsgApiId.MATCH_TIME)) is not None:
            ms.chargeTime_s = _u32(d, 0) // 1000
            ms.dischargeTime_s = _u32(d, 4) // 1000

        if (d := self._rx(CANMsgApiId.RMS_CURRENT)) is not None:
            ms.rmsDischargeCurrent_A = _u32(d, 0) / 1000.0
            cs.rmsDischargeCurrent_A = _u32(d, 4) / 1000.0

        if (d := self._rx(CANMsgApiId.CALIBRATION)) is not None:
            s.meas_current_offset = _u32(d, 0)
            s.meas_current_gain = _u32(d, 4)

        if (d := self._rx(CANMsgApiId.CYCLE_ENERGY)) is not None:
            # Energy is sent as a signed 16-bit value in units of 128 J
            cs.minDOD_Wh = (_s16(d, 0) << 7) / 3600.0
            cs.maxDOD_Wh = (_s16(d, 2) << 7) / 3600.0
            cs.startingVoltage_V = _u16(d, 4) / 1000.0
            s.rated_capacity_Ah = _u16(d, 6) / 1000.0

        if (d := self._rx(CANMsgApiId.MATCH_DELTA_ENERGY)) is not None:
            ms.startDOD_Wh = (_s16(d, 0) << 7) / 3600.0
            ms.endDOD_Wh = (_s16(d, 2) << 7) / 3600.0
            ms.startingVoltage_V = _u16(d, 4) / 1000.0
            s.batt_manufacturer = d[6]

        if (d := self._rx(CANMsgApiId.MATCH_DELTA_CHARGE)) is not None:
            ms.startDOD_Ah = _s16(d, 0) / 1000.0
            ms.endDOD_Ah = _s16(d, 2) / 1000.0
            ms.activeTime_s = _u32(d, 4) // 1000

        if (d := self._rx(CANMsgApiId.NICKNAME1)) is not None:
            self._nickname[0:8] = d[0:8]

        if (d := self._rx(CANMsgApiId.NICKNAME2)) is not None:
            self._nickname[8:11] = d[0:3]
            self._nickname[11] = 0

    # ---- JSON / logging ----------------------------------------------------

    def get_bfg_state_json(self, event_name: str = "", match_number: int = 0, team_number: int = 0) -> str:
        """Run update() and return the snapshot as JSON (see BfgState.to_json)."""
        return self.update().to_json(event_name, match_number, team_number)

    def save_log(self, filename: str | os.PathLike | None = None, event_name: str = "",
                 match_type_char: str = "_", match_number: int = 0) -> Path:
        """Write a JSON snapshot. With no filename it goes to ./logs/, named the same way as the C++ version."""
        if not filename:
            log_dir = Path.cwd() / "logs"
            log_dir.mkdir(exist_ok=True)
            t = datetime.now(timezone.utc)
            filename = log_dir / (
                f"BFGSnapshot_{t:%Y%m%d_%H%M%S}_{event_name}_{match_type_char}{match_number}.json"
            )
        path = Path(filename)
        path.write_text(self.get_bfg_state_json(event_name, match_number), encoding="latin-1", errors="replace")
        return path


# --------------------------------------------------------------------------- #
# Convenience wrapper
# --------------------------------------------------------------------------- #


class PWFCanBus:
    """Puts the adapter, the device tracker and the BFG objects behind one
    object. You can pass in your own python-can bus (for example a virtual one
    for testing), or leave it out to auto-detect a gs_usb or PCAN adapter."""

    def __init__(self, bus: can.BusABC | None = None):
        self.can = CanInterface(bus)
        self.tracker = PWFDeviceTracker(self.can)
        self._bfgs: dict[int, BattFuelGauge] = {}

    def open(self) -> bool:
        return self.can.open()

    def close(self) -> None:
        self.can.close()

    def __enter__(self) -> PWFCanBus:
        if not self.open():
            raise RuntimeError("No compatible CAN interface detected")
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def get_bfg(self, sensor_id: int) -> BattFuelGauge:
        """Get the BFG object for this CAN ID. Repeated calls return the same object, like BattFuelGauge_Create."""
        if sensor_id not in self._bfgs:
            self._bfgs[sensor_id] = BattFuelGauge(self.can, self.tracker, sensor_id)
        return self._bfgs[sensor_id]

    def discovered_bfgs(self) -> list[PWFController]:
        """BFGs whose heartbeat we've seen recently."""
        return [
            c for c in self.tracker.get_controller_list()
            if c.device == DeviceType.BFG_SENSOR and c.activeOnBus
        ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with PWFCanBus() as pwf:
        print(f"Using driver: {pwf.can.driver}. Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
                for c in pwf.discovered_bfgs():
                    s = pwf.get_bfg(c.id).update()
                    print(f"[{c.id}] {s.get_nickname()!r:14} {s.get_voltage():6.3f} V {s.get_current():8.3f} A "
                          f"{s.get_remaining_charge_pct():5.1f}%  {s.get_num_cycles()} cycles  "
                          f"{s.get_charge_state_string()}")
        except KeyboardInterrupt:
            pass
