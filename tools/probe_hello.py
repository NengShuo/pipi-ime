"""
快速探针：英文模式下打 hello，分别按空格 / 回车，看能不能上屏
目的：复现「英文打不出来」的问题，定位是哪一步丢了文本
"""

import ctypes
import sys
from ctypes import byref, sizeof, memset

sys.path.insert(0, ".")
from test_ascii_candidate import (
    RimeTraits, RimeContext, RimeCommit, setup_traits, bind, u8, dump, take_commit,
    DLL_PATH, SCHEMA,
)
import ctypes as ct

lib = ct.WinDLL(DLL_PATH)
bind(lib)

traits = setup_traits()
lib.RimeSetup(byref(traits))
lib.RimeInitialize(byref(traits))

session = lib.RimeCreateSession()
lib.RimeSelectSchema(session, SCHEMA)
lib.RimeSetOption(session, b"ascii_mode", 1)

print("=" * 60)
print("英文模式打 hello，然后按空格")
print("=" * 60)
lib.RimeSimulateKeySequence(session, b"hello")
dump(lib, session, "按空格前")
lib.RimeSimulateKeySequence(session, b"space")
c1 = take_commit(lib, session)
print(f"  >>> 按空格后上屏 = {c1!r}")
lib.RimeClearComposition(session)

print()
print("=" * 60)
print("英文模式打 hello，然后按回车")
print("=" * 60)
lib.RimeSimulateKeySequence(session, b"hello")
dump(lib, session, "按回车前")
lib.RimeSimulateKeySequence(session, b"Return")
c2 = take_commit(lib, session)
print(f"  >>> 按回车后上屏 = {c2!r}")
lib.RimeClearComposition(session)

print()
print("=" * 60)
print("中文模式打 hello，然后按空格（对照）")
print("=" * 60)
lib.RimeSetOption(session, b"ascii_mode", 0)
lib.RimeSimulateKeySequence(session, b"hello")
dump(lib, session, "按空格前")
lib.RimeSimulateKeySequence(session, b"space")
c3 = take_commit(lib, session)
print(f"  >>> 按空格后上屏 = {c3!r}")

lib.RimeDestroySession(session)
lib.RimeFinalize()
