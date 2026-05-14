## Why

当前剧本导出与小说修复前存在完全相同的结构缺陷：标题硬编码为 "剧本" / "SCREENPLAY"，无场次编号，场景标记格式不统一（混用 `[内景]`/`EXT.`/`内景.`），角色名有时变成英文大写（`LIN CHEN`），6 场戏简单罗列无幕间结构。小说已通过 `fix-narrative-output-quality` 完成修复，剧本需要同样的改造。

## What Changes

- **复用 TitleGenerator**：小说已有的标题生成逻辑直接用于剧本标题生成（备选剧名）
- **新增场次编号**：每场标记为 "第一场" / "Scene 1"
- **统一场景标记格式**：ZH一律 `[内景]`/`[外景]` + 地点 + 时间，EN 一律 `[INT.]`/`[EXT.]` + Location + Time
- **强制角色名格式**：始终使用原始中文名（或原始英文名），禁止 LLM 自行转换为大写英文
- **重建编剧 system prompt**：参考用户提供的编剧 prompt 结构——先构思角色/背景/对白→再创作充满转折的情节→保持悬念到结局
- **按章/幕组织**：复用 ChapterPlanner 的思路，将场景按叙事弧分组为幕（三幕或四幕）
- **i18n 静态文本**：移除所有硬编码（"剧本"/"SCREENPLAY" 等）

## Capabilities

### Modified Capabilities

- `narrative-writer`: 剧本导出逻辑完全重构——新增场次编号、格式统一、幕结构、编剧 prompt 重建。现有逐场景转换+硬编码标题的行为被替换。

## Impact

- `backend/app/services/narrative_writer.py`：ScreenplayWriter 核心重写，约 40% 代码变更
- `backend/app/core/i18n.py`：新增剧本相关翻译条目
- 不影响小说导出逻辑（NovelWriter 不变）
