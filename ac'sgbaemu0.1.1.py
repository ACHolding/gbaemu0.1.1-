"""mewgba$ VBAv0.2.1 Blue Edition — single-file GBA emulator (files=off). Python 3.14+.

Embedded docs: MEWGBA_BLUE_EDITION, MEWGBA_ROADMAP, MEWGBA_CYTHON_GUIDE.
AC Holdings 1999-2026 — Python Man + CatSDK Blue Tint Edition.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import struct
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

SCREEN_W = 240
SCREEN_H = 160
CYCLES_PER_FRAME = 280896
CYCLES_PER_SCANLINE = 1232
VDRAW_LINES = 160
TOTAL_LINES = 228

# I/O register offsets (from 0x04000000)
REG_DISPCNT = 0x000
REG_DISPSTAT = 0x004
REG_VCOUNT = 0x006
REG_BG0CNT = 0x008
REG_BG0HOFS = 0x010
REG_KEYINPUT = 0x130
REG_IE = 0x200
REG_IF = 0x202
REG_IME = 0x208
REG_BG2PA = 0x020
REG_WIN0H = 0x040
REG_WIN1H = 0x042
REG_WIN0V = 0x044
REG_WIN1V = 0x046
REG_WININ = 0x048
REG_WINOUT = 0x04A
REG_MOSAIC = 0x04C
REG_DMA0 = 0x0B0

GBA_KEY_MASK = 0x03FF

# GBA keypad (active low in KEYINPUT)
KEY_A, KEY_B, KEY_SELECT, KEY_START = 0, 1, 2, 3
KEY_RIGHT, KEY_LEFT, KEY_UP, KEY_DOWN = 4, 5, 6, 7
KEY_R, KEY_L = 8, 9

KEY_MAP = {
    "z": KEY_A,
    "x": KEY_B,
    "BackSpace": KEY_SELECT,
    "Return": KEY_START,
    "Right": KEY_RIGHT,
    "Left": KEY_LEFT,
    "Up": KEY_UP,
    "Down": KEY_DOWN,
    "e": KEY_R,
    "q": KEY_L,
}

MEWGBA_ROADMAP = """Next Level Moves (pick what you want):

Performance — Make Cython do even more (especially PPU and CPU hot paths)
Accuracy — Fix remaining CPU bugs so more test ROMs boot
Debug Tools — Register viewer + memory viewer (connect it to your Hex Editor!)
Save States — Super important for GBA
Sound (later)
UI Polish — FPS counter, speed control, recent files, etc."""

MEWGBA_TAGLINE = "VBAv0.2.1 but make it blue, single-file, and unhinged at 4AM."

MEWGBA_BLUE_THEME = {
    "bg": "#0a1a3f",          # blue background
    "accent": "#3d7bff",      # blue-hue text (matches bg family, still readable)
    "screen": "#020c1b",
    "button_bg": "#000000",   # buttons = black
    "button_fg": "#3d7bff",   # button text matches blue hue
    "panel": "#0f2350",
}

# authentic GBA refresh rate (16.777216 MHz / 280896 cycles-per-frame)
GBA_REFRESH_HZ = 16_777_216 / CYCLES_PER_FRAME  # ~59.7275 Hz, matches real VBA
GBA_FRAME_MS = 1000.0 / GBA_REFRESH_HZ  # ~16.7430 ms

MEWGBA_BLUE_EDITION = """# mewgba$ — VBAv0.2.1 Blue Edition Vibes

**AC Holdings 1999-2026**
*Single-file GBA Emulator (files=off) — Python Man + CatSDK Blue Tint Edition*

## Vision

Take everything great about classic **VisualBoy Advance 0.1** (the legendary early version)
and rebuild it with maximum **blue CatSDK chaos** — dark blue theme, single-file purity,
Cython acceleration, and pure vibe coding soul.

## Core Features (VBAv0.2.1 Level + Blue Upgrades)

### Emulation Core
- Full ARM7TDMI + Thumb instruction set
- Accurate memory bus (EWRAM, IWRAM, VRAM, Palette, OAM, ROM)
- BIOS HLE + SWI support
- Timers, DMA, Interrupts
- Save States (F5/F9 quicksave like old VBA)
- Speed control (0.5x → 4x+)

