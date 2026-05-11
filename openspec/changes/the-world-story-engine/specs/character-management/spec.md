## ADDED Requirements

### Requirement: Character Group Generation
系统 SHALL 基于已构建的世界观，通过 LLM 生成完整的角色群，每个角色包含身份、性格、核心欲望、深层恐惧等维度。

#### Scenario: Generate characters from world
- **WHEN** 世界构建阶段完成，用户进入角色生成阶段
- **THEN** LLM 基于世界观建议 3-8 个关键角色
- **AND** 每个角色包含：姓名、身份、外貌、性格矩阵（Big5/MBTI）、核心欲望、深层恐惧、说话风格
- **AND** 用户可增删角色、修改任意属性

#### Scenario: Character backstory generation
- **WHEN** 用户确认角色基础信息
- **THEN** 系统为每个角色生成详细背景故事，包含重大人生事件、关键关系、隐藏秘密
- **AND** 回写关联到世界观时间线中的相关事件

### Requirement: Character Profile Management
系统 SHALL 将角色档案以结构化方式存储到 OpenViking，支持 L0/L1/L2 分层管理。

#### Scenario: Character profile stored in OpenViking
- **WHEN** 角色创建完成
- **THEN** 角色档案按以下结构存储：
  - `viking://chars/{id}/profile/identity` — L0 核心身份
  - `viking://chars/{id}/profile/personality` — L1 完整性格
  - `viking://chars/{id}/memories/backstory` — L2 完整背景
  - `viking://chars/{id}/arc/` — 角色弧光进度

### Requirement: Relationship Graph Management
系统 SHALL 使用 Kuzu 图数据库管理角色间的关系网络，支持查询角色间的直接和间接关系路径。

#### Scenario: Build relationship graph
- **WHEN** 角色群生成完成
- **THEN** 系统在 Kuzu 中创建 Character 节点和关系边（如师徒、敌对、暗恋、隶属）
- **AND** 每条关系包含属性：关系类型、强度、建立时间、关键事件

#### Scenario: Query relationship paths
- **WHEN** 用户（或 Story Guardian）查询"主角到反派之间的所有间接联系"
- **THEN** Kuzu 执行多跳路径查询，返回所有 1-3 跳关系链
- **AND** 结果以可视化图展示

#### Scenario: Relationship evolves after scene
- **WHEN** 一场场景结束，角色间关系发生变化
- **THEN** Kuzu 更新对应的关系边属性（强度变化、新增关系、关系解除）
- **AND** 记录关系变化历史（时间戳 + 触发事件）
