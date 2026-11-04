# 验证 01：能否用纯 Lua 实现「英文模式下打出中文候选」

- 验证日期：2026-11-01
- 验证方式：静态代码分析（未安装任何软件，未改动机器）
- 代码来源：`librime` 与 `librime-lua` 官方仓库最新 master
- 验证人：WorkBuddy

---

## 一、结论（先说结果）

**能。功能一的核心能力可以只用 Lua 实现，不需要修改 C++。**

原本最担心的是「英文模式下按键被处理器直接吞掉，Lua 根本插不进手」。
读完源码后确认：**英文模式下按键并没有直接上屏，而是进入了输入缓冲区，并且会走完整的切分与翻译流程**，所以 Lua 翻译器有机会产出中文候选。

这一条如果成立，整个项目的工期从「3–6 个月」降到「4–8 周」的量级，因为不需要碰 librime 的 C++ 内核。

但有两个新发现的坑，见第三节。另有三项风险尚未验证，见第四节。

---

## 二、证据链

整条链路有五个环节，逐个确认：

### 1. 英文模式下，字母进入输入缓冲，而不是直接上屏

`librime/src/rime/gear/ascii_composer.cc` 第 253–255 行：

```cpp
if (ascii_mode && ctx->IsComposing()) {
  ctx->PushInput(ch);   // 推入输入缓冲
  return kAccepted;
}
```

关键在于 `PushInput`，不是 `Commit`。输入被推进了 context，后面还会被处理。

### 2. 英文输入会被切分成一个带 `raw` 标签的段

`librime/src/rime/gear/ascii_segmentor.cc`：

```cpp
if (!engine_->context()->get_option("ascii_mode"))
  return true;
...
Segment segment(j, input.length());
segment.tags.insert("raw");     // 英文段的标签是 raw
segmentation->AddSegment(segment);
```

只要处于英文模式且有输入，就一定会生成一个段。

### 3. 翻译阶段遍历所有翻译器，不按标签过滤

`librime/src/rime/engine.cc`，`ConcreteEngine::TranslateSegments`：

```cpp
for (auto& entry : translators_) {
  if (!entry.enabled) continue;
  auto translation = entry.component->Query(input, segment);
  ...
}
```

注意：这里**只检查组件是否启用（enabled），没有做任何 tag 匹配**。是否响应某个段，由翻译器自己决定。

### 4. Lua 翻译器不做标签判断，对任何段都响应

`librime-lua/src/lua_gears.h` 中 `LuaTranslator` 直接继承 `Translator`，**没有继承 `TagMatching`**。
对比同目录的 `LuaFilter` 是 `class LuaFilter : public Filter, TagMatching`——过滤器有标签限制，翻译器没有。

所以只要在方案配置里挂上 `lua_translator`，它在 `raw` 段上也会被调用。

### 5. 反向佐证：`echo_translator` 正在这条路上工作

`librime/src/rime/gear/echo_translator.cc`：

```cpp
an<Translation> EchoTranslator::Query(const string& input, const Segment& segment) {
  if (input.empty()) return nullptr;
  auto candidate = New<SimpleCandidate>("raw", segment.start, segment.end, input);
  candidate->set_quality(-100);  // 最低优先级
  return New<EchoTranslation>(candidate);
}
```

它对任何输入都返回「原文」候选，无任何标签限制——**这证明英文段确实会被翻译**，否则英文模式下候选栏里那句原文根本出不来。

同时 `quality = -100` 是个好消息：原文候选天然排最后，中文候选会自然排在它前面，排序不用额外处理。

### 6. 补充发现：Lua 还能接管处理器层

`librime-lua/src/modules.cc` 第 102–105 行，比预期多注册了一种组件：

```cpp
r.Register("lua_translator",  new LuaComponent<LuaTranslator>(lua));
r.Register("lua_filter",      new LuaComponent<LuaFilter>(lua));
r.Register("lua_segmentor",   new LuaComponent<LuaSegmentor>(lua));
r.Register("lua_processor",   new LuaComponent<LuaProcessor>(lua));  // 超出预期
```

`LuaProcessor` 能收到原始按键事件并返回「已处理 / 未处理」，这对绕开下面第一个坑很关键。

---

## 三、新发现的两个坑

### 坑 1：英文模式下数字键被当成文字，选不了候选

`ascii_composer.cc` 第 248 行：

```cpp
if (ch >= 0x20 && ch <= 0x7e) {   // 数字 1-9 也在这个范围内
  raw_keys_.push_back(static_cast<char>(ch));
  if (ascii_mode && ctx->IsComposing()) {
    ctx->PushInput(ch);           // 数字被当字符打进去了
    return kAccepted;
  }
  ...
}
```

后果：英文模式下按 `2` 不会选中第二个候选，而是往输入里加一个字符 `2`。

**影响**：功能一不能靠数字键选中文候选。
**候选解法**（择一，待实测）：
- 用 `lua_processor` 前置拦截数字键，命中候选时改成「选择第 N 项」
- 用 `key_binder` 把某个非字符键（如 Tab）映射成「选第 2 候选」
- 改用方向键移动光标选择

### 坑 2：英文模式下空格直接上屏原文

`ascii_composer.cc` 第 214–216 行：

```cpp
if (ch == XK_space && key_event.modifier() == 0) {
  CommitAndReset(ctx->input() + " ");
  return kAccepted;
}
```

空格会直接 commit 原文，不经过候选选择。

**这其实是好事**——用户在英文模式下按空格，本来就想打英文，行为完全符合预期。但它限制了交互设计：**「转中文」必须绑定到另一个键**，不能复用空格。

---

## 四、还没验证的风险

以下三项**静态分析看不出来，必须真机跑**：

| 风险 | 说明 | 影响程度 |
|---|---|---|
| 发行版是否启用 Lua 模块 | 小狼毫的 Windows 安装包不一定编译了 `librime-lua`，需要实际确认 | **致命**：没编就全盘不通 |
| Weasel 前端是否显示候选窗 | 引擎层产出了候选，但 Weasel 的 UI 在英文模式下可能根本不弹窗 | **高**：能算不能显示等于零 |
| 性能 | 每次按键都会跑一遍 Lua 翻译器，长输入可能掉帧 | 中：影响手感 |

其中第二项是本次分析暴露出的**新风险点**，之前没考虑到。它意味着即使引擎层通了，前端 UI 层还有一道关。

---

## 五、下一步

按顺序做，每步都是是非题：

1. **确认小狼毫发行版是否带 Lua**——查安装包文件列表，看有没有 `librime-lua.dll`，或看官方更新日志
2. **确认 Weasel 在 `raw` 段下是否显示候选窗**——需要读 Weasel 源码或实机验证
3. **真机跑最小样例**——写一个「把输入原样加括号」的 lua_translator，验证链路通了
4. **再验证数字键绕行方案**

第 1、2 步仍然可以纯静态完成，不用装东西。

---

## 六、一句话总结

功能一的技术风险，从「可能要改 C++ 内核」降级为「纯配置 + Lua 脚本，但要绕开数字键和前端 UI 两道关」。
**项目可行性显著上升，最大的不确定性已经从「能不能做」转移到「做出来准不准」。**
