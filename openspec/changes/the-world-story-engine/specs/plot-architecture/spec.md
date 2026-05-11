## ADDED Requirements

### Requirement: Narrative Structure Templates
系统 SHALL 支持多种叙事结构模板，用户可选择模板作为剧情架构的骨架。

#### Scenario: User selects narrative structure
- **WHEN** 用户进入剧情架构阶段
- **THEN** 系统提供叙事结构选项：三幕结构、英雄之旅（12步）、Save the Cat（15拍）、起承转合
- **AND** 展示每种结构的简要说明和适用场景

#### Scenario: Plot generated from structure and characters
- **WHEN** 用户选择叙事结构并确认
- **THEN** LLM 基于世界观、角色群和所选结构生成完整剧情大纲
- **AND** 大纲包含幕/步/拍级别的节点，每个节点标注核心冲突和关键角色

### Requirement: Scene Outline Generation
系统 SHALL 将剧情大纲细化为分场大纲，每场包含地点、角色、冲突目标和预期结果。

#### Scenario: Generate scene outline
- **WHEN** 用户确认剧情大纲
- **THEN** 系统将大纲拆解为具体的场景列表
- **AND** 每个场景包含：场景名称、地点、在场角色、冲突描述、预期结果、与前后场景的因果链
- **AND** 用户可拖拽调整场景顺序

#### Scenario: User adds custom scene
- **WHEN** 用户手动在剧情大纲中插入新场景
- **THEN** 系统分析插入位置的上下文，建议该场景的内容方向
- **AND** 用户填写场景目标后系统自动检查与前后场景的逻辑一致性

#### Scenario: User deletes a scene
- **WHEN** 用户删除某个场景
- **THEN** 系统检查该场景是否承载关键剧情信息
- **AND** 若承载关键信息，提示用户该信息将在何处重新安置

### Requirement: Plot-Scene Consistency Check
系统 SHALL 在场景执行前检查场景目标与整体剧情大纲的一致性。

#### Scenario: Scene goal conflicts with plot arc
- **WHEN** 某场景的目标与角色弧光规划发生冲突
- **THEN** 系统通过 Story Guardian 标记冲突
- **AND** 提供调整建议
