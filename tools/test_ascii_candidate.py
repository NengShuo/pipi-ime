"""
皮皮输入法 · 验证 04：英文模式下的中文候选 + 编辑键行为

覆盖五件事：
  A 中文模式基线          打 nihao，应该出「你好」
  B 英文模式打拼音        打 woyaochifan，应该出「我要吃饭」
  C 英文模式退格          打 woyao 再按退格，应该只少一个字母，不删文档
  D 英文模式数字选候选    打 woyaochifan 再按 2，应该上屏第二候选
  E 英文模式打英文单词    打 meeting，看误伤情况
"""

import ctypes
import os
import sys
from ctypes import (
    c_int, c_char_p, c_void_p, POINTER, Structure, byref, sizeof, memset,
)

DLL_PATH = r"C:\Program Files\Rime\weasel-0.17.4\rime.dll"
SHARED_DIR = r"C:\Program Files\Rime\weasel-0.17.4\data"
USER_DIR = os.path.expandvars(r"%APPDATA%\Rime")
SCHEMA = b"luna_pinyin_simp"


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


class RimeComposition(Structure):
    _fields_ = [
        ("length", c_int),
        ("cursor_pos", c_int),
        ("sel_start", c_int),
        ("sel_end", c_int),
        ("preedit", c_char_p),
    ]


class RimeCandidate(Structure):
    _fields_ = [
        ("text", c_char_p),
        ("comment", c_char_p),
        ("reserved", c_void_p),
    ]


class RimeMenu(Structure):
    _fields_ = [
        ("page_size", c_int),
        ("page_no", c_int),
        ("is_last_page", c_int),
        ("highlighted_candidate_index", c_int),
        ("num_candidates", c_int),
        ("candidates", POINTER(RimeCandidate)),
        ("select_keys", c_char_p),
    ]


class RimeContext(Structure):
    _fields_ = [
        ("data_size", c_int),
        ("composition", RimeComposition),
        ("menu", RimeMenu),
        ("commit_text_preview", c_char_p),
        ("select_labels", POINTER(c_char_p)),
    ]


class RimeCommit(Structure):
    _fields_ = [
        ("data_size", c_int),
        ("text", c_char_p),
    ]


def setup_traits():
    t = RimeTraits()
    memset(byref(t), 0, sizeof(t))
    t.data_size = sizeof(RimeTraits)
    t.shared_data_dir = SHARED_DIR.encode("mbcs")
    t.user_data_dir = USER_DIR.encode("mbcs")
    t.distribution_name = "小狼毫".encode("mbcs")
    t.distribution_code_name = b"weasel"
    t.distribution_version = b"0.17.4"
    t.app_name = b"rime.pipi"
    t.min_log_level = 3          # 只看 ERROR，避免日志刷屏
    t.log_dir = b""
    return t


def bind(lib):
    lib.RimeSetup.argtypes = [POINTER(RimeTraits)]
    lib.RimeSetup.restype = None
    lib.RimeInitialize.argtypes = [POINTER(RimeTraits)]
    lib.RimeInitialize.restype = None
    lib.RimeFinalize.argtypes = []
    lib.RimeFinalize.restype = None
    lib.RimeCreateSession.argtypes = []
    lib.RimeCreateSession.restype = c_void_p
    lib.RimeDestroySession.argtypes = [c_void_p]
    lib.RimeDestroySession.restype = c_int
    lib.RimeSelectSchema.argtypes = [c_void_p, c_char_p]
    lib.RimeSelectSchema.restype = c_int
    lib.RimeSetOption.argtypes = [c_void_p, c_char_p, c_int]
    lib.RimeSetOption.restype = None
    lib.RimeGetOption.argtypes = [c_void_p, c_char_p]
    lib.RimeGetOption.restype = c_int
    lib.RimeSimulateKeySequence.argtypes = [c_void_p, c_char_p]
    lib.RimeSimulateKeySequence.restype = c_int
    lib.RimeGetContext.argtypes = [c_void_p, POINTER(RimeContext)]
    lib.RimeGetContext.restype = c_int
    lib.RimeFreeContext.argtypes = [POINTER(RimeContext)]
    lib.RimeFreeContext.restype = None
    lib.RimeClearComposition.argtypes = [c_void_p]
    lib.RimeClearComposition.restype = c_int
    lib.RimeGetCommit.argtypes = [c_void_p, POINTER(RimeCommit)]
    lib.RimeGetCommit.restype = c_int
    lib.RimeFreeCommit.argtypes = [POINTER(RimeCommit)]
    lib.RimeFreeCommit.restype = None


def u8(p):
    if not p:
        return ""
    try:
        return p.decode("utf-8", errors="replace")
    except Exception:
        return repr(p)


