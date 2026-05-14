## Context

读取实际生成的剧本输出后发现 6 个格式问题和 1 个内容缺陷。问题根源在于 system prompt 禁止不够强 + `_format_scene_log` 未充分传递内心独白信息。

## Goals / Non-Goals

**Goals:**
- 清除 LLM 自行生成的标题、分隔符、场景结束标记
- 角色名格式统一（ZH 不加粗纯中文名，EN 大写）
- 移除空幕
- 内心独白（`inner_thought`）转化为剧本中的（旁白）/（OS）/ 动作指示
- 场景标记统一格式

**Non-Goals:**
- 不改 Scene Engine 输出格式
- 不改变小说输出逻辑

## Decisions

### 1. 禁止 LLM 生成结构性标记

**问题**: LLM 生成 `# 《赤色碎矿》第一幕·场景一`、`---`、`（第一幕·场景一完）`

**解决**: 在 system prompt 中加硬性禁止规则：
- "不要添加任何标题（#、##）"
- "不要添加分隔线（---）"  
- "不要添加场景结束标记（如"第一幕·场景一完"）"
- "代码会自动添加所有章节和场次标记"

PostProcessor 增加清理：移除行首 `#` 标题、移除独立 `---` 行。

### 2. 角色名格式

**ZH**: 统一用纯角色名（如 `林辰`），不加粗，不用 markdown
**EN**: 标准剧本大写（`LIN CHEN`）

system prompt 规定 + PostProcessor 移除 `**` 加粗。

### 3. 内心独白注入

**问题**: `_format_scene_log()` 输出了 `Thinks: xxx`，但 LLM 不知道如何转化为剧本格式

**解决**: 
1. `_format_scene_log()` 中将 `inner_thought` 格式化为更明确的提示：
   `[内心] 角色名心想：xxx`
2. system prompt 加规则："将 [内心] 标记的内容转化为剧本中的旁白（OS）、画外音或括弧动作指示"
3. 不强求每个 inner_thought 都转为 OS，灵活处理

### 4. 空幕移除

`_assemble_screenplay()` 中检测空幕（该幕下无任何场景），跳过不输出。

## Risks / Trade-offs

- 禁止项太多可能导致 LLM 输出过于机械 → 平衡点在 prompt 中用"禁止"而非"惩罚"
