# 验证 02：小狼毫前端与发行版插件支持

- 验证日期：2026-11-01
- 验证方式：静态代码分析（未安装任何软件）
- 代码来源：`rime/weasel` 官方仓库 master（当前版本 0.17.4，2025-06-04）
- 验证人：WorkBuddy

---

## 一、结论

**上一份报告列出的两个致命风险，全部排除。**

| 风险 | 结论 |
|---|---|
| 小狼毫发行版是否编进 Lua 模块 | **是，官方内置，2019 年起** |
| Weasel 在英文模式下是否显示候选窗 | **会显示，隐藏逻辑里没有英文模式判断** |

另外有个意外收获：**八股文（octagram）语言模型也是官方内置的**，这正好是当初判断的"最大风险"所在，现在不用自己训练模型。

---

## 二、证据一：候选窗在英文模式下会显示

### 判定逻辑

`weasel/WeaselUI/WeaselPanel.cpp`，`_UpdateHideCandidates()`：

```cpp
bool inline_no_candidates =
    (m_style.inline_preedit && m_candidateCount == 0) && !show_tips;
hide_candidates = inline_no_candidates ||
                  (margin_negative && !show_tips && !show_schema_menu);
```

这是决定候选窗是否隐藏的**唯一**逻辑。全部条件只有两个：

1. 开了 `inline_preedit` 且**候选数为 0**
2. 边距为负（`margin_negative`）且不在提示模式下

**代码里没有任何一处判断 `ascii_mode`。** 也就是说，只要候选数大于 0，窗口就显示，与当前是中文模式还是英文模式无关。

### 候选数据确实会传过去

`weasel/RimeWithWeasel/RimeWithWeasel.cpp`：

```cpp
bool has_candidates = ctx.menu.num_candidates > 0;
...
if (has_candidates) {
  // 序列化候选信息，发送给 UI 进程
}
```

注意：`is_composing` 只影响 preedit（输入框里的字母）要不要传，**不影响候选**。候选只看 `num_candidates`。

### 而英文模式下候选数不会是 0

由验证 01 已确认：英文输入会生成 `raw` 段，`echo_translator` 会对任何输入产出"原文"候选。所以英文模式下 `num_candidates` 至少为 1。

**加挂 `lua_translator` 之后，中文候选会和原文候选出现在同一个候选窗里。**

---

## 三、证据二：Lua 是官方内置插件

`weasel/CHANGELOG.md` 第 425–447 行，0.14.0（2019-06-11）：

> 將Rime插件納入自動化構建流程。本次發行包含兩款插件：
> - [librime-lua](https://github.com/hchunhui/librime-lua)
> - [librime-octagram](https://github.com/lotem/librime-octagram)

从 2019 年起，小狼毫的**官方发行包**就一直包含这两个插件，不是需要自己编译的可选项。

当前版本 0.17.4（2025-06-04），仍在持续维护。

---

## 四、意外收获：八股文语言模型也已内置

`librime-octagram` 就是俗称的「八股文」，基于 n-gram 的整句语言模型插件。

这很关键。前几轮讨论里我一直强调：

> 拼音转中文的准确率八成靠语言模型，不是靠词库。这是整个项目最难的一关。

现在的结论是：**这一关不需要自己训练模型，官方插件已经装在你的输入法里了。**

`librime` 主仓里也有配套的 `src/rime/gear/grammar.h`，说明引擎侧原生支持这个模型。

但要注意：是否启用、以及它在 `raw` 段上会不会生效，需要配置和实测，见下节。

---

## 五、剩余风险

| 风险 | 说明 | 等级 |
|---|---|---|
| 八股文在 `raw` 段是否生效 | octagram 通过 translator 工作，可能受标签匹配限制，需实测 | 中 |
| 性能 | 每键跑一遍 Lua 翻译器 + 语言模型，长输入可能掉帧 | 中 |
| 拼音解析准确率 | 这是产品核心质量问题，不是"能不能做"的问题 | 高（但性质不同） |

前两项可以实机验证；第三项属于调优范畴，需要真实语料反复打磨。

---

## 六、阶段总结

到这里，**"能不能做"这个问题已经有答案了：能做。**

三个原本的致命未知：

1. ~~英文模式下 Lua 能否介入~~ → 能（验证 01）
2. ~~发行版是否带 Lua~~ → 带（验证 02）
3. ~~前端是否显示候选窗~~ → 显示（验证 02）

**全部通过静态分析排除。剩下的都是"做得好不好"的问题，不是"做不做得了"的问题。**

下一步该进入实机验证了——需要安装小狼毫。