def dump(lib, session, title):
    """读当前候选栏，返回 (preedit, 候选文本列表, 注释列表)"""
    ctx = RimeContext()
    memset(byref(ctx), 0, sizeof(ctx))
    ctx.data_size = sizeof(RimeContext)

    if not lib.RimeGetContext(session, byref(ctx)):
        print(f"  [{title}] 取上下文失败")
        return "", []

    preedit = u8(ctx.composition.preedit)
    n = ctx.menu.num_candidates
    print(f"        [调试] 选中项 index = {ctx.menu.highlighted_candidate_index}")
    cands, comments = [], []
    print(f"  [{title}] 输入框={preedit!r}  候选数={n}")
    for i in range(n):
        c = ctx.menu.candidates[i]
        text, comment = u8(c.text), u8(c.comment)
        cands.append(text)
        comments.append(comment)
        print(f"       {i + 1}. {text}    {('// ' + comment) if comment else ''}")

    lib.RimeFreeContext(byref(ctx))
    return preedit, cands, comments


def take_commit(lib, session):
    """取走已上屏的文字"""
    commit = RimeCommit()
    memset(byref(commit), 0, sizeof(commit))
    commit.data_size = sizeof(RimeCommit)
    if lib.RimeGetCommit(session, byref(commit)):
        text = u8(commit.text)
        lib.RimeFreeCommit(byref(commit))
        return text
    return None


