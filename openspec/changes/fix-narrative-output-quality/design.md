## Context

当前 NarrativeWriter 存在三个结构问题：

1. **无标题生成**：`_assemble_novel()` 使用硬编码 `"Generated Narrative"` 作为标题，LLM 从未被要求根据故事内容生成书名
2. **无章回结构**：`"Part I"` / `"Chapter N"` 硬编码为英文，中文小说需要的章回体（第X章 ××篇名）完全缺失
3. **逐场景机械拼接**：每个场景独立调用 LLM 转为散文，然后简单拼接——缺乏跨场景的叙事连贯性、章节整体感

用户明确反馈："小说名字、章节回数还是英文"，"生成的小说质量很糟糕"。

## Goals / Non-Goals

**Goals:**
- 小说标题由 LLM 根据世界+角色+剧情自动生成（中文模式下生成中文书名）
- 章节结构由 LLM 规划：场景→章节的映射、每章标题
- 写作品质从逐场景翻译升级为逐章统一写作
- 所有静态文本通过 i18n 输出
- 中文小说输出符合章回体惯例

**Non-Goals:**
- 不改变 SceneEngine 产出（场景日志格式不变）
- 不改变 WorldBuilder/CharacterManager/PlotArchitect 接口
- 不添加 AI 校对/事实核查
- 不做封面/排版美化（那是前端的事）

## Decisions

### 1. 新增 TitleGenerator（独立类）

**选择**：在 NarrativeWriter 内部新增 `TitleGenerator` 类
**理由**：标题生成逻辑足够独立，值得单独一个类。输入世界摘要+角色摘要+剧情大纲，输出 3-5 个备选书名。

**标题生成 Prompt 规则**：
- ZH 模式：生成纯中文书名，风格参考金庸/古龙/网络文学命名惯例
- EN 模式：生成英文书名
- 至少包含 3 个风格各异的备选（如：诗意型、悬念型、直白型）

### 2. 新增 ChapterPlanner（独立类）

**选择**：新增 `ChapterPlanner`，由 LLM 规划场景→章节映射
**理由**：场景数量（10-15 场）和章节数量（3-5 章）不同层级，需要 PLANNING 而非机械分组。

**章节规划输出**：
```python
@dataclass
class ChapterPlan:
    chapters: list[ChapterSpec]

@dataclass 
class ChapterSpec:
    number: int
    title: str  # 中文: "第一章 青云城之约", EN: "Chapter 1: The Pact"
    scene_ids: list[str]  # 属于此章的 2-4 个场景
    summary: str  # 本章概要
```

**中文章节标题规则**：
- 使用 "第X章" 形式（不用"第X回"——后者是章回体专用，不适合现代小说）
- 每章有文学性篇名

### 3. 章节字数控制

**选择**：ChapterPlanner 和 LLM 写作 prompt 共同控制章节字数

真实小说一章的字数：
- 中文：2000-5000 字/章
- 英文：1500-4000 词/章

控制机制：

1. **ChapterPlanner 阶段**：根据场景预估产出字数（每场景约 800-1500 中文字/500-1000 英文词），计算需要多少场景才能达到目标章字数。若场景不足，在规划中注明"本章需扩展描写"。

2. **写作 prompt 阶段**：LLM 收到目标字数范围，在 `<story>` 中输出时自行控制篇幅：
   - 中文：2500-4000 字/章
   - 英文：2000-3500 词/章
   - prompt 中明确说明："本章目标字数为 2500-4000 字。请充分展开描写、内心独白、环境渲染以达到目标字数。"

3. **字数不足处理**：若全篇场景少于 3 场且每场轮数少（短篇），则放宽字数要求（800-1500 字也可成章，标记为"短篇"模式）。

### 4. 逐章写作替代逐场景写作

**选择**：改为逐章调用 LLM——一次性传入整章所有场景日志+章节标题+前后章节摘要，LLM 统一写出整章散文

**对比**：

| 维度 | 旧：逐场景 | 新：逐章节 |
|------|----------|----------|
| LLM 调用次数 | N 次（每场景一次） | M 次（每章一次，M≈N/3） |
| 叙事连贯性 | 无（各场景独立） | 强（LLM 看到完整章结构） |
| 章节转场 | 无 | LLM 在场景间写过渡段落 |
| 章节内统一感 | 断裂 | 连贯 |
| Token 消耗 | 每场景 4-6K | 每章 15-25K（3-4 场景） |

**章内写作 Prompt 规则**：
- LLM 收到：章节标题 + 章摘要 + 本章所有场景的日志 + 前后章摘要（如有）
- LLM 输出：完整章散文，含场景间过渡段落
- 保留所有原始对话和关键动作
- 可在场景间添加叙事桥梁（一两段过渡描写）

### 5. 组装流程重建

```
旧流程:                         新流程:
scene logs                      scene logs
  │                               │
  ├─ LLM → prose_1               ├─ TitleGenerator → 3-5 备选书名
  ├─ LLM → prose_2               ├─ ChapterPlanner → 章节规划
  ├─ LLM → prose_3               │    chap_1: [scene_1, scene_2]
  │                               │    chap_2: [scene_3, scene_4, scene_5]
  └─ assemble(proses)            │    chap_3: [scene_6, scene_7]
     # Generated Narrative       │
     ## Part I                   ├─ LLM → chap_1 完整散文
     [prose_1]                   ├─ LLM → chap_2 完整散文
     ## Chapter 2                ├─ LLM → chap_3 完整散文
     [prose_2]                   │
                                  └─ assemble(chaps, title)
     # 灵石垄断：青云劫
     第一章 矿道血盟
     [chap_1 完整散文，2500-4000字]
     第二章 黑市暗涌
     [chap_2 完整散文，2500-4000字]
```

### 6. i18n 静态文本

所有硬编码英文文本改为 i18n 调用：
- `"Generated Narrative"` → `t("writer.default_title")`
- `"Chapter N"` / `"Part I"` → 通过章节标题直接使用 LLM 生成的标题（不再需要 i18n 占位）
- `"SCREENPLAY"` → `t("writer.default_screenplay_title")`
- 章节标记 `"第{n}章"` / `"第{n}回"` → 由 ChapterPlanner 直接输出本地化标题

## Risks / Trade-offs

- **[R1] 逐章写作 Token 消耗增加** → 单章 15-25K tokens vs 旧方式单场景 4-6K。但章数远少于场景数，总消耗相近（甚至因减少 LLM 调用次数而降低）
- **[R2] 长章节可能超出 LLM 注意力** → 限制每章最多 4 个场景，约 25K tokens 输入（DeepSeek 1M 窗口绰绰有余）
- **[R3] 章节标题可能不够好** → 用户可在前端编辑章节标题（后续 Phase 11 实现）

## Open Questions

- 字数不足的短篇是否应该合成单章（不分章），还是仍然按场景分成多个小章？建议短篇合成单章，中长篇按字数分章。
