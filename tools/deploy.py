"""
皮皮输入法 · 直接调用 rime.dll 执行部署
绕开 WeaselDeployer（它在非交互环境下静默失败）
"""

import ctypes
import os
import sys
from ctypes import c_int, c_char_p, c_void_p, POINTER, Structure

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


def make_traits(log_level=0):
    t = RimeTraits()
    ctypes.memset(ctypes.byref(t), 0, ctypes.sizeof(t))
    t.data_size = ctypes.sizeof(RimeTraits)
    t.shared_data_dir = SHARED_DIR.encode("mbcs")
    t.user_data_dir = USER_DIR.encode("mbcs")
    t.distribution_name = "小狼毫".encode("mbcs")
    t.distribution_code_name = b"weasel"
    t.distribution_version = b"0.17.4"
    t.app_name = b"rime.pipi"
    t.modules = None
    t.min_log_level = log_level
    t.log_dir = b""  # 空字符串 = 只输出到 stderr
    t.prebuilt_data_dir = None
    t.staging_dir = None
    return t


def main():
    print(f"shared: {SHARED_DIR}")
    print(f"user:   {USER_DIR}")

    lib = ctypes.WinDLL(DLL_PATH)

    lib.RimeSetup.argtypes = [POINTER(RimeTraits)]
    lib.RimeSetup.restype = None
    lib.RimeDeployerInitialize.argtypes = [POINTER(RimeTraits)]
    lib.RimeDeployerInitialize.restype = None
    lib.RimeDeployWorkspace.argtypes = [POINTER(RimeTraits)]
    lib.RimeDeployWorkspace.restype = c_int
    lib.RimeFinalize.argtypes = []
    lib.RimeFinalize.restype = None

    t = make_traits()
    lib.RimeSetup(ctypes.byref(t))
    lib.RimeDeployerInitialize(ctypes.byref(t))

    print("--- deploying ---")
    result = lib.RimeDeployWorkspace(ctypes.byref(t))
    print(f"deploy result: {result} (1=success, 0=fail)")

    lib.RimeFinalize()

    build_dir = os.path.join(USER_DIR, "build")
    if os.path.isdir(build_dir):
        files = os.listdir(build_dir)
        print(f"build dir has {len(files)} files")
        hits = [f for f in files if "luna_pinyin_simp" in f]
        print(f"luna_pinyin_simp artifacts: {hits}")
    else:
        print("build dir NOT created")
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
