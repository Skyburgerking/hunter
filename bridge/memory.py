# -*- coding: utf-8 -*-
""

import ctypes
import ctypes.wintypes as wt
import struct

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("th32ModuleID", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage", wt.DWORD),
        ("ProccntUsage", wt.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wt.DWORD),
        ("hModule", wt.HMODULE),
        ("szModule", ctypes.c_char * 256),
        ("szExePath", ctypes.c_char * 260),
    ]


def list_processes(name_part=None):
    ""
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap in (0, -1):
        raise OSError("CreateToolhelp32Snapshot failed")
    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    out = []
    ok = kernel32.Process32First(snap, ctypes.byref(entry))
    while ok:
        name = entry.szExeFile.decode("mbcs", "replace")
        if name_part is None or name_part.lower() in name.lower():
            out.append({"pid": entry.th32ProcessID, "exe": name})
        ok = kernel32.Process32Next(snap, ctypes.byref(entry))
    kernel32.CloseHandle(snap)
    return out


class Module:
    def __init__(self, name, base, size, path):
        self.name = name
        self.base = base
        self.size = size
        self.path = path

    def __repr__(self):
        return "Module(%s, base=0x%X, size=0x%X)" % (self.name, self.base, self.size)


class Process:
    def __init__(self, name=None, pid=None):
        if pid is None:
            matches = list_processes(name)
            if not matches:
                raise RuntimeError("找不到进程: %s" % name)
            pid = matches[0]["pid"]
            self.exe = matches[0]["exe"]
        else:
            self.exe = name or str(pid)
        self.pid = pid
        self.handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not self.handle:
            err = ctypes.get_last_error()
            raise OSError("OpenProcess failed (pid=%d, err=%d)" % (pid, err))

    def close(self):
        if getattr(self, "handle", None):
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    
    def module(self, name_part):
        snap = kernel32.CreateToolhelp32Snapshot(
            TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid)
        if snap in (0, -1):
            raise OSError("CreateToolhelp32Snapshot(module) failed")
        entry = MODULEENTRY32()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32)
        ok = kernel32.Module32First(snap, ctypes.byref(entry))
        found = None
        while ok:
            nm = entry.szModule.decode("mbcs", "replace")
            if name_part.lower() in nm.lower():
                found = Module(
                    nm,
                    ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value or 0,
                    entry.modBaseSize,
                    entry.szExePath.decode("mbcs", "replace"),
                )
                break
            ok = kernel32.Module32Next(snap, ctypes.byref(entry))
        kernel32.CloseHandle(snap)
        if not found:
            raise RuntimeError("找不到模块: %s" % name_part)
        return found

    
    def read(self, addr, size):
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(
            self.handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(got))
        if not ok:
            raise OSError("ReadProcessMemory 0x%X failed (err=%d)"
                          % (addr, ctypes.get_last_error()))
        return buf.raw[:got.value]

    def write(self, addr, data):
        buf = ctypes.create_string_buffer(data, len(data))
        put = ctypes.c_size_t(0)
        ok = kernel32.WriteProcessMemory(
            self.handle, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(put))
        if not ok:
            raise OSError("WriteProcessMemory 0x%X failed (err=%d)"
                          % (addr, ctypes.get_last_error()))
        return put.value

    def read_int(self, addr, size=4, signed=False):
        raw = self.read(addr, size)
        return int.from_bytes(raw, "little", signed=signed)

    def write_int(self, addr, value, size=4):
        return self.write(addr, int(value).to_bytes(size, "little",
                                                    signed=value < 0))

    def read_float(self, addr):
        return struct.unpack("<f", self.read(addr, 4))[0]

    def read_double(self, addr):
        return struct.unpack("<d", self.read(addr, 8))[0]

    def read_ptr(self, addr, size=4):
        return int.from_bytes(self.read(addr, size), "little")


if __name__ == "__main__":
    for p in list_processes()[:8]:
        print(p)
