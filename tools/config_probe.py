"""
读取 Rime 引擎实际看到的 weasel 配置值，用于排查 display_tray_icon 为什么不生效。
"""
import ctypes
import os
from ctypes import c_int, c_char_p, c_void_p, POINTER, Structure, byref

DLL_PATH = r"C:\Program Files\Rime\weasel-0.17.4\rime.dll"
SHARED_DIR = r"C:\Program Files\Rime\weasel-0.17.4\data"
USER_DIR = os.path.expandvars(r"%APPDATA%\Rime")


class RimeTraits(Structure):
    _fields_ = [
        ("data_size", c_int),
        ("shared_data_dir", c_char_p),
        ("user_data_dir", c_char_p),
        ("distribution_name", c_char_p),
        ("distribution_code_name", c_char_p),
        ("distribution_version", c_char_p),
        ("app_name", c_char_p),
        ("modules", POINTER(c_char_p)),
        ("min_log_level", c_int),
        ("log_dir", c_char_p),
        ("prebuilt_data_dir", c_char_p),
        ("staging_dir", c_char_p),
    ]


class RimeConfig(Structure):
    _fields_ = [("ptr", c_void_p)]


def make_traits():
    t = RimeTraits()
    ctypes.memset(byref(t), 0, ctypes.sizeof(t))
    t.data_size = ctypes.sizeof(RimeTraits)
    t.shared_data_dir = SHARED_DIR.encode("mbcs")
    t.user_data_dir = USER_DIR.encode("mbcs")
    t.distribution_name = "小狼毫".encode("mbcs")
    t.distribution_code_name = b"weasel"
    t.distribution_version = b"0.17.4"
    t.app_name = b"rime.probe"
    t.modules = None
    t.min_log_level = 0
    t.log_dir = b""
    return t


def main():
    lib = ctypes.WinDLL(DLL_PATH)

    lib.RimeSetup.argtypes = [POINTER(RimeTraits)]
    lib.RimeSetup.restype = None
    lib.RimeDeployerInitialize.argtypes = [POINTER(RimeTraits)]
    lib.RimeDeployerInitialize.restype = None
    lib.RimeConfigOpen.argtypes = [c_char_p, POINTER(RimeConfig)]
    lib.RimeConfigOpen.restype = c_int
    lib.RimeConfigGetBool.argtypes = [POINTER(RimeConfig), c_char_p, POINTER(c_int)]
    lib.RimeConfigGetBool.restype = c_int
    lib.RimeConfigGetString.argtypes = [POINTER(RimeConfig), c_char_p, c_char_p, ctypes.c_size_t]
    lib.RimeConfigGetString.restype = c_int
    lib.RimeConfigClose.argtypes = [POINTER(RimeConfig)]
    lib.RimeConfigClose.restype = None

    t = make_traits()
    lib.RimeSetup(byref(t))
    lib.RimeDeployerInitialize(byref(t))

    cfg = RimeConfig()
    rc = lib.RimeConfigOpen(b"weasel", byref(cfg))
    print(f"RimeConfigOpen('weasel') -> {rc}  ({'ok' if rc else 'FAIL'})")
    if not rc:
        return 1

    val = c_int(-1)
    ok = lib.RimeConfigGetBool(byref(cfg), b"style/display_tray_icon", byref(val))
    print(f"  style/display_tray_icon = {val.value}   (get ok={ok})")

    buf = ctypes.create_string_buffer(256)
    ok2 = lib.RimeConfigGetString(byref(cfg), b"style/color_scheme", buf, 256)
    print(f"  style/color_scheme      = {buf.value.decode('utf-8', 'replace')!r}  (get ok={ok2})")

    val2 = c_int(-1)
    ok3 = lib.RimeConfigGetBool(byref(cfg), b"style/horizontal", byref(val2))
    print(f"  style/horizontal        = {val2.value}   (get ok={ok3})")

    lib.RimeConfigClose(byref(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
