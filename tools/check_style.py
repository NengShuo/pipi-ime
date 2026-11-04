# -*- coding: utf-8 -*-
"""读取 Rime 运行时实际生效的 weasel 配置，用于确认 custom 补丁有没有生效。"""
import ctypes
import ctypes.wintypes as wt
import os

DLL = r"C:\Program Files\Rime\weasel-0.17.4\rime.dll"
USER_DIR = os.path.join(os.environ["APPDATA"], "Rime")
SHARED_DIR = r"C:\Program Files\Rime\weasel-0.17.4\data"


class RimeTraits(ctypes.Structure):
    _fields_ = [
        ("data_size", ctypes.c_int),
        ("shared_data_dir", ctypes.c_char_p),
        ("user_data_dir", ctypes.c_char_p),
        ("distribution_name", ctypes.c_char_p),
        ("distribution_code_name", ctypes.c_char_p),
        ("distribution_version", ctypes.c_char_p),
        ("app_name", ctypes.c_char_p),
        ("modules", ctypes.c_char_p),
        ("min_log_level", ctypes.c_int),
        ("log_dir", ctypes.c_char_p),
        ("prebuilt_data_dir", ctypes.c_char_p),
        ("staging_dir", ctypes.c_char_p),
    ]


class RimeConfig(ctypes.Structure):
    _fields_ = [("ptr", ctypes.c_void_p)]


lib = ctypes.WinDLL(DLL)
lib.RimeSetup.restype = None
lib.RimeSetup.argtypes = [ctypes.POINTER(RimeTraits)]
lib.RimeInitialize.restype = ctypes.c_bool
lib.RimeFinalize.restype = None
lib.RimeConfigOpen.restype = ctypes.c_bool
lib.RimeConfigOpen.argtypes = [ctypes.c_char_p, ctypes.POINTER(RimeConfig)]
lib.RimeConfigClose.restype = ctypes.c_bool
lib.RimeConfigClose.argtypes = [ctypes.POINTER(RimeConfig)]
lib.RimeConfigGetString.restype = ctypes.c_bool
lib.RimeConfigGetString.argtypes = [ctypes.POINTER(RimeConfig), ctypes.c_char_p,
                                    ctypes.c_char_p, ctypes.c_size_t]
lib.RimeConfigGetBool.restype = ctypes.c_bool
lib.RimeConfigGetBool.argtypes = [ctypes.POINTER(RimeConfig), ctypes.c_char_p,
                                  ctypes.POINTER(ctypes.c_int)]
lib.RimeConfigGetInt.restype = ctypes.c_bool
lib.RimeConfigGetInt.argtypes = [ctypes.POINTER(RimeConfig), ctypes.c_char_p,
                                 ctypes.POINTER(ctypes.c_int)]


def main():
    t = RimeTraits()
    t.data_size = ctypes.sizeof(RimeTraits)
    t.shared_data_dir = SHARED_DIR.encode()
    t.user_data_dir = USER_DIR.encode()
    t.prebuilt_data_dir = SHARED_DIR.encode()
    t.distribution_name = "皮皮输入法".encode()
    t.distribution_code_name = "pipi".encode()
    t.distribution_version = "0.1".encode()
    t.app_name = "pipi.check".encode()
    t.min_log_level = 3
    lib.RimeSetup(ctypes.byref(t))
    lib.RimeInitialize()

    cfg = RimeConfig()
    ok = lib.RimeConfigOpen(b"weasel", ctypes.byref(cfg))
    print(f"config_open('weasel') = {ok}")
    if not ok:
        lib.RimeFinalize()
        return

    buf = ctypes.create_string_buffer(512)
    for key in [b"style/current_zhung_icon", b"style/current_ascii_icon",
                b"style/color_scheme"]:
        r = lib.RimeConfigGetString(ctypes.byref(cfg), key, buf, 512)
        print(f"  {key.decode():30s} = {buf.value.decode(errors='replace')!r}  ok={bool(r)}")

    for key in [b"style/display_tray_icon", b"style/corner_radius"]:
        v = ctypes.c_int()
        r = (lib.RimeConfigGetBool(ctypes.byref(cfg), key, ctypes.byref(v))
             if key == b"style/display_tray_icon"
             else lib.RimeConfigGetInt(ctypes.byref(cfg), key, ctypes.byref(v)))
        print(f"  {key.decode():30s} = {v.value}  ok={bool(r)}")

    # 看自定义皮肤是否也在
    r = lib.RimeConfigGetString(ctypes.byref(cfg),
                                b"preset_color_schemes/pipi/name", buf, 512)
    print(f"  preset_color_schemes/pipi/name = {buf.value.decode(errors='replace')!r} ok={bool(r)}")

    lib.RimeConfigClose(ctypes.byref(cfg))
    lib.RimeFinalize()


if __name__ == "__main__":
    main()
