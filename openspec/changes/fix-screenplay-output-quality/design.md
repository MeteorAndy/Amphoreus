## Context

当前 `ScreenplayWriter` 存在格式和结构问题，与 `fix-narrative-output-quality` 中修复的小说导出问题完全同源。TitleGenerator 和 ChapterPlanner 已在小说修复中实现，可直接复用。更改集中在 `ScreenplayWriter` 和剧本组装流程。

## Goals / Non-Goals

**Goals:**
- 剧本标题由 LLM 生成（复用 TitleGenerator）
- 每场有统一编号：ZH "第X场"、EN "Scene X"
- 场景标记格式统一：ZH `[内景] 地点 - 时间`、EN `[INT.] Location - Time`
- 角色名始终保留原始语言形式
- 按幕组织场景（使用 ChapterPlanner 的思路）
- 编剧 system prompt 重建：先构思角色/对白→再创作悬念情节
- 所有静态文本通过 i18n 输出

**Non-Goals:**
- 不修改 TitleGenerator / ChapterPlanner / PostProcessor（已可用）
- 不改变 SceneEngine 输出
- 不生成分镜头脚本（那是电影制作的事）

## Decisions

### 1. 复用 TitleGenerator

小说和剧本共用同一套标题生成逻辑。`NarrativeWriter.convert()` 已统一调用 TitleGenerator，无论 format 是 novel 还是 screenplay。无需改动。

### 2. 场景标记统一

**问题**：LLM 自由发挥导致同一份剧本出现 `[内景]`、`EXT.`、`内景.`、`[INT.]` 多种格式。

**解决**：在 system prompt 中给出唯一正确格式，并在 PostProcessor 中添加场景标记规范化。

| 语言 | 内景 | 外景 | 格式 |
|------|------|------|------|
| ZH | `[内景]` | `[外景]` | `[内景] 地点名称 - 时间` |
| EN | `[INT.]` | `[EXT.]` | `[INT.] Location Name - Time` |

### 3. 角色名格式强制

**问题**：LLM 有时将中文角色名转为大写英文（`LIN CHEN`、`SU WANQING`）。

**解决**：在 system prompt 中明确："角色名必须使用原始语言的原始写法。中文名保持中文，不得转换为拼音或英文大写。" PostProcessor 中检测并修复。

### 4. 场次编号

每场自动标注编号：

```
第一场                              Scene 1
[内景] 老陈杂货铺 - 夜               [INT.] Old Chen's Shop - Night
...
                                     ...
第二场                              Scene 2
[内景] 灵石巷 - 夜                    [INT.] Spirit Stone Alley - Night
```

### 5. 幕结构

使用 ChapterPlanner 的思路将场景分组为幕。剧本通常 3-4 幕：
- 第一幕：建置（setup）
- 第二幕：对抗（confrontation） 
- 第三幕：高潮+解决（climax + resolution）

### 6. 编剧 System Prompt 重建

参考用户提供的 prompt，重构为两步结构：
1. **角色与场景构思**：LLM 先审视所有场景中的角色动机、关系、背景
2. **情节创作**：将这些场景编织成充满转折与悬念的剧本
3. 在 `<剧本>` 标签中输出完整剧本

## Risks / Trade-offs

- **[R1] 场景标记在 LLM 输出中仍可能不一致** → PostProcessor 用正则检测 `[内]`/`[外]`/`[INT]`/`[EXT]` 模式并统一
- **[R2] 短剧本（<3场）幕结构可能尴尬** → 3 场以下合并为单幕，不强制分幕

## Open Questions

- 是否需要生成角色登场表（dramatis personae）？建议作为可选项，默认生成简要角色表放在标题页后
