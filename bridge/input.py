# -*- coding: utf-8 -*-
""

import ctypes
import ctypes.wintypes as wt
import time

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ulong, ctypes.c_ulong]

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

VK = {
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "space": 0x20, "enter": 0x0D, "esc": 0x1B, "tab": 0x09,
    "shift": 0x10, "ctrl": 0x11, "alt": 0x12,
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
    "z": 0x5A,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
}

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _INPUT_UNION)]


def vk_of(key):
    if isinstance(key, int):
        return key
    k = key.lower()
    if k not in VK:
        raise KeyError("未知按键: %s" % key)
    return VK[k]


class Keyboard:
    def __init__(self):
        self._down = set()

    def _send(self, vk, up):
        
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP if up else 0, 0)

    def down(self, key):
        vk = vk_of(key)
        if vk not in self._down:
            self._send(vk, False)
            self._down.add(vk)

    def up(self, key):
        vk = vk_of(key)
        if vk in self._down:
            self._send(vk, True)
            self._down.discard(vk)

    def release_all(self):
        for vk in list(self._down):
            self._send(vk, True)
        self._down.clear()

    def tap(self, key, ms=30):
        self.down(key)
        time.sleep(ms / 1000.0)
        self.up(key)

    def hold(self, key, ms):
        self.down(key)
        time.sleep(ms / 1000.0)
        self.up(key)

    def send_to(self, hwnd, key):
        vk = vk_of(key)
        user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
        time.sleep(0.02)
        user32.PostMessageW(hwnd, WM_KEYUP, vk, 0)


def find_window(title_part):
    ""
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if title_part.lower() in buf.value.lower():
                found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(cb, 0)
    return found[0][0] if found else None


if __name__ == "__main__":
    print("VK keys:", len(VK))