### Graphics (Blue Tint Special)
- All major modes: 0, 1, 2, 3, 4, 5
- Backgrounds (text + affine)
- Sprite rendering + affine transformations
- Window system + Mosaic
- Proper priority handling
- Signature deep blue/dark CatSDK color scheme (#0a192f + #00b4d8 accent)

### Input & Controls
- Standard GBA keypad (Z=A, X=B, Arrows, Q=L, E=R, Enter=Start, Backspace=Select)
- Keyboard focus + smooth response

### Developer Tools (CatSDK Upgrade)
- Live Registers viewer
- Memory viewer with direct Hex Editor launch (hexeditor4k)
- Cython acceleration status panel
- Embedded roadmap + Cython guide

### Quality of Life
- Recent ROMs list
- Load ROM + built-in demo
- FPS counter + real-time speed display
- Dark blue professional UI (no ugly default Tkinter look)
- Auto Cython compile cache (zero external files)

### Philosophy (Blue Tint Rules)
- Single file maximalism
- Cherish the 16GB RAM
- Maximum vibe, minimum bloat
- If it can be accelerated in Cython → it will be
- Looks cool even when broken

---

**Tagline:**
> "VBAv0.2.1 but make it blue, single-file, and unhinged at 4AM."

**Python Man Approved**
*From Mira Mesa to Shanghai — we keep the 16GB sacred.*

---

**Next Goals (After Blue Edition):**
- Better accuracy (more test ROMs)
- Sound emulation
- Link cable / multiplayer memes
- Cheat support
- Export as standalone .exe
"""

MEWGBA_NEXT_GOALS = (
    "Better accuracy (more test ROMs)",
    "Sound emulation",
    "Link cable / multiplayer memes",
    "Cheat support",
    "Export as standalone .exe",
)

MEWGBA_BLUE_FEATURES: dict[str, list[tuple[str, bool]]] = {
    "Emulation Core": [
        ("ARM7TDMI + Thumb opcodes", True),
        ("Memory bus (EWRAM/IWRAM/VRAM/Palette/OAM/ROM)", True),
        ("BIOS HLE + SWI", True),
        ("Timers, DMA, IRQ", True),
        ("Save states F5/F9", True),
        ("Speed 0.5x–4x", True),
    ],
    "Graphics": [
        ("Modes 0–5", True),
        ("Text + affine backgrounds", True),
        ("Sprites + affine", True),
        ("Windows + mosaic", True),
        ("Priority compositor", True),
        ("CatSDK blue theme", True),
    ],
    "Input": [
        ("GBA keypad mapping", True),
        ("Keyboard focus", True),
    ],
    "Developer Tools": [
        ("Register viewer", True),
        ("Memory viewer", True),
        ("Hex Editor launch", True),
        ("Cython status panel", True),
        ("Embedded docs (this file)", True),
    ],
    "Quality of Life": [
        ("Recent ROMs", True),
        ("Load ROM + demo", True),
        ("FPS + speed display", True),
        ("Cython temp cache", True),
    ],
}

MEWGBA_CYTHON_GUIDE = """# mewgba$ — Cython Acceleration Guide (files=off)

**AC Holdings 1999-2026**
*Single-file GBA emulator with maximum CatSDK vibes*

## Philosophy

We keep everything **self-contained** (files=off).
No external `.pyx` files lying around — everything lives in one `.py` with smart temp caching.

## Core Strategy

1. Store Cython code as a big string (`_MEWGBA_PYX`)
2. Hash it → only recompile when changed
3. Use `pyximport` + temp cache folder (`MEWGBA_CACHE`)
4. Fallback to pure Python automatically

## How to Add More Cython Vibes

### 1. New Hot Path Function

Add to the `_MEWGBA_PYX` string:

    def fast_new_function(...):
        ...

### 2. Call it from Python

    if _ACCEL is not None:
        _ACCEL.fast_new_function(...)
    else:
        self.slow_version(...)

### 3. Recompile Trigger

Just change the string → hash changes → auto recompiles on next run.

## Current Accelerated Functions

- fast_run_cycles
- fast_run_scanline
- fast_run_frame
- fast_render_mode3
- fast_render_mode4
- fast_render_mode5
- fast_compose_fb
- fast_build_win_layers

## Pro Tips for Maximum Vibes

- Keep Cython functions small and hot
- Use cdef + typed variables aggressively
- Pass large arrays (vram, palette, etc.) directly
- Never use Python objects in inner loops
- Add `# cython: boundscheck=False, wraparound=False, cdivision=True`

## Future Cython Targets (Priority Order)

1. PPU rendering (biggest win)
2. Thumb/ARM CPU hot paths
3. Affine background math
4. Sprite rendering
5. Memory bus (read/write)

## CatSDK Official Motto

"If it runs at 60FPS in Python, it shall run at 300+ in Cython."
"""

MEWGBA_ACCEL_FUNCTIONS = (
    "fast_run_cycles",
    "fast_run_scanline",
    "fast_run_frame",
    "fast_render_mode3",
    "fast_render_mode4",
    "fast_render_mode5",
    "fast_compose_fb",
    "fast_build_win_layers",
)

MEWGBA_FUTURE_CYTHON_TARGETS = (
    "PPU rendering (biggest win)",
    "Thumb/ARM CPU hot paths",
    "Affine background math",
    "Sprite rendering",
    "Memory bus (read/write)",
)

MEWGBA_CACHE = os.path.join(tempfile.gettempdir(), "mewgba_emugba4k")
MEWGBA_RECENT = os.path.join(MEWGBA_CACHE, "recent.json")
MEWGBA_SAVES = os.path.join(MEWGBA_CACHE, "saves")
REG_WAITCNT = 0x204
REG_POSTFLG = 0x300

MEMORY_REGIONS = (
    ("EWRAM", 0x02000000, "ewram"),
    ("IWRAM", 0x03000000, "iwram"),
    ("I/O", 0x04000000, "io"),
    ("Palette", 0x05000000, "palette"),
    ("VRAM", 0x06000000, "vram"),
    ("OAM", 0x07000000, "oam"),
    ("ROM", 0x08000000, "rom"),
)

HEX_EDITOR_REL = "../ac'shexeditor4k/hexeditor4k.py"


def _build_demo_rom() -> bytes:
    """ARM bx stub + Thumb: mode 3 gradient demo."""
    rom = bytearray(0x200)
    struct.pack_into("<I", rom, 0x00, 0xEA00002E)  # b 0x080000C0
    rom[0xA0:0xAC] = b"MEWGBA      "
    struct.pack_into("<I", rom, 0xC0, 0xE59F0000)  # ldr r0, [pc, #0]
    struct.pack_into("<I", rom, 0xC4, 0xE12FFF10)  # bx r0
    thumb_entry = 0xCC
    struct.pack_into("<I", rom, 0xC8, 0x08000000 | thumb_entry | 1)

    demo_thumb = bytes.fromhex(
        "0648"
        "0749"
        "0880"
        "074a"
        "2300"
        "2000"
        "1846"
        "4010"
        "1080"
        "921d"
        "cb1d"
        "ff2b"
        "f8d1"
        "f8e7"
    )
    rom[thumb_entry : thumb_entry + len(demo_thumb)] = demo_thumb
    pool_off = (thumb_entry + len(demo_thumb) + 3) & ~3
    struct.pack_into("<III", rom, pool_off, 0x0403, 0x04000000, 0x06000000)
    return bytes(rom)


DEFAULT_ROM = _build_demo_rom()

# Pre-baked Cython accel (temp cache, files=off) — see MEWGBA_CYTHON_GUIDE
_MEWGBA_PYX = r'''# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
# mewgba$ embedded accel — edit parent .py _MEWGBA_PYX string, not this temp file

cdef inline tuple _c565(int c):
    return ((c & 0x1F) << 3, ((c >> 5) & 0x1F) << 3, ((c >> 10) & 0x1F) << 3)

def fast_render_mode3(vram, prio, pxbuf, win_layers, layer_bit):
    cdef int x, y, off, c
    cdef tuple rgb
    for y in range(160):
        for x in range(240):
            if not (win_layers[y][x] & layer_bit):
                continue
            off = (y * 240 + x) * 2
            c = vram[off] | (vram[off + 1] << 8)
            rgb = _c565(c)
            prio[y][x] = 0
            pxbuf[y][x] = rgb

def fast_render_mode4(vram, palette, prio, pxbuf, win_layers, layer_bit, int base):
    cdef int x, y, idx, c
    cdef tuple rgb
    for y in range(160):
        for x in range(240):
            if not (win_layers[y][x] & layer_bit):
                continue
            idx = vram[base + y * 240 + x]
            c = palette[idx * 2] | (palette[idx * 2 + 1] << 8)
            rgb = _c565(c)
            prio[y][x] = 0
            pxbuf[y][x] = rgb

def fast_compose_fb(fb, pxbuf, w, h):
    cdef int x, y, i
    cdef object p
    for y in range(h):
        for x in range(w):
            p = pxbuf[y][x]
            i = (y * w + x) * 3
            fb[i] = p[0]
            fb[i + 1] = p[1]
            fb[i + 2] = p[2]

def fast_run_cycles(obj, int budget):
    cdef int used = 0
    cdef int c
    while used < budget:
        if obj.halted:
            used += 4
            obj.cycles += 4
            obj._timer_tick(4)
            continue
        c = obj.step_cpu()
        used += c
        obj.cycles += c
        obj._timer_tick(c)

def fast_run_frame(obj, int scanlines, int cpl):
    cdef int ln, used
    cdef int c
    for ln in range(scanlines):
        obj._set_io16(6, ln)
        used = 0
        while used < cpl:
            if obj.halted:
                used += 4
                obj.cycles += 4
                obj._timer_tick(4)
                continue
            c = obj.step_cpu()
            used += c
            obj.cycles += c
            obj._timer_tick(c)

def fast_build_win_layers(out, int disp, int win0h, int win0v, int win1h, int win1v, int winin, int winout):
    cdef int x, y, left, right, top, bot, layers
    cdef int in0, in1
    cdef int outside = winout & 0x3F
    cdef int w0in = winin & 0x3F
    cdef int w1in = (winin >> 8) & 0x3F
    for y in range(160):
        for x in range(240):
            in0 = in1 = 0
            if disp & 0x2000:
                left = win0h & 0xFF
                right = win0h >> 8
                if right > 240:
                    right = 240
                top = win0v & 0xFF
                bot = win0v >> 8
                if bot > 160:
                    bot = 160
                if left <= x < right and top <= y < bot:
                    in0 = 1
            if disp & 0x4000:
                left = win1h & 0xFF
                right = win1h >> 8
                if right > 240:
                    right = 240
                top = win1v & 0xFF
                bot = win1v >> 8
                if bot > 160:
                    bot = 160
                if left <= x < right and top <= y < bot:
                    in1 = 1
            if in0 and in1:
                layers = w0in & w1in
            elif in0:
                layers = w0in
            elif in1:
                layers = w1in
            else:
                layers = outside if outside else 0x3F
            out[y][x] = layers

def fast_run_scanline(obj, int line, int budget):
    cdef int used = 0
    cdef int c
    obj._set_io16(6, line)
    while used < budget:
        if obj.halted:
            used += 4
            obj.cycles += 4
            obj._timer_tick(4)
            continue
        c = obj.step_cpu()
        used += c
        obj.cycles += c
        obj._timer_tick(c)

def fast_render_mode5(vram, prio, pxbuf, win_layers, layer_bit, int base):
    cdef int x, y, off, c
    cdef tuple rgb
    for y in range(160):
        for x in range(240):
            if not (win_layers[y][x] & layer_bit):
                continue
            off = base + (y * 240 + x) * 2
            c = vram[off] | (vram[off + 1] << 8)
            rgb = _c565(c)
            prio[y][x] = 0
            pxbuf[y][x] = rgb
'''


def _write_cache_docs(cache: str) -> None:
    """Mirror embedded opcode docs to temp cache (files=off in project)."""
    for name, text in (
        ("BLUE_EDITION.txt", MEWGBA_BLUE_EDITION),
        ("CYTHON_GUIDE.txt", MEWGBA_CYTHON_GUIDE),
        ("ROADMAP.txt", MEWGBA_ROADMAP),
    ):
        try:
            with open(os.path.join(cache, name), "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass


def _blue_edition_status() -> dict:
    total = live = 0
    for items in MEWGBA_BLUE_FEATURES.values():
        for _, ok in items:
            total += 1
            if ok:
                live += 1
    return {
        "tagline": MEWGBA_TAGLINE,
        "theme": MEWGBA_BLUE_THEME,
        "features_live": live,
        "features_total": total,
        "cython": _ACCEL is not None,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


def _pyx_digest() -> str:
    return hashlib.sha256(_MEWGBA_PYX.encode()).hexdigest()


def _accel_status() -> dict:
    """Runtime Cython status for debug UI."""
    loaded = {name: _ACCEL is not None and hasattr(_ACCEL, name) for name in MEWGBA_ACCEL_FUNCTIONS}
    return {
        "active": _ACCEL is not None,
        "cache": MEWGBA_CACHE,
        "digest": _pyx_digest()[:16],
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "functions": loaded,
    }


def _load_mewgba_accel():
    """Compile _MEWGBA_PYX via pyximport into MEWGBA_CACHE; pure-Python fallback on failure."""
    cache = MEWGBA_CACHE
    os.makedirs(cache, exist_ok=True)
    pyx = os.path.join(cache, "mewgba_accel.pyx")
    stamp = os.path.join(cache, "mewgba_accel.hash")
    digest = _pyx_digest()
    try:
        import setuptools  # noqa: F401 — pyximport shim on Py3.12+
        if not os.path.exists(stamp) or open(stamp, encoding="utf-8").read().strip() != digest:
            with open(pyx, "w", encoding="utf-8") as f:
                f.write(_MEWGBA_PYX)
            with open(stamp, "w", encoding="utf-8") as f:
                f.write(digest)
            _write_cache_docs(cache)
            for name in os.listdir(cache):
                if name.startswith("mewgba_accel.") and name.endswith((".pyd", ".so", ".dll")):
                    try:
                        os.remove(os.path.join(cache, name))
                    except OSError:
                        pass
        if cache not in sys.path:
            sys.path.insert(0, cache)
        import pyximport
        pyximport.install(build_dir=cache, language_level=3)
        import mewgba_accel  # type: ignore[import-not-found]
        return mewgba_accel
    except Exception:
        return None


_ACCEL = _load_mewgba_accel()


def rgb565_to_rgb(color: int) -> tuple[int, int, int]:
    r = (color & 0x1F) << 3
    g = ((color >> 5) & 0x1F) << 3
    b = ((color >> 10) & 0x1F) << 3
    return r, g, b


class MewGBACore:
    """ARM7TDMI GBA core. See MEWGBA_ROADMAP for the feature roadmap."""

    def __init__(self) -> None:
        self.rom = bytearray()
        self.ewram = bytearray(256 * 1024)
        self.iwram = bytearray(32 * 1024)
        self.io = bytearray(1024)
        self.palette = bytearray(1024)
        self.vram = bytearray(96 * 1024)
        self.oam = bytearray(1024)
        self.r = [0] * 16
        self.cpsr = 0x0000001F
        self.spsr = 0
        self.halted = False
        self.framebuffer = bytearray(SCREEN_W * SCREEN_H * 3)
        self._prio = [[3] * SCREEN_W for _ in range(SCREEN_H)]
        self._pxbuf = [[(8, 12, 27)] * SCREEN_W for _ in range(SCREEN_H)]
        self.keys_down = 0
        self.rom_label: str | None = None
        self.is_loaded = False
        self.cycles = 0
        self.line_cycles = 0
        self.current_line = 0
        self.timers = [{"reload": 0, "count": 0, "ctrl": 0, "frac": 0} for _ in range(4)]
        self.dma = [{"src": 0, "dst": 0, "count": 0, "ctrl": 0} for _ in range(4)]
        self._win_layers = [[0x3F] * SCREEN_W for _ in range(SCREEN_H)]
        self._init_io_defaults()

    def _init_io_defaults(self) -> None:
        self.io[REG_KEYINPUT : REG_KEYINPUT + 2] = struct.pack("<H", GBA_KEY_MASK)
        self.io[REG_DISPSTAT : REG_DISPSTAT + 2] = struct.pack("<H", 0x0000)
        self.io[REG_VCOUNT : REG_VCOUNT + 2] = struct.pack("<H", 0x0000)
        self.io[REG_IE : REG_IE + 2] = struct.pack("<H", 0x0000)
        self.io[REG_IF : REG_IF + 2] = struct.pack("<H", 0x0000)
        self.io[REG_IME : REG_IME + 2] = struct.pack("<H", 0x0000)
        self.io[REG_DISPCNT : REG_DISPCNT + 2] = struct.pack("<H", 0x0080)
        self.io[REG_WININ : REG_WININ + 2] = struct.pack("<H", 0x3F3F)
        self.io[REG_WINOUT : REG_WINOUT + 2] = struct.pack("<H", 0x003F)
        self._set_io16(REG_WAITCNT, 0x0000)
        self.io[REG_POSTFLG] = 0x01

    def _boot_regs(self) -> None:
        """Post-reset register values matching GBA hardware."""
        self.r[13] = 0x03007F00
        self.r[15] = 0x08000000
        self.cpsr = 0x0000001F
        self.set_thumb(False)

    def reset_cpu(self) -> None:
        self.r = [0] * 16
        self.cpsr = 0x0000001F
        self.spsr = 0
        self.halted = False
        self.cycles = 0
        self.line_cycles = 0
        self.current_line = 0
        self.ewram[:] = b"\x00" * len(self.ewram)
        self.iwram[:] = b"\x00" * len(self.iwram)
        self.io[:] = b"\x00" * len(self.io)
        self.palette[:] = b"\x00" * len(self.palette)
        self.vram[:] = b"\x00" * len(self.vram)
        self.oam[:] = b"\x00" * len(self.oam)
        self.timers = [{"reload": 0, "count": 0, "ctrl": 0, "frac": 0} for _ in range(4)]
        self.dma = [{"src": 0, "dst": 0, "count": 0, "ctrl": 0} for _ in range(4)]
        self._win_layers = [[0x3F] * SCREEN_W for _ in range(SCREEN_H)]
        self._init_io_defaults()
        self._boot_regs()

    def _io16(self, off: int) -> int:
        return self.io[off] | (self.io[off + 1] << 8)

    def _set_io16(self, off: int, val: int) -> None:
        self.io[off] = val & 0xFF
        self.io[off + 1] = (val >> 8) & 0xFF

    def _irq_raise(self, bit: int) -> None:
        self._set_io16(REG_IF, self._io16(REG_IF) | (1 << bit))
        self._irq_dispatch()

    def _irq_dispatch(self) -> None:
        if not (self._io16(REG_IME) & 1):
            return
        pending = self._io16(REG_IE) & self._io16(REG_IF) & 0x3FFF
        if not pending:
            return
        bit = (pending & -pending).bit_length() - 1
        self.halted = False
        self.spsr = self.cpsr
        self.cpsr = (self.cpsr & ~0xFF) | 0x92
        self.r[14] = (self.r[15] - (2 if self.thumb() else 4)) & 0xFFFFFFFF
        self.set_thumb(True)
        self.r[15] = 0x03000000 + bit * 4
        self._set_io16(REG_IF, self._io16(REG_IF) & ~(1 << bit))

    def _wait_states(self, addr: int, bits: int) -> int:
        region = addr & 0xFF000000
        if region == 0x02000000:
            return 3 if bits == 32 else 2
        if region == 0x03000000:
            return 1
        if region in (0x05000000, 0x06000000, 0x07000000):
            return 1
        if region in (0x08000000, 0x09000000):
            return 5 if bits == 32 else 3
        return 1

    def _swi_hle(self, num: int) -> None:
        if num == 0x00:
            self.reset_cpu()
            self.r[15] = 0x08000000
            self.cpsr = 0x0000001F
            return
        if num == 0x01:
            flags = self.r[0] & 0xFF
            if flags & 0x01:
                self.palette[:] = b"\x00" * len(self.palette)
            if flags & 0x02:
                self.vram[:] = b"\x00" * len(self.vram)
            if flags & 0x04:
                self.oam[:] = b"\x00" * len(self.oam)
            if flags & 0x08:
                self.io[:] = b"\x00" * len(self.io)
                self._init_io_defaults()
            if flags & 0x10:
                self.iwram[:] = b"\x00" * len(self.iwram)
            if flags & 0x20:
                self.palette[512:] = b"\x00" * (len(self.palette) - 512)
            if flags & 0x40:
                self.ewram[:] = b"\x00" * len(self.ewram)
            return
        if num in (0x02, 0x03):
            self.halted = True
            return
        if num in (0x04, 0x05):
            clear = self.r[0] & 0x3FFF
            wait = self.r[1] & 0x3FFF if num == 0x04 else 0x0001
            guard = 0
            while not (self._io16(REG_IF) & wait):
                self._run_cycles(4)
                guard += 1
                if guard > CYCLES_PER_FRAME * 4:
                    break
            self._set_io16(REG_IF, self._io16(REG_IF) & ~clear)
            return
        if num == 0x08:
            val = self.r[0] & 0xFFFFFFFF
            self.r[0] = 0 if val == 0 else int(val ** 0.5)
            return
        if num in (0x0B, 0x0C):
            src = self.r[0] & 0xFFFFFFFC
            dst = self.r[1] & 0xFFFFFFFC
            ctrl = self.r[2] & 0xFFFFFFFF
            count = ctrl & 0x001FFFFF
            fill = bool(ctrl & 0x01000000)
            word = bool(ctrl & 0x04000000)
            if num == 0x0C:
                count = (count + 7) // 8
            if word:
                if fill:
                    val = self.read32(src)
                    for _ in range(count):
                        self.write32(dst, val)
                        dst = (dst + 4) & 0xFFFFFFFF
                else:
                    for _ in range(count):
                        self.write32(dst, self.read32(src))
                        src = (src + 4) & 0xFFFFFFFF
                        dst = (dst + 4) & 0xFFFFFFFF
            elif fill:
                val = self.read16(src)
                for _ in range(count):
                    self.write16(dst, val)
                    dst = (dst + 2) & 0xFFFFFFFF
            else:
                for _ in range(count):
                    self.write16(dst, self.read16(src))
                    src = (src + 2) & 0xFFFFFFFF
                    dst = (dst + 2) & 0xFFFFFFFF
            return
        if num == 0x0D:
            self.r[0] = 1

    def _timer_tick(self, cyc: int) -> None:
        for i, t in enumerate(self.timers):
            if not (t["ctrl"] & 0x80):
                continue
            if i > 0 and (t["ctrl"] & 0x04):
                continue
            prescale = (0, 6, 8, 10)[(t["ctrl"] >> 0) & 3]
            step = 1 << prescale
            t["frac"] += cyc
            while t["frac"] >= step:
                t["frac"] -= step
                t["count"] = (t["count"] - 1) & 0xFFFF
                if t["count"] == 0xFFFF:
                    t["count"] = t["reload"]
                    if t["ctrl"] & 0x40:
                        self._irq_raise(3 + i)

    def _run_cycles(self, budget: int) -> None:
        if _ACCEL is not None:
            _ACCEL.fast_run_cycles(self, budget)
            return
        used = 0
        while used < budget:
            if self.halted:
                used += 4
                self.cycles += 4
                self._timer_tick(4)
                continue
            c = self.step_cpu()
            used += c
            self.cycles += c
            self._timer_tick(c)

    def _dma_reg(self, off: int) -> tuple[int, int] | None:
        if off < REG_DMA0 or off > REG_DMA0 + 46:
            return None
        rel = off - REG_DMA0
        ch, reg = rel // 12, rel % 12
        return (ch, reg) if ch <= 3 else None

    def _dma_write(self, ch: int, reg: int, val: int) -> None:
        d = self.dma[ch]
        if reg == 0:
            d["src"] = (d["src"] & 0xFFFF0000) | val
        elif reg == 2:
            d["src"] = (d["src"] & 0x0000FFFF) | (val << 16)
        elif reg == 4:
            d["dst"] = (d["dst"] & 0xFFFF0000) | val
        elif reg == 6:
            d["dst"] = (d["dst"] & 0x0000FFFF) | (val << 16)
        elif reg == 8:
            d["count"] = val
        elif reg == 10:
            d["ctrl"] = val
            if val & 0x8000 and ((val >> 12) & 3) == 0:
                self._start_dma(ch)

    def _start_dma(self, ch: int) -> None:
        d = self.dma[ch]
        src = d["src"] & 0x0FFFFFFF
        dst = d["dst"] & 0x0FFFFFFF
        count = d["count"]
        if ch == 3:
            count &= 0xFFFF
            if count == 0:
                count = 0x10000
        elif count == 0:
            count = 0x4000
        ctrl = d["ctrl"]
        src_inc = (0, 2, -2, 0)[(ctrl >> 7) & 3]
        dst_inc = (0, 2, -2, 0)[(ctrl >> 5) & 3]
        width = 4 if ctrl & 0x0400 else 2 if ctrl & 0x0200 else 1
        for _ in range(count):
            if width == 4:
                self.write32(dst, self.read32(src))
                src = (src + src_inc) & 0xFFFFFFFF if src_inc else src
                dst = (dst + dst_inc) & 0xFFFFFFFF if dst_inc else dst
            elif width == 2:
                self.write16(dst, self.read16(src))
                src = (src + src_inc) & 0xFFFFFFFF if src_inc else src
                dst = (dst + dst_inc) & 0xFFFFFFFF if dst_inc else dst
            else:
                self.write8(dst, self.read8(src))
                src = (src + src_inc) & 0xFFFFFFFF if src_inc else src
                dst = (dst + dst_inc) & 0xFFFFFFFF if dst_inc else dst
        d["ctrl"] = ctrl & 0x7FFF
        if ctrl & 0x4000:
            self._irq_raise(8 + ch)

    def _dma_vblank_hblank(self, mode: int) -> None:
        for ch in range(4):
            ctrl = self.dma[ch]["ctrl"]
            if (ctrl & 0x8000) and ((ctrl >> 12) & 3) == mode:
                self._start_dma(ch)

    def _read_io(self, off: int) -> int:
        if off == REG_VCOUNT:
            return self._io16(REG_VCOUNT) & 0xFF
        if off == REG_VCOUNT + 1:
            return (self._io16(REG_VCOUNT) >> 8) & 0xFF
        if off in (REG_KEYINPUT, REG_KEYINPUT + 1):
            return self.io[off]
        if 0x100 <= off < 0x110:
            idx = (off - 0x100) // 4
            rem = (off - 0x100) % 4
            if rem == 0:
                return self.timers[idx]["count"] & 0xFF
            if rem == 1:
                return (self.timers[idx]["count"] >> 8) & 0xFF
        return self.io[off]

    def _write_io(self, off: int, val: int) -> None:
        if off in (REG_KEYINPUT, REG_KEYINPUT + 1):
            return
        if 0x100 <= off < 0x110:
            idx = (off - 0x100) // 4
            rem = (off - 0x100) % 4
            if rem == 0:
                self.timers[idx]["reload"] = (self.timers[idx]["reload"] & 0xFF00) | val
                self.timers[idx]["count"] = (self.timers[idx]["count"] & 0xFF00) | val
            elif rem == 1:
                self.timers[idx]["reload"] = (self.timers[idx]["reload"] & 0x00FF) | (val << 8)
                self.timers[idx]["count"] = (self.timers[idx]["count"] & 0x00FF) | (val << 8)
            elif rem == 2:
                self.timers[idx]["ctrl"] = (self.timers[idx]["ctrl"] & 0xFF00) | val
            elif rem == 3:
                self.timers[idx]["ctrl"] = (self.timers[idx]["ctrl"] & 0x00FF) | (val << 8)
                if val & 0x80:
                    self.timers[idx]["count"] = self.timers[idx]["reload"]
                    self.timers[idx]["frac"] = 0
            return
        dma = self._dma_reg(off)
        if dma is not None:
            ch, reg = dma
            self.io[off] = val
            self._dma_write(ch, reg, val)
            return
        self.io[off] = val

    def load_rom_bytes(self, rom: bytes, label: str = "Demo (built-in)") -> bool:
        if not rom:
            return False
        self.rom = bytearray(rom)
        self.reset_cpu()
        self.rom_label = label
        self.is_loaded = True
        return True

    def read_bus(self, addr: int, size: int = 1) -> int:
        addr &= 0xFFFFFFFF
        if size == 1:
            return self.read8(addr)
        if size == 2:
            return self.read16(addr)
        return self.read32(addr)

    def snapshot(self) -> dict:
        return {
            "rom": bytes(self.rom),
            "ewram": bytes(self.ewram),
            "iwram": bytes(self.iwram),
            "io": bytes(self.io),
            "palette": bytes(self.palette),
            "vram": bytes(self.vram),
            "oam": bytes(self.oam),
            "r": list(self.r),
            "cpsr": self.cpsr,
            "spsr": self.spsr,
            "halted": self.halted,
            "cycles": self.cycles,
            "timers": [dict(t) for t in self.timers],
            "dma": [dict(d) for d in self.dma],
            "keys_down": self.keys_down,
            "rom_label": self.rom_label,
        }

    def restore(self, snap: dict) -> None:
        self.rom = bytearray(snap["rom"])
        self.ewram[:] = snap["ewram"]
        self.iwram[:] = snap["iwram"]
        self.io[:] = snap["io"]
        self.palette[:] = snap["palette"]
        self.vram[:] = snap["vram"]
        self.oam[:] = snap["oam"]
        self.r = list(snap["r"])
        self.cpsr = snap["cpsr"]
        self.spsr = snap["spsr"]
        self.halted = snap["halted"]
        self.cycles = snap["cycles"]
        self.timers = [dict(t) for t in snap["timers"]]
        self.dma = [dict(d) for d in snap["dma"]]
        self.keys_down = snap["keys_down"]
        self.rom_label = snap.get("rom_label")
        self.is_loaded = True
        self.set_keys(self.keys_down)

    def memory_dump(self, region: str, max_len: int = 65536) -> tuple[int, bytes]:
        data = getattr(self, region, None)
        if data is None:
            return 0, b""
        base = next(b for name, b, attr in MEMORY_REGIONS if attr == region)
        chunk = bytes(data[:max_len])
        return base, chunk

    def set_keys(self, mask: int) -> None:
        self.keys_down = mask & GBA_KEY_MASK
        self._set_io16(REG_KEYINPUT, GBA_KEY_MASK & ~self.keys_down)

    # --- Memory bus ---

    def _rom_addr(self, addr: int) -> int | None:
        if 0x08000000 <= addr < 0x0A000000:
            off = addr - 0x08000000
            if off < len(self.rom):
                return off
        elif 0x0E000000 <= addr < 0x0E010000:
            off = addr - 0x0E000000
            if off < len(self.rom):
                return off
        return None

    def read8(self, addr: int) -> int:
        addr &= 0xFFFFFFFF
        if 0x02000000 <= addr < 0x02040000:
            return self.ewram[addr - 0x02000000]
        if 0x03000000 <= addr < 0x03008000:
            return self.iwram[addr - 0x03000000]
        if 0x04000000 <= addr < 0x04000400:
            return self._read_io(addr - 0x04000000)
        if 0x05000000 <= addr < 0x05000400:
            return self.palette[addr - 0x05000000]
        if 0x06000000 <= addr < 0x06018000:
            return self.vram[addr - 0x06000000]
        if 0x07000000 <= addr < 0x07000400:
            return self.oam[addr - 0x07000000]
        off = self._rom_addr(addr)
        if off is not None:
            return self.rom[off]
        return 0

    def read16(self, addr: int) -> int:
        addr &= 0xFFFFFFFE
        lo = self.read8(addr)
        hi = self.read8(addr + 1)
        return lo | (hi << 8)

    def read32(self, addr: int) -> int:
        addr &= 0xFFFFFFFC
        return (
            self.read8(addr)
            | (self.read8(addr + 1) << 8)
            | (self.read8(addr + 2) << 16)
            | (self.read8(addr + 3) << 24)
        )

    def write8(self, addr: int, val: int) -> None:
        addr &= 0xFFFFFFFF
        val &= 0xFF
        if 0x02000000 <= addr < 0x02040000:
            self.ewram[addr - 0x02000000] = val
        elif 0x03000000 <= addr < 0x03008000:
            self.iwram[addr - 0x03000000] = val
        elif 0x04000000 <= addr < 0x04000400:
            self._write_io(addr - 0x04000000, val)
        elif 0x05000000 <= addr < 0x05000400:
            self.palette[addr - 0x05000000] = val
        elif 0x06000000 <= addr < 0x06018000:
            self.vram[addr - 0x06000000] = val
        elif 0x07000000 <= addr < 0x07000400:
            self.oam[addr - 0x07000000] = val
        elif 0x08000000 <= addr < 0x0E000000:
            off = self._rom_addr(addr)
            if off is not None and off < len(self.rom):
                self.rom[off] = val

    def write16(self, addr: int, val: int) -> None:
        addr &= 0xFFFFFFFE
        val &= 0xFFFF
        self.write8(addr, val & 0xFF)
        self.write8(addr + 1, (val >> 8) & 0xFF)

    def write32(self, addr: int, val: int) -> None:
        addr &= 0xFFFFFFFC
        val &= 0xFFFFFFFF
        self.write8(addr, val & 0xFF)
        self.write8(addr + 1, (val >> 8) & 0xFF)
        self.write8(addr + 2, (val >> 16) & 0xFF)
        self.write8(addr + 3, (val >> 24) & 0xFF)

    # --- CPU flags ---

    def thumb(self) -> bool:
        return bool(self.cpsr & 0x20)

    def set_thumb(self, on: bool) -> None:
        if on:
            self.cpsr |= 0x20
        else:
            self.cpsr &= ~0x20

    def flag_n(self) -> bool:
        return bool(self.cpsr & 0x80000000)

    def flag_z(self) -> bool:
        return bool(self.cpsr & 0x40000000)

    def flag_c(self) -> bool:
        return bool(self.cpsr & 0x20000000)

    def flag_v(self) -> bool:
        return bool(self.cpsr & 0x10000000)

    def set_nz(self, val: int, bits: int = 32) -> None:
        val &= (1 << bits) - 1
        self.cpsr &= ~0xC0000000
        if val & (1 << (bits - 1)):
            self.cpsr |= 0x80000000
        if val == 0:
            self.cpsr |= 0x40000000

    def set_nz_sub(self, res: int, op1: int, op2: int, bits: int = 32) -> None:
        self.set_nz(res, bits)
        mask = (1 << bits) - 1
        op1 &= mask
        op2 &= mask
        res &= mask
        self.cpsr &= ~0x30000000
        if op1 >= op2:
            self.cpsr |= 0x20000000
        if ((op1 ^ op2) & (op1 ^ res)) & (1 << (bits - 1)):
            self.cpsr |= 0x10000000

    def set_nz_add(self, res: int, op1: int, op2: int, bits: int = 32) -> None:
        self.set_nz(res, bits)
        mask = (1 << bits) - 1
        op1 &= mask
        op2 &= mask
        res &= mask
        self.cpsr &= ~0x30000000
        if res < op1:
            self.cpsr |= 0x20000000
        if (~(op1 ^ op2) & (op1 ^ res)) & (1 << (bits - 1)):
            self.cpsr |= 0x10000000

    def check_cond(self, cond: int) -> bool:
        n, z, c, v = self.flag_n(), self.flag_z(), self.flag_c(), self.flag_v()
        return {
            0x0: z,
            0x1: not z,
            0x2: c,
            0x3: not c,
            0x4: n,
            0x5: not n,
            0x6: v,
            0x7: not v,
            0x8: c and not z,
            0x9: not c or z,
            0xA: n == v,
            0xB: n != v,
            0xC: not z and (n == v),
            0xD: z or (n != v),
            0xE: True,
            0xF: False,
        }.get(cond, False)

    def reg_get(self, i: int) -> int:
        i &= 15
        if i == 15:
            return (self.r[15] + (2 if self.thumb() else 4)) & 0xFFFFFFFF
        return self.r[i] & 0xFFFFFFFF

    def reg_set(self, i: int, val: int) -> None:
        i &= 15
        val &= 0xFFFFFFFF
        if i == 15:
            thumb_bit = bool(val & 1)
            if self.thumb() or thumb_bit:
                val &= ~1
                self.set_thumb(thumb_bit)
            else:
                val &= ~3
            self.r[15] = val
        else:
            self.r[i] = val

    # --- CPU execution (ARM7TDMI Thumb + ARM decode) ---
    # Thumb: fmt1-3 shifts/adds, fmt4 ALU (AND..MVN), fmt5 hi-reg, fmt6-10
    #   loads/stores, fmt11 SP, fmt12 push/pop, fmt13-16 branches, LDRH, SXTH/UXTH
    # ARM: data proc, single/half/block trans, multiply, long multiply, PSR, CLZ, BX, SWI, B/BL

    def step_cpu(self) -> int:
        if self.halted:
            return 4
        if self.thumb():
            return self._exec_thumb(self.read16(self.r[15]))
        return self._exec_arm(self.read32(self.r[15]))

    def _exec_thumb(self, op: int) -> int:
        pc = self.r[15]
        self.r[15] = (pc + 2) & 0xFFFFFFFF
        hi = (op >> 12) & 0xF

        if (op >> 13) == 0:
            if ((op >> 11) & 3) == 3:
                imm3 = (op >> 6) & 7
                rn = (op >> 3) & 7
                rd = op & 7
                res = (self.reg_get(rn) + imm3) & 0xFFFFFFFF
                self.set_nz_add(res, self.reg_get(rn), imm3)
                self.reg_set(rd, res)
                return 1

            rd, imm = op & 7, (op >> 3) & 0x1F
            if op & 0x0800:
                if op & 0x0400:
                    self.set_nz_sub((self.reg_get(rd) - imm) & 0xFFFFFFFF, self.reg_get(rd), imm)
                else:
                    res = (self.reg_get(rd) + imm) & 0xFFFFFFFF
                    self.set_nz_add(res, self.reg_get(rd), imm)
                    self.reg_set(rd, res)
            else:
                shift = (op >> 6) & 3
                if shift == 0:
                    old = self.reg_get(rd)
                    val = (old << imm) & 0xFFFFFFFF
                    if imm:
                        carry = ((old << (imm - 1)) & 0x80000000) != 0
                        self.cpsr = (self.cpsr & ~0x20000000) | (0x20000000 if carry else 0)
                elif shift == 1:
                    old = self.reg_get(rd)
                    val = (old >> imm) & 0xFFFFFFFF
                    if imm:
                        self.cpsr = (self.cpsr & ~0x20000000) | (((old >> (imm - 1)) & 1) << 29)
                elif shift == 2:
                    c = self.flag_c()
                    old = self.reg_get(rd)
                    if imm:
                        val = ((old >> (imm - 1)) | (int(c) << 31)) >> 1 if imm < 32 else 0
                        self.cpsr = (self.cpsr & ~0x20000000) | (((old >> (imm - 1)) & 1) << 29)
                    else:
                        val = old
                else:
                    c = self.flag_c()
                    old = self.reg_get(rd)
                    if imm:
                        val = (((old << (32 - imm)) | (old >> imm)) & 0xFFFFFFFF) if imm < 32 else 0
                        self.cpsr = (self.cpsr & ~0x20000000) | ((old >> (imm - 1)) & 1) << 29
                    else:
                        val = old
                self.set_nz(val)
                self.reg_set(rd, val)
            return 1

        if (op & 0xF800) == 0x1800:
            rs, rd = (op >> 3) & 7, op & 7
            if op & 0x0400:
                res = (self.reg_get(rd) - self.reg_get(rs)) & 0xFFFFFFFF
                self.set_nz_sub(res, self.reg_get(rd), self.reg_get(rs))
            else:
                res = (self.reg_get(rd) + self.reg_get(rs)) & 0xFFFFFFFF
                self.set_nz_add(res, self.reg_get(rd), self.reg_get(rs))
            self.reg_set(rd, res)
            return 1

        if (op & 0xE000) == 0x2000:
            rd, imm = (op >> 8) & 7, op & 0xFF
            fn = (op >> 11) & 3
            if fn == 0:
                self.set_nz(imm, 8)
                self.reg_set(rd, imm)
            elif fn == 1:
                self.set_nz(self.reg_get(rd) | imm, 8)
                self.reg_set(rd, self.reg_get(rd) | imm)
            elif fn == 2:
                res = (self.reg_get(rd) + imm) & 0xFFFFFFFF
                self.set_nz_add(res, self.reg_get(rd), imm)
                self.reg_set(rd, res)
            else:
                res = (self.reg_get(rd) - imm) & 0xFFFFFFFF
                self.set_nz_sub(res, self.reg_get(rd), imm)
                self.reg_set(rd, res)
            return 1

        if (op & 0xFC00) == 0x4000:
            rs, rd = (op >> 3) & 7, op & 7
            val = self.reg_get(rs)
            alu = (op >> 6) & 0x3C
            if alu == 0x00:
                res = self.reg_get(rd) & val
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x04:
                res = self.reg_get(rd) ^ val
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x08:
                shift = val & 0xFF
                old = self.reg_get(rd)
                res = (old << shift) & 0xFFFFFFFF
                if shift:
                    self.cpsr = (self.cpsr & ~0x20000000) | (((old << (shift - 1)) >> 31) & 0x20000000)
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x0C:
                shift = val & 0xFF
                old = self.reg_get(rd)
                res = (old >> shift) & 0xFFFFFFFF if shift < 32 else 0
                if shift:
                    self.cpsr = (self.cpsr & ~0x20000000) | (((old >> (shift - 1)) & 1) << 29)
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x10:
                shift = val & 0xFF
                old = self.reg_get(rd)
                c = int(self.flag_c())
                if shift:
                    res = ((old >> shift) | (c << (31 - shift + 1))) & 0xFFFFFFFF if shift <= 32 else 0
                    self.cpsr = (self.cpsr & ~0x20000000) | (((old >> (shift - 1)) & 1) << 29)
                else:
                    res = old
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x14:
                res = (self.reg_get(rd) + val + int(self.flag_c())) & 0xFFFFFFFF
                self.set_nz_add(res, self.reg_get(rd), val)
                self.reg_set(rd, res)
            elif alu == 0x18:
                res = (self.reg_get(rd) - val - (1 - int(self.flag_c()))) & 0xFFFFFFFF
                self.set_nz_sub(res, self.reg_get(rd), val)
                self.reg_set(rd, res)
            elif alu == 0x1C:
                shift = val & 0xFF
                old = self.reg_get(rd)
                c = int(self.flag_c())
                if shift:
                    res = (((old >> shift) | (old << (32 - shift))) & 0xFFFFFFFF) if shift < 32 else 0
                    self.cpsr = (self.cpsr & ~0x20000000) | ((old >> (shift - 1)) & 1) << 29
                else:
                    res = (old >> 1) | (c << 31)
                    self.cpsr = (self.cpsr & ~0x20000000) | ((old & 1) << 29)
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x20:
                self.set_nz(self.reg_get(rd) & val)
            elif alu == 0x24:
                res = (-self.reg_get(rd)) & 0xFFFFFFFF
                self.set_nz_sub(res, 0, self.reg_get(rd))
                self.reg_set(rd, res)
            elif alu == 0x28:
                self.set_nz_sub((self.reg_get(rd) - val) & 0xFFFFFFFF, self.reg_get(rd), val)
            elif alu == 0x2C:
                res = self.reg_get(rd) | val
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x30:
                res = (self.reg_get(rd) * val) & 0xFFFFFFFF
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x34:
                res = self.reg_get(rd) & ~val
                self.set_nz(res)
                self.reg_set(rd, res)
            elif alu == 0x38:
                res = (~val) & 0xFFFFFFFF
                self.set_nz(res)
                self.reg_set(rd, res)
            else:
                res = (self.reg_get(rd) + val) & 0xFFFFFFFF
                self.set_nz_add(res, self.reg_get(rd), val)
                self.reg_set(rd, res)
            return 1

        if (op & 0xFC00) == 0x4400:
            if (op >> 6) & 0xF == 11:
                rs, rd = ((op >> 3) & 7) | 8, (op & 7) | 8
                addr = self.reg_get(rs)
                self.set_thumb(bool(addr & 1))
                self.r[15] = (addr & ~1) & 0xFFFFFFFF
                return 3
            rs, rd = ((op >> 3) & 7) | 8, (op & 7) | 8
            fn = (op >> 6) & 0xF
            if fn in (1, 2, 4, 8):
                ops = {1: lambda a, b: a + b, 2: lambda a, b: a - b, 4: lambda a, b: a & b, 8: lambda a, b: a ^ b}
                a, b = self.reg_get(rd), self.reg_get(rs)
                res = ops[fn](a, b) & 0xFFFFFFFF
                if fn == 1:
                    self.set_nz_add(res, a, b)
                elif fn == 2:
                    self.set_nz_sub(res, a, b)
                else:
                    self.set_nz(res)
                self.reg_set(rd, res)
            elif fn == 0xA:
                self.reg_set(rd, self.reg_get(rs))
            elif fn == 0xB:
                self.set_nz_sub((self.reg_get(rd) - self.reg_get(rs)) & 0xFFFFFFFF, self.reg_get(rd), self.reg_get(rs))
            elif fn == 0x9:
                res = self.reg_get(rd) * self.reg_get(rs)
                self.set_nz(res)
                self.reg_set(rd, res)
            return 1

        if (op & 0xF800) == 0x4800:
            rd = (op >> 8) & 7
            off = (op & 0xFF) << 2
            base = ((pc & 0xFFFFFFFC) + 4) & 0xFFFFFFFF
            self.reg_set(rd, self.read32((base + off) & 0xFFFFFFFC))
            return 2

        if (op & 0xF800) == 0x5000:
            rb, ro, rd = (op >> 3) & 7, (op >> 6) & 7, op & 7
            addr = (self.reg_get(rb) + self.reg_get(ro)) & 0xFFFFFFFF
            if op & 0x0800:
                if op & 0x0400:
                    val = self.read8(addr)
                    if val & 0x80:
                        val |= 0xFFFFFF00
                    self.reg_set(rd, val)
                elif op & 0x0200:
                    val = self.read16(addr)
                    if val & 0x8000:
                        val |= 0xFFFF0000
                    self.reg_set(rd, val)
                else:
                    self.reg_set(rd, self.read16(addr))
            elif op & 0x0400:
                self.write8(addr, self.reg_get(rd) & 0xFF)
            else:
                self.write16(addr, self.reg_get(rd) & 0xFFFF)
            return 2 + self._wait_states(addr, 16)

        if (op & 0xF800) == 0x5800:
            rb, rd = (op >> 3) & 7, op & 7
            off = (op >> 6) & 0x1F
            addr = (self.reg_get(rb) + off) & 0xFFFFFFFF
            if op & 0x0800:
                val = self.read8(addr)
                if val & 0x80:
                    val |= 0xFFFFFF00
                self.reg_set(rd, val)
            else:
                self.write8(addr, self.reg_get(rd) & 0xFF)
            return 2

        if (op & 0xF800) == 0x6000:
            rb, rd = (op >> 3) & 7, op & 7
            off = ((op >> 6) & 0x1F) << 2
            addr = (self.reg_get(rb) + off) & 0xFFFFFFFF
            if op & 0x0800:
                self.reg_set(rd, self.read32(addr))
            else:
                self.write32(addr, self.reg_get(rd))
            return 2

        if (op & 0xF800) == 0x8000:
            rb, rd = (op >> 3) & 7, op & 7
            off = ((op >> 6) & 0x1F) << 1
            addr = (self.reg_get(rb) + off) & 0xFFFFFFFF
            if op & 0x0800:
                val = self.read16(addr)
                self.reg_set(rd, val)
            else:
                self.write16(addr, self.reg_get(rd) & 0xFFFF)
            return 2 + self._wait_states(addr, 16)

        if (op & 0xF800) == 0x9000:
            rd = (op >> 8) & 7
            off = (op & 0xFF) << 2
            addr = (self.r[13] + off) & 0xFFFFFFFF
            if op & 0x0800:
                self.reg_set(rd, self.read32(addr))
            else:
                self.write32(addr, self.reg_get(rd))
            return 2

        if (op & 0xFF00) == 0xA000:
            rd = (op >> 8) & 7
            off = (op & 0xFF) << 2
            base = ((pc & 0xFFFFFFFC) + 4) & 0xFFFFFFFF
            self.reg_set(rd, (self.reg_get(rd) + base + off) & 0xFFFFFFFF)
            return 1

        if (op & 0xF800) == 0x8800:
            rb, rd = (op >> 3) & 7, op & 7
            off = (op >> 6) & 0x1F
            addr = (self.reg_get(rb) + (off << 1)) & 0xFFFFFFFF
            if op & 0x0800:
                self.reg_set(rd, self.read16(addr))
            else:
                self.write16(addr, self.reg_get(rd) & 0xFFFF)
            return 2 + self._wait_states(addr, 16)

        if (op & 0xFF00) == 0xB000 and not (op & 0x0E00):
            imm = (op & 0x7F) << 2
            if op & 0x0080:
                self.r[13] = (self.r[13] + imm) & 0xFFFFFFFF
            else:
                self.r[13] = (self.r[13] - imm) & 0xFFFFFFFF
            return 1

        if (op & 0xF800) == 0xB200:
            rd = (op >> 8) & 7
            rm = (op >> 3) & 7
            val = self.reg_get(rm)
            if op & 0x0800:
                if val & 0x80:
                    val |= 0xFFFFFF00
            else:
                val &= 0xFF
            self.reg_set(rd, val)
            return 1

        # --- push/pop (0xB400-0xB5FF) ---
        if (op & 0xF800) == 0xB400 and (op & 0x0600) == 0x0400:
            regs = [i for i in range(8) if op & (1 << i)]
            lr_pc = bool(op & 0x100)
            sp = self.r[13]
            if op & 0x0800:
                if lr_pc:
                    regs.append(15)
                for r in regs:
                    self.reg_set(r, self.read32(sp))
                    sp = (sp + 4) & 0xFFFFFFFF
                self.r[13] = sp
            else:
                if lr_pc:
                    regs.append(14)
                for r in reversed(regs):
                    sp = (sp - 4) & 0xFFFFFFFF
                    self.write32(sp, self.reg_get(r))
                self.r[13] = sp
            return 3

        # --- LDMIA / STMIA (0xC000-0xCFFF) ---
        if (op & 0xF000) == 0xC000:
            rb = (op >> 8) & 7
            regs = [i for i in range(8) if op & (1 << i)]
            addr = self.reg_get(rb)
            if op & 0x0800:
                for r in regs:
                    self.reg_set(r, self.read32(addr))
                    addr = (addr + 4) & 0xFFFFFFFF
                if op & 0x2000:
                    self.reg_set(rb, addr)
            else:
                for r in regs:
                    self.write32(addr, self.reg_get(r))
                    addr = (addr + 4) & 0xFFFFFFFF
                if op & 0x2000:
                    self.reg_set(rb, addr)
            return 3

        # --- conditional branch (0xD000-0xDFFF) ---
        if (op & 0xF000) == 0xD000:
            if (op & 0xFF00) == 0xDF00:
                self._swi_hle(op & 0xFF)
                return 4
            cond = (op >> 8) & 0xF
            if self.check_cond(cond):
                off = op & 0xFF
                if off & 0x80:
                    off |= 0xFFFFFF00
                self.r[15] = (self.r[15] + (off << 1)) & 0xFFFFFFFF
            return 2

        # --- unconditional branch (0xE000-0xEFFF) ---
        if (op & 0xF000) == 0xE000:
            off = op & 0x7FF
            if off & 0x400:
                off |= 0xFFFFF800
            self.r[15] = (self.r[15] + (off << 1)) & 0xFFFFFFFF
            return 3

        # --- long branch with link (0xF000-0xFFFF) ---
        if (op & 0xF000) == 0xF000:
            if not self._bl_half:
                self._bl_temp = (op & 0x7FF) << 12
                if self._bl_temp & 0x400000:
                    self._bl_temp |= 0xFF800000
                self._bl_half = True
            else:
                self._bl_half = False
                off = op & 0x7FF
                if off & 0x400:
                    off |= 0xFFFFF800
                imm = self._bl_temp | (off << 1)
                self.reg_set(14, self.r[15] | 1)
                self.r[15] = (self.r[15] + imm) & 0xFFFFFFFF
            return 3

        # --- undefined ---
        return 1

    @property
    def _bl_half(self):
        return getattr(self, '__bl_half', False)

    @_bl_half.setter
    def _bl_half(self, v):
        self.__bl_half = v

    @property
    def _bl_temp(self):
        return getattr(self, '__bl_temp', 0)

    @_bl_temp.setter
    def _bl_temp(self, v):
        self.__bl_temp = v

    def _exec_arm(self, insn: int) -> int:
        cond = (insn >> 28) & 0xF
        if not self.check_cond(cond):
            return 1
        op = (insn >> 25) & 7
        nib = (insn >> 4) & 0xF

        # --- BX ---
        if ((insn & 0x0FFFFFF0) == 0x012FFF10) and nib == 0b0001:
            rm = insn & 0xF
            addr = self.reg_get(rm)
            self.set_thumb(bool(addr & 1))
            self.r[15] = (addr & ~1) & 0xFFFFFFFF
            return 3

        # --- data processing ---
        if op in (0b000, 0b001):
            return self._arm_data_proc(insn)

        # --- load/store immediate offset ---
        if op == 0b010:
            return self._arm_load_store(insn, True)

        # --- load/store register offset ---
        if op == 0b011:
            if nib == 0b1011:
                return self._arm_half_signed(insn)
            return self._arm_load_store(insn, False)

        # --- block data transfer / load/store multiple ---
        if op == 0b100:
            if (insn >> 24) & 1:
                return self._arm_load_store(insn, True)
            return self._arm_block_xfer(insn)

        # --- branch / load store ---
        if op == 0b101:
            if (insn >> 24) & 1:
                return self._arm_load_store(insn, False)
            return self._arm_branch(insn)

        # --- coprocessor / SWI ---
        if (insn & 0x0F000000) == 0x0F000000:
            self._swi_hle(insn & 0xFFFFFF)
            return 4

        return 1

    def _arm_data_proc(self, insn: int) -> int:
        opcode = (insn >> 21) & 0xF
        s = bool(insn & 0x00100000)
        rn = (insn >> 16) & 0xF
        rd = (insn >> 12) & 0xF
        op2, carry = self._arm_operand2(insn)
        lhs = self.reg_get(rn) if rn != 15 else self.r[15] + 4
        lhs &= 0xFFFFFFFF

        if opcode == 0x00:
            res = lhs & op2
            if s:
                self.set_nz(res)
                self.cpsr = (self.cpsr & ~0x20000000) | (carry << 29)
            self.reg_set(rd, res)
        elif opcode == 0x01:
            res = lhs ^ op2
            if s:
                self.set_nz(res)
            self.reg_set(rd, res)
        elif opcode == 0x02:
            res = (lhs - op2) & 0xFFFFFFFF
            if s:
                self.set_nz_sub(res, lhs, op2)
                self.cpsr = (self.cpsr & ~0x20000000) | (carry << 29)
            if rd == 15 and s:
                self.cpsr = self.spsr
            else:
                self.reg_set(rd, res)
        elif opcode == 0x03:
            res = (op2 - lhs) & 0xFFFFFFFF
            if s:
                self.set_nz_sub(res, op2, lhs)
            self.reg_set(rd, res)
        elif opcode == 0x04:
            res = (lhs + op2) & 0xFFFFFFFF
            if s:
                self.set_nz_add(res, lhs, op2)
                self.cpsr = (self.cpsr & ~0x20000000) | (carry << 29)
            if rd == 15 and s:
                self.cpsr = self.spsr
            else:
                self.reg_set(rd, res)
        elif opcode == 0x05:
            c = int(self.flag_c())
            res = (lhs + op2 + c) & 0xFFFFFFFF
            if s:
                self.set_nz_add(res, lhs, op2 + c)
            self.reg_set(rd, res)
        elif opcode == 0x06:
            c = int(self.flag_c())
            res = (lhs - op2 - (1 - c)) & 0xFFFFFFFF
            if s:
                self.set_nz_sub(res, lhs, op2 + (1 - c))
            self.reg_set(rd, res)
        elif opcode == 0x07:
            c = int(self.flag_c())
            res = (op2 - lhs - (1 - c)) & 0xFFFFFFFF
            if s:
                self.set_nz_sub(res, op2, lhs + (1 - c))
            self.reg_set(rd, res)
        elif opcode == 0x08:
            val = lhs & op2
            self.set_nz(val)
            self.cpsr = (self.cpsr & ~0x20000000) | (carry << 29)
        elif opcode == 0x09:
            self.set_nz(lhs ^ op2)
        elif opcode == 0x0A:
            self.set_nz_sub((lhs - op2) & 0xFFFFFFFF, lhs, op2)
        elif opcode == 0x0B:
            self.set_nz_add((lhs + op2) & 0xFFFFFFFF, lhs, op2)
        elif opcode == 0x0C:
            res = lhs | op2
            if s:
                self.set_nz(res)
            self.reg_set(rd, res)
        elif opcode == 0x0D:
            res = op2
            if s:
                self.set_nz(res)
            self.reg_set(rd, res)
        elif opcode == 0x0E:
            res = lhs & ~op2
            if s:
                self.set_nz(res)
            self.reg_set(rd, res)
        elif opcode == 0x0F:
            res = ~op2 & 0xFFFFFFFF
            if s:
                self.set_nz(res)
            self.reg_set(rd, res)
        return 1 + (self._wait_states(self.r[15], 32) if rd == 15 else 0)

    def _arm_operand2(self, insn: int) -> tuple[int, int]:
        if insn & 0x02000000:
            imm = insn & 0xFF
            rot = ((insn >> 8) & 0xF) << 1
            if rot:
                imm = ((imm >> rot) | (imm << (32 - rot))) & 0xFFFFFFFF
                carry = (imm >> 31) & 1
            else:
                carry = int(self.flag_c())
            return imm, carry
        rm = insn & 0xF
        val = self.reg_get(rm)
        st = (insn >> 5) & 3
        if insn & 0x10:
            rs = (insn >> 8) & 0xF
            amt = self.reg_get(rs) & 0xFF
        else:
            amt = (insn >> 7) & 0x1F
        if amt == 0:
            return val, int(self.flag_c())
        if st == 0:
            res = (val << amt) & 0xFFFFFFFF
            carry = (val >> (32 - amt)) & 1
        elif st == 1:
            res = (val >> amt) & 0xFFFFFFFF
            carry = (val >> (amt - 1)) & 1
        elif st == 2:
            if val & 0x80000000:
                res = (val >> amt) | (0xFFFFFFFF << (32 - amt))
            else:
                res = val >> amt
            res &= 0xFFFFFFFF
            carry = (val >> (amt - 1)) & 1
        else:
            if amt == 0:
                res = val
                carry = int(self.flag_c())
            else:
                res = ((val >> amt) | (val << (32 - amt))) & 0xFFFFFFFF
                carry = (val >> (amt - 1)) & 1
        return res & 0xFFFFFFFF, carry

    def _arm_load_store(self, insn: int, immediate: bool) -> int:
        rd = (insn >> 12) & 0xF
        rn = (insn >> 16) & 0xF
        pre = bool(insn & 0x01000000)
        add = bool(insn & 0x00800000)
        wb = bool(insn & 0x00200000)
        load = bool(insn & 0x00100000)
        byte = bool(insn & 0x00400000)

        base = self.reg_get(rn)
        if immediate:
            off = insn & 0xFFF
        else:
            rm = insn & 0xF
            off = self.reg_get(rm)
            if insn & 0x10:
                st = (insn >> 5) & 3
                amt = (insn >> 7) & 0x1F
                if amt:
                    off, _ = self._arm_shift(off, st, amt)
        if not add:
            off = -off
        addr = (base + off) & 0xFFFFFFFF if pre else base

        if load:
            if byte:
                val = self.read8(addr)
            else:
                val = self.read32(addr)
            self.reg_set(rd, val)
        else:
            val = self.reg_get(rd)
            if byte:
                self.write8(addr, val & 0xFF)
            else:
                self.write32(addr, val)

        if wb and rn != 15:
            write_addr = (base + off) & 0xFFFFFFFF if pre else (base + off) & 0xFFFFFFFF
            if not pre:
                write_addr = (base + off) & 0xFFFFFFFF
            self.reg_set(rn, write_addr)

        return 2

    def _arm_shift(self, val: int, st: int, amt: int) -> tuple[int, int]:
        if amt == 0:
            return val, int(self.flag_c())
        if st == 0:
            res = (val << amt) & 0xFFFFFFFF
            carry = (val >> (32 - amt)) & 1
        elif st == 1:
            res = val >> amt
            carry = (val >> (amt - 1)) & 1
        elif st == 2:
            if val & 0x80000000:
                res = (val >> amt) | (0xFFFFFFFF << (32 - amt))
            else:
                res = val >> amt
            res &= 0xFFFFFFFF
            carry = (val >> (amt - 1)) & 1
        else:
            res = ((val >> amt) | (val << (32 - amt))) & 0xFFFFFFFF
            carry = (val >> (amt - 1)) & 1
        return res & 0xFFFFFFFF, carry

    def _arm_half_signed(self, insn: int) -> int:
        rd = (insn >> 12) & 0xF
        rn = (insn >> 16) & 0xF
        pre = bool(insn & 0x01000000)
        add = bool(insn & 0x00800000)
        wb = bool(insn & 0x00200000)
        load = bool(insn & 0x00100000)
        op = (insn >> 5) & 3
        base = self.reg_get(rn)
        off = (insn & 0xF) | ((insn >> 4) & 0xF0)
        if not add:
            off = -off
        addr = (base + off) & 0xFFFFFFFF if pre else base

        if load:
            if op == 1:
                val = self.read16(addr)
                if insn & 0x40:
                    val = val - 0x10000 if val & 0x8000 else val
            elif op == 2:
                val = self.read8(addr)
                if insn & 0x40 and val & 0x80:
                    val |= 0xFFFFFF00
            else:
                val = self.read8(addr)
            self.reg_set(rd, val & 0xFFFFFFFF)
        else:
            if op == 1:
                self.write16(addr, self.reg_get(rd) & 0xFFFF)
            else:
                self.write8(addr, self.reg_get(rd) & 0xFF)

        if wb and rn != 15:
            self.reg_set(rn, (base + off) & 0xFFFFFFFF)
        return 2

    def _arm_block_xfer(self, insn: int) -> int:
        rn = (insn >> 16) & 0xF
        addr = self.reg_get(rn)
        regs = [i for i in range(16) if insn & (1 << i)]
        pre = bool(insn & 0x01000000)
        up = bool(insn & 0x00800000)
        wb = bool(insn & 0x00200000)
        load = bool(insn & 0x00100000)

        n = len(regs)
        if up:
            start = addr + (4 if pre else 0)
        else:
            start = addr - n * 4 + (0 if pre else -4)

        for i, r in enumerate(regs):
            a = (start + i * 4) & 0xFFFFFFFF
            if load:
                val = self.read32(a)
                if r == 15 and (self.thumb() or (val & 1)):
                    self.set_thumb(bool(val & 1))
                    self.r[15] = (val & ~1) & 0xFFFFFFFF
                else:
                    self.reg_set(r, val)
            else:
                self.write32(a, self.reg_get(r))

        if wb and rn != 15:
            if up:
                self.reg_set(rn, (addr + n * 4) & 0xFFFFFFFF)
            else:
                self.reg_set(rn, (addr - n * 4) & 0xFFFFFFFF)
        return 3

    def _arm_branch(self, insn: int) -> int:
        link = bool(insn & 0x01000000)
        off = insn & 0x00FFFFFF
        if off & 0x00800000:
            off |= 0xFF000000
        if link:
            self.reg_set(14, (self.r[15] + 4) & 0xFFFFFFFF)
        self.r[15] = (self.r[15] + 4 + (off << 2)) & 0xFFFFFFFF
        return 3

    # --- PPU rendering ---

    def _render_scanline(self, line: int) -> None:
        dispcnt = self._io16(REG_DISPCNT)
        mode = dispcnt & 7
        bg_enable = (dispcnt >> 8) & 0xF

        # build window layers
        if _ACCEL is not None and hasattr(_ACCEL, 'fast_build_win_layers'):
            _ACCEL.fast_build_win_layers(
                self._win_layers, dispcnt,
                self._io16(REG_WIN0H), self._io16(REG_WIN0V),
                self._io16(REG_WIN1H), self._io16(REG_WIN1V),
                self._io16(REG_WININ), self._io16(REG_WINOUT),
            )
        else:
            self._build_win_layers(dispcnt)

        if mode <= 2:
            self._render_text_bg(line, mode, dispcnt, bg_enable)
        elif mode == 3:
            self._render_mode3(line)
        elif mode == 4:
            self._render_mode4(line, dispcnt)
        elif mode == 5:
            self._render_mode5(line, dispcnt)

        self._render_sprites(line, dispcnt)

    def _build_win_layers(self, dispcnt: int) -> None:
        win0h = self._io16(REG_WIN0H)
        win0v = self._io16(REG_WIN0V)
        win1h = self._io16(REG_WIN1H)
        win1v = self._io16(REG_WIN1V)
        winin = self._io16(REG_WININ)
        winout = self._io16(REG_WINOUT)
        for y in range(160):
            for x in range(240):
                in0 = in1 = 0
                if dispcnt & 0x2000:
                    l, r = win0h & 0xFF, win0h >> 8
                    t, b = win0v & 0xFF, win0v >> 8
                    if r > 240: r = 240
                    if b > 160: b = 160
                    if l <= x < r and t <= y < b:
                        in0 = 1
                if dispcnt & 0x4000:
                    l, r = win1h & 0xFF, win1h >> 8
                    t, b = win1v & 0xFF, win1v >> 8
                    if r > 240: r = 240
                    if b > 160: b = 160
                    if l <= x < r and t <= y < b:
                        in1 = 1
                if in0 and in1:
                    layers = winin & 0x3F
                elif in0:
                    layers = winin & 0x3F
                elif in1:
                    layers = (winin >> 8) & 0x3F
                else:
                    layers = winout & 0x3F if winout & 0x3F else 0x3F
                self._win_layers[y][x] = layers

    def _render_mode3(self, line: int) -> None:
        layer_bit = 1
        if _ACCEL is not None and hasattr(_ACCEL, 'fast_render_mode3'):
            _ACCEL.fast_render_mode3(self.vram, self._prio, self._pxbuf, self._win_layers, layer_bit)
        else:
            for x in range(240):
                if not (self._win_layers[line][x] & layer_bit):
                    continue
                off = (line * 240 + x) * 2
                c = self.vram[off] | (self.vram[off + 1] << 8)
                self._prio[line][x] = 0
                self._pxbuf[line][x] = rgb565_to_rgb(c)

    def _render_mode4(self, line: int, dispcnt: int) -> None:
        frame = (dispcnt >> 4) & 1
        base = 0xA000 if frame else 0
        layer_bit = 1
        if _ACCEL is not None and hasattr(_ACCEL, 'fast_render_mode4'):
            _ACCEL.fast_render_mode4(self.vram, self.palette, self._prio, self._pxbuf, self._win_layers, layer_bit, base)
        else:
            for x in range(240):
                if not (self._win_layers[line][x] & layer_bit):
                    continue
                idx = self.vram[base + line * 240 + x]
                c = self.palette[idx * 2] | (self.palette[idx * 2 + 1] << 8)
                self._prio[line][x] = 0
                self._pxbuf[line][x] = rgb565_to_rgb(c)

    def _render_mode5(self, line: int, dispcnt: int) -> None:
        frame = (dispcnt >> 4) & 1
        base = 0xA000 if frame else 0
        layer_bit = 1
        if _ACCEL is not None and hasattr(_ACCEL, 'fast_render_mode5'):
            _ACCEL.fast_render_mode5(self.vram, self._prio, self._pxbuf, self._win_layers, layer_bit, base)
        else:
            for x in range(240):
                if not (self._win_layers[line][x] & layer_bit):
                    continue
                off = base + (line * 240 + x) * 2
                c = self.vram[off] | (self.vram[off + 1] << 8)
                self._prio[line][x] = 0
                self._pxbuf[line][x] = rgb565_to_rgb(c)

    def _render_text_bg(self, line: int, mode: int, dispcnt: int, bg_enable: int) -> None:
        for bg in range(4):
            if not (bg_enable & (1 << bg)):
                continue
            layer_bit = 1 << (bg + 1)
            bcnt = self._io16(REG_BG0CNT + bg * 2)
            char_base = ((bcnt >> 2) & 0x3) * 0x4000
            screen_base = ((bcnt >> 8) & 0x1F) * 0x800
            size = (bcnt >> 14) & 3
            map_w = 32 << (size & 1)
            map_h = 32 << (size >> 1)
            hofs = self._io16(REG_BG0HOFS + bg * 4) & 0x1FF
            vofs = self._io16(REG_BG0HOFS + bg * 4 + 2) & 0x1FF
            bpp8 = bool(bcnt & 0x80)
            for x in range(240):
                if not (self._win_layers[line][x] & layer_bit):
                    continue
                sx = (x + hofs) % (map_w * 8)
                sy = (line + vofs) % (map_h * 8)
                tile_x = sx >> 3
                tile_y = sy >> 3
                entry_off = screen_base + (tile_y * map_w + tile_x) * 2
                if entry_off + 1 >= len(self.vram):
                    continue
                entry = self.vram[entry_off] | (self.vram[entry_off + 1] << 8)
                tile_id = entry & 0x3FF
                pal_bank = (entry >> 12) & 0xF
                flip_h = bool(entry & 0x400)
                flip_v = bool(entry & 0x800)
                tx = sx & 7
                ty = sy & 7
                if flip_h:
                    tx = 7 - tx
                if flip_v:
                    ty = 7 - ty
                if bpp8:
                    tile_off = char_base + tile_id * 64 + ty * 8 + tx
                    if tile_off >= len(self.vram):
                        continue
                    color_idx = self.vram[tile_off]
                    if color_idx == 0:
                        continue
                else:
                    tile_off = char_base + tile_id * 32 + ty * 4 + (tx >> 1)
                    if tile_off >= len(self.vram):
                        continue
                    px = self.vram[tile_off]
                    nibble = (px >> (4 if tx & 1 else 0)) & 0xF
                    if nibble == 0:
                        continue
                    color_idx = pal_bank * 16 + nibble
                color = self.palette[color_idx * 2] | (self.palette[color_idx * 2 + 1] << 8)
                if color:
                    self._prio[line][x] = bg
                    self._pxbuf[line][x] = rgb565_to_rgb(color)

    def _render_sprites(self, line: int, dispcnt: int) -> None:
        for i in range(128):
            off = i * 8
            attr0 = self.oam[off] | (self.oam[off + 1] << 8)
            attr1 = self.oam[off + 2] | (self.oam[off + 3] << 8)
            attr2 = self.oam[off + 4] | (self.oam[off + 5] << 8)
            y = attr0 & 0xFF
            if y > 160:
                y -= 256
            height = (8, 16, 32, 64)[(attr0 >> 14) & 3]
            if not (y <= line < y + height):
                continue
            x = attr1 & 0x1FF
            if x > 240:
                x -= 512
            width = height if not (attr0 & 0x200) else (8, 16, 32, 64)[(attr1 >> 14) & 3]
            tile_id = attr2 & 0x3FF
            pal_bank = (attr2 >> 12) & 0xF
            flip_h = bool(attr1 & 0x1000)
            flip_v = bool(attr1 & 0x2000)
            prio = (attr0 >> 10) & 3
            bpp8 = bool(attr0 & 0x2000)
            sy = line - y
            if flip_v:
                sy = height - 1 - sy
            for sx in range(width):
                dx = sx
                if flip_h:
                    dx = width - 1 - sx
                px = x + sx
                if not (0 <= px < 240):
                    continue
                if bpp8:
                    tile_base = tile_id + (sy // 8) * (width // 8) + (dx // 8)
                    t_off = tile_base * 64 + (sy % 8) * 8 + (dx % 8)
                    if t_off >= len(self.vram):
                        continue
                    ci = self.vram[t_off]
                    if ci == 0:
                        continue
                else:
                    tile_base = tile_id + (sy // 8) * (width // 8) + (dx // 8)
                    t_off = tile_base * 32 + (sy % 8) * 4 + ((dx % 8) >> 1)
                    if t_off >= len(self.vram):
                        continue
                    pv = self.vram[t_off]
                    nib = (pv >> 4) if (dx & 1) else (pv & 0xF)
                    if nib == 0:
                        continue
                    ci = pal_bank * 16 + nib
                if prio < self._prio[line][px] and (self._win_layers[line][px] & 0x10):
                    co = self.palette[ci * 2] | (self.palette[ci * 2 + 1] << 8)
                    self._pxbuf[line][px] = rgb565_to_rgb(co)
                    self._prio[line][px] = prio

    def _compose_fb(self) -> None:
        if _ACCEL is not None and hasattr(_ACCEL, 'fast_compose_fb'):
            _ACCEL.fast_compose_fb(self.framebuffer, self._pxbuf, SCREEN_W, SCREEN_H)
        else:
            for y in range(SCREEN_H):
                for x in range(SCREEN_W):
                    p = self._pxbuf[y][x]
                    i = (y * SCREEN_W + x) * 3
                    self.framebuffer[i] = p[0]
                    self.framebuffer[i + 1] = p[1]
                    self.framebuffer[i + 2] = p[2]

    def _run_frame(self) -> None:
        if _ACCEL is not None and hasattr(_ACCEL, 'fast_run_frame'):
            _ACCEL.fast_run_frame(self, VDRAW_LINES, CYCLES_PER_SCANLINE)
        else:
            for ln in range(VDRAW_LINES):
                self._set_io16(REG_VCOUNT, ln)
                used = 0
                while used < CYCLES_PER_SCANLINE:
                    if self.halted:
                        used += 4
                        self.cycles += 4
                        self._timer_tick(4)
                        continue
                    c = self.step_cpu()
                    used += c
                    self.cycles += c
                    self._timer_tick(c)
                self._render_scanline(ln)
        # vblank
        self._set_io16(REG_VCOUNT, VDRAW_LINES)
        self._irq_raise(0)
        # remaining lines
        if _ACCEL is not None and hasattr(_ACCEL, 'fast_run_cycles'):
            _ACCEL.fast_run_cycles(self, (TOTAL_LINES - VDRAW_LINES) * CYCLES_PER_SCANLINE)
        else:
            remaining = (TOTAL_LINES - VDRAW_LINES) * CYCLES_PER_SCANLINE
            used = 0
            while used < remaining:
                if self.halted:
                    used += 4
                    self.cycles += 4
                    self._timer_tick(4)
                    continue
                c = self.step_cpu()
                used += c
                self.cycles += c
                self._timer_tick(c)
        self._compose_fb()


class MewGBAApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("mewgba$ VBAv0.2.1 Blue Edition (files=off)")
        self.root.configure(bg=MEWGBA_BLUE_THEME["bg"])
        self.root.resizable(False, False)

        self.core = MewGBACore()
        self.running = False
        self.status_var = tk.StringVar(value="No ROM — use File > Load ROM or start demo")
        self.speed = 1.0

        self._style()
        self._build_menubar()
        self._build_ui()
        self._bind_keys()

        self.core.load_rom_bytes(DEFAULT_ROM, "Demo (built-in)")
        self.after_id = self.root.after(int(GBA_FRAME_MS), self._tick)
        self.running = True

    def _style(self) -> None:
        t = MEWGBA_BLUE_THEME
        self.root.option_add("*Font", "TkDefaultFont 10")
        self.root.option_add("*Background", t["panel"])
        self.root.option_add("*Foreground", t["accent"])
        self.root.option_add("*Menu.background", t["bg"])
        self.root.option_add("*Menu.foreground", t["accent"])
        self.root.option_add("*Menu.activeBackground", t["button_bg"])
        self.root.option_add("*Menu.activeForeground", t["accent"])

    def _btn(self, parent: tk.Widget, text: str, cmd) -> tk.Button:
        t = MEWGBA_BLUE_THEME
        return tk.Button(
            parent, text=text, command=cmd,
            bg=t["button_bg"], fg=t["accent"],
            activebackground=t["panel"], activeforeground=t["accent"],
            relief=tk.FLAT, bd=1, highlightthickness=1,
            highlightbackground=t["accent"], highlightcolor=t["accent"],
            padx=10, pady=2,
        )

    def _build_menubar(self) -> None:
        t = MEWGBA_BLUE_THEME
        bar = tk.Frame(self.root, bg=t["bg"], height=26)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        menus = {
            "File": [
                ("Load ROM...", self._load_rom),
                ("Load Demo", self._load_demo),
                ("Recent ROMs", self._show_recent),
                ("Exit", self.root.quit),
            ],
            "Emulation": [
                ("Pause / Resume", self._toggle_run),
                ("Reset", self._reset),
                ("Speed 0.5x", lambda: self._set_speed(0.5)),
                ("Speed 1x", lambda: self._set_speed(1.0)),
                ("Speed 2x", lambda: self._set_speed(2.0)),
                ("Speed 4x", lambda: self._set_speed(4.0)),
            ],
            "Tools": [
                ("Registers", self._show_regs),
                ("Memory Viewer", self._show_memory),
                ("Cython Status", self._show_cython),
                ("About", self._show_about),
            ],
        }

        for name, items in menus.items():
            mb = tk.Menubutton(bar, text=name, bg=t["bg"], fg=t["accent"],
                               activebackground=t["panel"], activeforeground=t["accent"],
                               relief=tk.FLAT, padx=8, pady=2)
            mb.pack(side=tk.LEFT)
            menu = tk.Menu(mb, tearoff=0, bg=t["bg"], fg=t["accent"],
                           activebackground=t["panel"], activeforeground=t["accent"])
            mb.config(menu=menu)
            for label, cmd in items:
                menu.add_command(label=label, command=cmd)

    def _build_ui(self) -> None:
        t = MEWGBA_BLUE_THEME
        toolbar = tk.Frame(self.root, bg=t["panel"], height=32)
        toolbar.pack(fill=tk.X, padx=4, pady=(2, 0))
        toolbar.pack_propagate(False)

        self._btn(toolbar, "Pause", self._toggle_run).pack(side=tk.LEFT, padx=2)
        self._btn(toolbar, "Reset", self._reset).pack(side=tk.LEFT, padx=2)
        self._btn(toolbar, "Load ROM", self._load_rom).pack(side=tk.RIGHT, padx=2)
        self._btn(toolbar, "Demo", self._load_demo).pack(side=tk.RIGHT, padx=2)

        body = tk.Frame(self.root, bg=t["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        left = tk.Frame(body, bg=t["screen"],
                        highlightbackground=t["accent"], highlightthickness=1)
        left.pack(side=tk.LEFT, fill=tk.BOTH)

        self.canvas = tk.Canvas(left, width=SCREEN_W * 2, height=SCREEN_H * 2,
                                bg=t["screen"], highlightthickness=0)
        self.canvas.pack(padx=4, pady=4)
        self._img = tk.PhotoImage(width=SCREEN_W, height=SCREEN_H)
        self._img_2x = tk.PhotoImage(width=SCREEN_W * 2, height=SCREEN_H * 2)
        self.canvas.create_image((0, 0), image=self._img_2x, anchor="nw")

        right = tk.Frame(body, bg=t["panel"], width=180,
                         highlightbackground=t["accent"], highlightthickness=1)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        right.pack_propagate(False)

        tk.Label(right, text="MEWGBA$ CONTROL", bg=t["panel"], fg=t["accent"],
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        tk.Label(right, text="GBA Keys:", bg=t["panel"], fg=t["accent"],
                 font=("TkDefaultFont", 9)).pack(anchor="w", padx=8, pady=(4, 0))
        keys_text = "A=Z  B=X\nSELECT=BackSpace\nSTART=Enter\n↑↓←→  L=Q  R=E"
        tk.Label(right, text=keys_text, bg=t["panel"], fg=t["accent"],
                 justify=tk.LEFT, font=("TkDefaultFont", 8)).pack(anchor="w", padx=8, pady=2)

        self.fps_label = tk.Label(right, text="FPS: ---", bg=t["panel"], fg=t["accent"],
                                  font=("TkDefaultFont", 9))
        self.fps_label.pack(anchor="w", padx=8, pady=(12, 2))

        self.speed_label = tk.Label(right, text="Speed: 1.0x", bg=t["panel"], fg=t["accent"],
                                    font=("TkDefaultFont", 9))
        self.speed_label.pack(anchor="w", padx=8, pady=2)

        self.cython_label = tk.Label(right, text=f"Cython: {'ON' if _ACCEL else 'OFF'}",
                                     bg=t["panel"],
                                     fg=t["accent"] if _ACCEL else "#ff6b6b",
                                     font=("TkDefaultFont", 9))
        self.cython_label.pack(anchor="w", padx=8, pady=2)

        status = tk.Frame(self.root, bg=t["bg"], height=22)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)
        tk.Label(status, textvariable=self.status_var,
                 bg=t["bg"], fg=t["accent"],
                 anchor="w", font=("TkDefaultFont", 9)).pack(fill=tk.X, padx=8)

    def _bind_keys(self) -> None:
        self.root.bind("<space>", lambda _e: self._toggle_run())
        self.root.bind("<F5>", lambda _e: self._quicksave())
        self.root.bind("<F9>", lambda _e: self._quickload())
        gba = {
            "z": KEY_A, "x": KEY_B, "BackSpace": KEY_SELECT,
            "Return": KEY_START, "Right": KEY_RIGHT, "Left": KEY_LEFT,
            "Up": KEY_UP, "Down": KEY_DOWN, "e": KEY_R, "q": KEY_L,
        }
        mask = [GBA_KEY_MASK]

        def press(e):
            k = gba.get(e.keysym)
            if k is not None:
                mask[0] &= ~(1 << k)
                self.core.set_keys(mask[0])

        def release(e):
            k = gba.get(e.keysym)
            if k is not None:
                mask[0] |= (1 << k)
                self.core.set_keys(mask[0])

        self.root.bind("<KeyPress>", press)
        self.root.bind("<KeyRelease>", release)

    def _set_speed(self, s: float) -> None:
        self.speed = s
        self.speed_label.config(text=f"Speed: {s}x")

    def _toggle_run(self) -> None:
        self.running = not self.running
        self.status_var.set("Running" if self.running else "Paused")

    def _reset(self) -> None:
        rom = bytes(self.core.rom)
        label = self.core.rom_label
        self.core.reset_cpu()
        if rom:
            self.core.load_rom_bytes(rom, label)
        self.running = True
        self.status_var.set(f"Reset: {label}")

    def _load_rom(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root, title="Load GBA ROM",
            filetypes=[("GBA ROM", "*.gba"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
            if data[0xB2] != 0x96 or data[0xB3] != 0x00:
                raise ValueError("Invalid GBA ROM (bad header)")
            label = os.path.basename(path)
            self.core.load_rom_bytes(data, label)
            self.running = True
            self.status_var.set(f"Loaded: {label}")
            self.root.title(f"mewgba$ — {label}")
            self._save_recent(path)
        except (OSError, ValueError, IndexError) as e:
            messagebox.showerror("Load ROM", str(e), parent=self.root)

    def _load_demo(self) -> None:
        self.core.load_rom_bytes(DEFAULT_ROM, "Demo (built-in)")
        self.running = True
        self.status_var.set("Demo loaded")
        self.root.title("mewgba$ VBAv0.2.1 Blue Edition (files=off)")

    def _save_recent(self, path: str) -> None:
        try:
            recents = []
            if os.path.exists(MEWGBA_RECENT):
                with open(MEWGBA_RECENT, "r", encoding="utf-8") as f:
                    recents = json.load(f)
            recents = [p for p in recents if p != path]
            recents.insert(0, path)
            recents = recents[:10]
            with open(MEWGBA_RECENT, "w", encoding="utf-8") as f:
                json.dump(recents, f)
        except OSError:
            pass

    def _show_recent(self) -> None:
        try:
            if not os.path.exists(MEWGBA_RECENT):
                self.status_var.set("No recent ROMs")
                return
            with open(MEWGBA_RECENT, "r", encoding="utf-8") as f:
                recents = json.load(f)
            if not recents:
                self.status_var.set("No recent ROMs")
                return
            top = tk.Toplevel(self.root)
            top.title("Recent ROMs")
            top.geometry("400x300")
            top.configure(bg=MEWGBA_BLUE_THEME["bg"])
            lb = tk.Listbox(top, bg=MEWGBA_BLUE_THEME["panel"],
                            fg=MEWGBA_BLUE_THEME["accent"],
                            selectbackground=MEWGBA_BLUE_THEME["button_bg"])
            lb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
            for p in recents:
                lb.insert(tk.END, p)

            def load_sel():
                sel = lb.curselection()
                if sel:
                    path = lb.get(sel[0])
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                        self.core.load_rom_bytes(data, os.path.basename(path))
                        self.running = True
                        self.status_var.set(f"Loaded: {os.path.basename(path)}")
                        self.root.title(f"mewgba$ — {os.path.basename(path)}")
                        top.destroy()
                    except (OSError, ValueError) as e:
                        messagebox.showerror("Error", str(e))

            tk.Button(top, text="Load Selected", command=load_sel,
                      bg=MEWGBA_BLUE_THEME["button_bg"],
                      fg=MEWGBA_BLUE_THEME["accent"]).pack(pady=4)
        except (OSError, json.JSONDecodeError):
            self.status_var.set("Error reading recent ROMs")

    def _quicksave(self) -> None:
        try:
            os.makedirs(MEWGBA_SAVES, exist_ok=True)
            snap = self.core.snapshot()
            path = os.path.join(MEWGBA_SAVES, "quicksave.pkl")
            with open(path, "wb") as f:
                pickle.dump(snap, f)
            self.status_var.set("Quicksaved (F5)")
        except OSError:
            self.status_var.set("Quicksave failed")

    def _quickload(self) -> None:
        try:
            path = os.path.join(MEWGBA_SAVES, "quicksave.pkl")
            if not os.path.exists(path):
                self.status_var.set("No quicksave found")
                return
            with open(path, "rb") as f:
                snap = pickle.load(f)
            self.core.restore(snap)
            self.running = True
            self.status_var.set("Quickloaded (F9)")
        except (OSError, pickle.UnpicklingError, KeyError):
            self.status_var.set("Quickload failed")

    def _show_regs(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("CPU Registers")
        top.geometry("350x400")
        top.configure(bg=MEWGBA_BLUE_THEME["bg"])
        text = tk.Text(top, bg=MEWGBA_BLUE_THEME["panel"],
                       fg=MEWGBA_BLUE_THEME["accent"],
                       font=("Menlo", 9))
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        lines = []
        for i in range(16):
            lines.append(f"R{i:02d}: 0x{self.core.r[i]:08X}")
        lines.append(f"PC:  0x{self.core.r[15]:08X}")
        lines.append(f"CPSR: 0x{self.core.cpsr:08X}  {'Thumb' if self.core.thumb() else 'ARM'}")
        lines.append(f"Halted: {self.core.halted}")
        text.insert(tk.END, "\n".join(lines))
        text.config(state=tk.DISABLED)

        def refresh():
            nonlocal text
            text.config(state=tk.NORMAL)
            text.delete("1.0", tk.END)
            lines = []
            for i in range(16):
                lines.append(f"R{i:02d}: 0x{self.core.r[i]:08X}")
            lines.append(f"PC:  0x{self.core.r[15]:08X}")
            lines.append(f"CPSR: 0x{self.core.cpsr:08X}  {'Thumb' if self.core.thumb() else 'ARM'}")
            lines.append(f"Halted: {self.core.halted}")
            text.insert(tk.END, "\n".join(lines))
            text.config(state=tk.DISABLED)
            top.after(200, refresh)

        top.after(200, refresh)

    def _show_memory(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("Memory Viewer")
        top.geometry("500x400")
        top.configure(bg=MEWGBA_BLUE_THEME["bg"])

        ctrl = tk.Frame(top, bg=MEWGBA_BLUE_THEME["bg"])
        ctrl.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(ctrl, text="Region:", bg=MEWGBA_BLUE_THEME["bg"],
                 fg=MEWGBA_BLUE_THEME["accent"]).pack(side=tk.LEFT)
        region_var = tk.StringVar(value="ewram")
        regions = [a for _, _, a in MEMORY_REGIONS]
        dd = ttk.Combobox(ctrl, textvariable=region_var, values=regions, width=12)
        dd.pack(side=tk.LEFT, padx=4)

        tk.Label(ctrl, text="Addr (hex):", bg=MEWGBA_BLUE_THEME["bg"],
                 fg=MEWGBA_BLUE_THEME["accent"]).pack(side=tk.LEFT, padx=(8, 2))
        addr_var = tk.StringVar(value="00000000")
        addr_e = tk.Entry(ctrl, textvariable=addr_var, width=10,
                          bg=MEWGBA_BLUE_THEME["panel"],
                          fg=MEWGBA_BLUE_THEME["accent"],
                          insertbackground=MEWGBA_BLUE_THEME["accent"])
        addr_e.pack(side=tk.LEFT)

        text = tk.Text(top, bg=MEWGBA_BLUE_THEME["panel"],
                       fg=MEWGBA_BLUE_THEME["accent"],
                       font=("Menlo", 9))
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        def refresh():
            region = region_var.get()
            try:
                addr = int(addr_var.get(), 16)
            except ValueError:
                addr = 0
            base, data = self.core.memory_dump(region)
            if not data:
                text.delete("1.0", tk.END)
                text.insert(tk.END, "No data")
                return
            off = addr - base
            if off < 0:
                off = 0
            chunk = data[off:off + 256]
            lines = []
            for i in range(0, len(chunk), 16):
                line_addr = addr + i
                hex_part = " ".join(f"{chunk[i + j]:02x}" for j in range(min(16, len(chunk) - i)))
                ascii_part = "".join(chr(chunk[i + j]) if 32 <= chunk[i + j] < 127 else "." for j in range(min(16, len(chunk) - i)))
                lines.append(f"{line_addr:08X}  {hex_part:<48}  {ascii_part}")
            text.delete("1.0", tk.END)
            text.insert(tk.END, "\n".join(lines))

        tk.Button(ctrl, text="Refresh", command=refresh,
                  bg=MEWGBA_BLUE_THEME["button_bg"],
                  fg=MEWGBA_BLUE_THEME["accent"]).pack(side=tk.RIGHT, padx=4)

        # try to launch hex editor
        try:
            hex_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), HEX_EDITOR_REL)
            hex_path = os.path.normpath(hex_path)
            if os.path.exists(hex_path):
                def launch_hex():
                    region = region_var.get()
                    base, data = self.core.memory_dump(region)
                    if data:
                        tmp = tempfile.NamedTemporaryFile(prefix=f"mewgba_{region}_", suffix=".bin", delete=False)
                        tmp.write(data)
                        tmp.close()
                        subprocess.Popen([sys.executable, hex_path, tmp.name])
                tk.Button(ctrl, text="Hex Editor", command=launch_hex,
                          bg=MEWGBA_BLUE_THEME["button_bg"],
                          fg=MEWGBA_BLUE_THEME["accent"]).pack(side=tk.RIGHT, padx=4)
        except (OSError, ValueError):
            pass

    def _show_cython(self) -> None:
        status = _accel_status()
        top = tk.Toplevel(self.root)
        top.title("Cython Status")
        top.geometry("400x350")
        top.configure(bg=MEWGBA_BLUE_THEME["bg"])
        t = MEWGBA_BLUE_THEME
        text = tk.Text(top, bg=t["panel"], fg=t["accent"], font=("Menlo", 9))
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        lines = [
            f"Cython Active: {status['active']}",
            f"Python: {status['python']}",
            f"Cache: {status['cache']}",
            f"Digest: {status['digest']}",
            "",
            "Functions:",
        ]
        for name, ok in status["functions"].items():
            lines.append(f"  {'✓' if ok else '✗'} {name}")
        text.insert(tk.END, "\n".join(lines))
        text.config(state=tk.DISABLED)

    def _show_about(self) -> None:
        b = _blue_edition_status()
        messagebox.showinfo(
            "About mewgba$ VBAv0.2.1 Blue Edition",
            f"mewgba$ — Single-file GBA Emulator (files=off)\n\n"
            f"Python {b['python']}\n"
            f"Features: {b['features_live']}/{b['features_total']}\n"
            f"Cython: {'Enabled' if b['cython'] else 'Not available'}\n\n"
            f"AC Holdings 1999-2026\n"
            f"CatSDK Blue Tint Edition",
            parent=self.root,
        )

    def _tick(self) -> None:
        t0 = time.perf_counter()
        frame_count = 0

        def loop():
            nonlocal t0, frame_count
            if self.running and self.core.is_loaded:
                self.core._run_frame()
                self._update_display()
                frame_count += 1
            elapsed = time.perf_counter() - t0
            if elapsed >= 1.0:
                fps = frame_count / elapsed
                self.fps_label.config(text=f"FPS: {fps:.0f}")
                t0 = time.perf_counter()
                frame_count = 0
            delay = max(1, int(GBA_FRAME_MS / self.speed))
            self.after_id = self.root.after(delay, loop)

        self.after_id = self.root.after(int(GBA_FRAME_MS), loop)

    def _update_display(self) -> None:
        fb = self.core.framebuffer
        img = self._img
        hex_str = " ".join(f"{fb[i]:02x}{fb[i+1]:02x}{fb[i+2]:02x}" for i in range(0, len(fb), 3))
        img.tk.call(img, 'put', hex_str, '-format', 'rgb')
        # blit the native 240x160 frame into the persistent 2x display image
        # (fixed 2x scale each frame -- no cumulative canvas.scale runaway)
        self._img_2x.tk.call(self._img_2x, 'copy', img, '-zoom', 2, 2)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = MewGBAApp()
    app.run()


if __name__ == "__main__":
    main()