def main():
    lib = ctypes.WinDLL(DLL_PATH)
    bind(lib)

    traits = setup_traits()
    lib.RimeSetup(byref(traits))
    lib.RimeInitialize(byref(traits))

    session = lib.RimeCreateSession()
    if not session:
        print("创建会话失败")
        return 1

    ok = lib.RimeSelectSchema(session, SCHEMA)
    print(f"切换方案 {SCHEMA.decode()} : {'成功' if ok else '失败'}\n")

    r = {}

    print("=" * 62)
    print("A · 中文模式基线：打 nihao")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 0)
    lib.RimeSimulateKeySequence(session, b"nihao")
    r["A"] = dump(lib, session, "中文模式 nihao")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("B · 核心：英文模式打 woyaochifan")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 1)
    lib.RimeSimulateKeySequence(session, b"woyaochifan")
    r["B"] = dump(lib, session, "英文模式 woyaochifan")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("C · 退格：英文模式打 woyao 再按一次退格")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 1)
    lib.RimeSimulateKeySequence(session, b"woyao")
    before = dump(lib, session, "退格前")
    lib.RimeSimulateKeySequence(session, b"{BackSpace}")
    after = dump(lib, session, "退格后")
    committed = take_commit(lib, session)
    r["C"] = (before, after, committed)
    print(f"  上屏文字={committed!r}（应为空，退格不该把正文删掉）")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("D · 数字键选候选：英文模式打 woyaochifan 再按 1")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 1)
    lib.RimeSimulateKeySequence(session, b"woyaochifan")
    dump(lib, session, "按 1 之前")
    lib.RimeSimulateKeySequence(session, b"1")
    committed = take_commit(lib, session)
    print(f"  上屏文字={committed!r}（应该是「我要吃饭」）")
    r["D"] = committed
    preedit_left = dump(lib, session, "按 1 之后")[0]
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("E · 误伤检查：英文模式打 meeting")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 1)
    lib.RimeSimulateKeySequence(session, b"meeting")
    r["E"] = dump(lib, session, "英文模式 meeting")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("F · 重复输入：模拟「按下 a、松开 a、按下 b、松开 b」")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 1)
    lib.RimeSimulateKeySequence(session, b"a{Release+a}b{Release+b}")
    r["F"] = dump(lib, session, "按键含松开事件")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("G · 空格上屏中文：英文模式打 woyaochifan 再按空格")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 1)
    lib.RimeSimulateKeySequence(session, b"woyaochifan")
    dump(lib, session, "按空格前")
    lib.RimeSimulateKeySequence(session, b"{space}")
    r["G"] = take_commit(lib, session)
    print(f"  上屏文字={r['G']!r}（应该是「我要吃饭」，不是字母串）")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("H · 英文单词：英文模式打 hello 再按空格")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 1)
    lib.RimeSimulateKeySequence(session, b"hello")
    r["H_cands"] = dump(lib, session, "按空格前")
    lib.RimeSimulateKeySequence(session, b"{space}")
    r["H"] = take_commit(lib, session)
    print(f"  上屏文字={r['H']!r}（应该是 'hello ' 带空格）")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("I · meeting 是否还弹中文")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 1)
    lib.RimeSimulateKeySequence(session, b"meeting")
    r["I"] = dump(lib, session, "英文模式 meeting")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("J · 中文模式下打英文：应该也能直接出 hello")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 0)
    lib.RimeSimulateKeySequence(session, b"hello")
    r["J_cands"] = dump(lib, session, "中文模式 hello（按空格前）")
    lib.RimeSimulateKeySequence(session, b"{space}")
    r["J"] = take_commit(lib, session)
    print(f"  上屏文字={r['J']!r}（应该是 'hello '，说明不用切模式）")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("K · 中文模式打拼音：空格照常上屏中文")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 0)
    lib.RimeSimulateKeySequence(session, b"nihao")
    dump(lib, session, "中文模式 nihao（按空格前）")
    lib.RimeSimulateKeySequence(session, b"{space}")
    r["K"] = take_commit(lib, session)
    print(f"  上屏文字={r['K']!r}（应该是「你好」）")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("L · 注释列已关闭：候选右侧不应再有拼音")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 0)
    lib.RimeSimulateKeySequence(session, b"woyaochifan")
    r["L"] = dump(lib, session, "woyaochifan 的注释列")
    lib.RimeClearComposition(session)

    print()
    print("=" * 62)
    print("M · 备选：拼音原样候选应固定在第 2 位，且能选上屏")
    print("=" * 62)
    lib.RimeSetOption(session, b"ascii_mode", 0)
    lib.RimeSimulateKeySequence(session, b"nihao")
    pre, texts, comments = dump(lib, session, "nihao（按 5 之前）")
    idx = texts.index("nihao") + 1 if "nihao" in texts else 0
    print(f"  原样拼音候选在第 {idx} 位（应为 2）")
    if idx:
        lib.RimeSimulateKeySequence(session, str(idx).encode())
        r["M"] = take_commit(lib, session)
    else:
        r["M"] = None
    print(f"  上屏文字={r['M']!r}（应该是 'nihao'）")
    lib.RimeClearComposition(session)

    lib.RimeDestroySession(session)
    lib.RimeFinalize()

    print()
    print("=" * 62)
    print("结论")
    print("=" * 62)
    a_ok = any("你" in c for c in r["A"][1])
    b_ok = r["B"][1] and r["B"][1][0] == "我要吃饭"
    c_pre = r["C"][1][0]
    c_ok = c_pre.replace(" ", "") == "woya" and not r["C"][2]
    d_ok = r["D"] == "我要吃饭"
    e_cands = r["E"][1]
    f_pre = r["F"][0].replace(" ", "")
    f_ok = f_pre == "ab"

    print(f"  A 中文模式正常出中文        : {'是 ✅' if a_ok else '否 ❌'}  {r['A'][1][:3]}")
    print(f"  B 英文模式出正确中文        : {'是 ✅' if b_ok else '否 ❌'}  {r['B'][1][:3]}")
    print(f"  C 退格只删字母不删正文      : {'是 ✅' if c_ok else '否 ❌'}  输入框={c_pre!r} 上屏={r['C'][2]!r}")
    print(f"  D 数字键能选候选            : {'是 ✅' if d_ok else '否 ❌'}  上屏={r['D']!r}")
    print(f"  F 松开按键不重复输入        : {'是 ✅' if f_ok else '否 ❌'}  输入框={r['F'][0]!r}（应为 ab）")
    print(f"  E meeting 误伤             : {e_cands[:3]}")

    g_ok = r["G"] == "我要吃饭"
    h_ok = (r["H"] or "").strip() == "hello"
    i_ok = bool(r["I"][1]) and r["I"][1][0] == "meeting"

    print(f"  G 空格上屏中文候选          : {'是 ✅' if g_ok else '否 ❌'}  上屏={r['G']!r}")
    print(f"  H 英文单词能打出来          : {'是 ✅' if h_ok else '否 ❌'}  上屏={r['H']!r}")
    print(f"  I 英文原文排第一候选        : {'是 ✅' if i_ok else '否 ❌'}  候选={r['I'][1][:3]}")

    j_ok = (r["J"] or "").strip() == "hello"
    k_ok = r["K"] == "你好"
    print(f"  J 中文模式下也能打英文      : {'是 ✅' if j_ok else '否 ❌'}  上屏={r['J']!r}")
    print(f"  K 中文模式空格照常上屏中文  : {'是 ✅' if k_ok else '否 ❌'}  上屏={r['K']!r}")

    l_comments = r["L"][2]
    l_ok = all((c or "") == "" for c in l_comments)
    m_ok = r["M"] == "nihao"
    print(f"  L 注释列已关闭              : {'是 ✅' if l_ok else '否 ❌'}  注释={l_comments[:3]}")
    print(f"  M 拼音原样备选可用          : {'是 ✅' if m_ok else '否 ❌'}  上屏={r['M']!r}")

    all_ok = (a_ok and b_ok and c_ok and d_ok and f_ok
              and g_ok and h_ok and i_ok and j_ok and k_ok
              and l_ok and m_ok)
    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
