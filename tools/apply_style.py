# -*- coding: utf-8 -*-
"""
把 weasel.custom.yaml 里的 patch 合并进 build/weasel.yaml
=========================================================
为什么需要这一步：
  librime 的 auto-patch 只在「编译配置」那一刻生效，而 Weasel 运行时的
  config_open("weasel") 只是直接读 build/weasel.yaml，不会再走编译器。
  所以 weasel.custom.yaml 改了也不会自动反映到产物里。
  这里自己把 patch 应用一遍，写回产物，效果等价且可控。

支持的 patch 写法（够用即可）：
  "a/b/c": 值               覆盖/新增
  "a/b/+": [x, y]           追加到列表末尾
  "a/b/@before 0": 值       插到列表开头
  "a/b/@after 0": 值        插到第 0 项之后
"""

import os
import sys
import yaml

DATA_DIR = r"C:\Program Files\Rime\weasel-0.17.4\data"
USER_DIR = os.path.join(os.environ["APPDATA"], "Rime")

SRC = os.path.join(DATA_DIR, "weasel.yaml")
CUSTOM = os.path.join(USER_DIR, "weasel.custom.yaml")
DEST = os.path.join(USER_DIR, "build", "weasel.yaml")
BASE_DEST = os.path.join(USER_DIR, "build", "weasel.base.yaml")


def get_parent(doc, parts, create=False):
    """按路径逐级下钻，返回 (容器, 最后一层的键)。"""
    node = doc
    for p in parts[:-1]:
        if not isinstance(node, dict):
            return None, None
        if p not in node or not isinstance(node[p], (dict, list)):
            if not create:
                return None, None
            node[p] = {}
        node = node[p]
    return node, parts[-1]


def apply_one(doc, key, value):
    """应用单条 patch。"""
    parts = key.split("/")
    last = parts[-1]

    # 列表操作后缀
    if last in ("+", "") or last.startswith("@"):
        container, k = get_parent(doc, parts, create=True)
        if container is None:
            return False
        if not isinstance(container, dict):
            return False
        target = k if last != "+" else parts[-2]
        arr = container.get(target)
        if not isinstance(arr, list):
            arr = []
            container[target] = arr
        if last == "+":
            arr.extend(value if isinstance(value, list) else [value])
        else:
            # "@before N" / "@after N"
            op, _, idx = last.partition(" ")
            idx = int(idx or 0)
            if isinstance(value, list):
                if op == "@before":
                    arr[idx:idx] = value
                else:
                    arr[idx + 1:idx + 1] = value
            else:
                arr.insert(idx if op == "@before" else idx + 1, value)
        return True

    container, k = get_parent(doc, parts, create=True)
    if container is None or not isinstance(container, dict):
        return False
    container[k] = value
    return True


def load_yaml_text(path):
    """读 YAML 并做容错：原版配置里混了 tab，PyYAML 不接受 tab 作缩进/分隔。"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    text = text.replace("\t", "  ")
    return yaml.safe_load(text) or {}, text


def main():
    # 首次运行：把安装目录的原版配置存一份当干净基底，之后都基于它
    if not os.path.exists(BASE_DEST):
        with open(SRC, "r", encoding="utf-8") as f:
            base_text = f.read().replace("\t", "  ")
        os.makedirs(os.path.dirname(BASE_DEST), exist_ok=True)
        with open(BASE_DEST, "w", encoding="utf-8") as f:
            f.write(base_text)
    with open(BASE_DEST, "r", encoding="utf-8") as f:
        base_text = f.read().replace("\t", "  ")

    doc = yaml.safe_load(base_text) or {}

    if not os.path.exists(CUSTOM):
        print("no weasel.custom.yaml, skip")
        return 0

    with open(CUSTOM, "r", encoding="utf-8") as f:
        custom = yaml.safe_load(f) or {}

    patch = custom.get("patch") or {}
    applied = 0
    for key, value in patch.items():
        if apply_one(doc, str(key), value):
            applied += 1
        else:
            print(f"  skipped: {key}")

    with open(DEST, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, width=4096)

    print(f"applied {applied}/{len(patch)} patches -> {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
