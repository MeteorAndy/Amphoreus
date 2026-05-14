## MODIFIED Requirements

### Requirement: Scene Log to Screenplay Conversion
系统 SHALL 将场景交互的原始日志转换为格式统一、具有角色心理深度的完整剧本体文本。

#### Scenario: No structural markers in scene content
- **WHEN** LLM 生成单个场景的剧本内容
- **THEN** 场景内容中 SHALL NOT 包含标题（#、##）、分隔线（---）、场景结束标记
- **AND** 这些结构性标记由代码在 assembly 阶段统一添加
- **AND** PostProcessor SHALL 清除泄露的标题、分隔线、结束标记

#### Scenario: Character name format — Chinese
- **WHEN** 当前语言为中文且生成剧本
- **THEN** 角色名 SHALL 为纯中文文本（如 `林辰`），不加粗、不用 markdown 格式
- **AND** PostProcessor SHALL 移除角色名的 `**` 加粗标记

#### Scenario: Character name format — English  
- **WHEN** 当前语言为英文且生成剧本
- **THEN** 角色名 SHALL 为标准剧本大写（如 `LIN CHEN`）

#### Scenario: Empty act removal
- **WHEN** 某个幕下没有任何场景归档
- **THEN** assembly 阶段 SHALL 跳过该幕，不输出空的幕标题

### Requirement: Output Quality Enhancement
系统 SHALL 将角色内心独白转化为剧本中的心理深度表现。

#### Scenario: Inner thought conversion
- **WHEN** 场景日志中包含角色的 `inner_thought` 数据
- **THEN** `_format_scene_log()` SHALL 将其格式化为明确的 `[内心]` 标记
- **AND** system prompt SHALL 要求 LLM 将 `[内心]` 转化为：（旁白）、（OS）、画外音、或括弧动作指示
- **AND** 保留原对话和关键动作不变

## ADDED Requirements

### Requirement: Screenplay content sanitization  
系统 SHALL 在后处理阶段清理 LLM 生成的非法结构性标记。

#### Scenario: Remove leaked headings
- **WHEN** 场景内容中出现以 `#` 开头的行
- **THEN** PostProcessor SHALL 移除该行（因其与代码生成的标题冲突）

#### Scenario: Remove leaked separators
- **WHEN** 场景内容中出现独立的 `---` 行
- **THEN** PostProcessor SHALL 移除该行

#### Scenario: Remove scene-end markers
- **WHEN** 场景内容中出现中文场景结束标记（如 `（第一幕·场景一完）`）
- **THEN** PostProcessor SHALL 移除该行
