## Why

上次修复解决了结构性问题（标题、章节、场景标记），但实际生成的剧本仍有严重格式问题：LLM 在场景内容中自行生成标题和分隔符（`# 《赤色碎矿》第一幕·场景一`、`---`、`（第一幕·场景一完）`），角色名格式不统一（`**林辰**` vs `林辰`），空幕出现。更根本的是——剧本完全缺失角色的心理活动和内心深度，变成了只有对话和简单动作的"台词本"。

## What Changes

- **格式清理**：在 system prompt 中禁止 LLM 输出标题、分隔符、场景结束标记；PostProcessor 清理泄露的格式标记
- **角色名格式统一**：ZH 用 `林辰`（不加粗），EN 用 `LIN CHEN`（标准大写），PostProcessor 统一化
- **空幕处理**：ChapterPlanner 或 assemble 阶段检测空幕并移除
- **心理活动注入**：在 `_format_scene_log()` 中将角色的 inner_thought 格式化为"内心独白"提示，在 system prompt 中要求 LLM 将其转化为剧本中的（旁白）或（OS）或动作指示
- **场景标记统一**：PostProcessor 统一 `[场景] 地点 - 时间` 格式

## Capabilities

### Modified Capabilities

- `narrative-writer`: ScreenplayWriter 的 format_scene_log、system prompt、PostProcessor、assemble 流程进一步修复

## Impact

- `backend/app/services/narrative_writer.py`：约 30% 代码变更
