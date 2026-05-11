## ADDED Requirements

### Requirement: OpenViking Storage Hierarchy
系统 SHALL 使用 OpenViking 的文件系统范式管理所有结构化数据，按`viking://world/`、`viking://chars/`、`viking://story/`三级目录组织。

#### Scenario: World data stored in OpenViking
- **WHEN** 用户完成世界构建
- **THEN** 世界观数据存储为：
  - `viking://world/rules/{rule_name}` — 每条规则（含 L0 摘要 + L1 详解 + L2 完整内容）
  - `viking://world/locations/{location_name}` — 每个地点
  - `viking://world/factions/{faction_name}` — 每个势力
  - `viking://world/timeline/{event_name}` — 每个历史事件

#### Scenario: Character data stored in OpenViking
- **WHEN** 角色创建或更新
- **THEN** 角色数据存储为：
  - `viking://chars/{id}/profile/` — 身份、性格
  - `viking://chars/{id}/memories/` — 按时间线组织的记忆条目
  - `viking://chars/{id}/arc/` — 弧光规划与当前进度

### Requirement: L0/L1/L2 Tiered Memory
系统 SHALL 为每份记忆数据生成 L0（摘要层，~100 tokens）、L1（概览层，~2K tokens）、L2（完整内容）三层。

#### Scenario: Memory tiering on write
- **WHEN** 系统写入一条新记忆
- **THEN** 自动生成 L0 摘要（关键事实，用于快速筛选）
- **AND** 自动生成 L1 概览（结构化摘要，用于决策和规划）
- **AND** 保留 L2 完整内容（仅在需要时检索加载）

#### Scenario: Tiered loading during character action
- **WHEN** 为角色组装上下文
- **THEN** 角色的核心身份和目标从 L0 加载（始终在上下文）
- **AND** 关系详情和近期记忆从 L1 加载（场景级加载）
- **AND** 久远记忆和完整知识仅在检索触发时从 L2 按需加载

### Requirement: Kuzu Relationship Graph
系统 SHALL 使用 Kuzu 图数据库管理所有角色间关系、势力从属关系和事件因果链。

#### Scenario: Graph schema initialization
- **WHEN** 系统首次启动
- **THEN** Kuzu 数据库初始化以下节点表：Character、Location、Faction、Event
- **AND** 初始化以下关系边表：RELATES_TO（角色关系）、BELONGS_TO（势力从属）、LOCATED_AT（位置）、CAUSED_BY（事件因果）

#### Scenario: Multi-hop relationship query
- **WHEN** 系统查询"A 与 B 之间的所有间接关系（1-3跳）"
- **THEN** Kuzu 返回所有路径及每条边的属性（关系类型、强度、建立时间）
- **AND** 结果可用于 Guardian 校验和角色上下文组装

#### Scenario: Graph update after scene
- **WHEN** 场景结束时角色关系发生变化
- **THEN** Kuzu 更新对应关系边的属性
- **AND** 若产生新关系，创建新边
- **AND** 若关系解除，标记边的结束时间（软删除）

### Requirement: Memory Update Pipeline
系统 SHALL 在每场场景结束后自动执行角色记忆更新管道。

#### Scenario: Post-scene memory update
- **WHEN** 场景结束
- **THEN** 系统为每个参与角色调用 LLM 生成："这场戏中我经历了什么？学到了什么？情绪如何变化？对他人的看法改变了吗？"
- **AND** 将生成的更新写入 OpenViking 对应角色的 memories 目录
- **AND** 更新角色的 L0（如核心目标或情绪状态有重大变化）
- **AND** 将关系变化同步到 Kuzu

### Requirement: DuckDB-style Embedded Operation
系统 SHALL 确保 OpenViking 和 Kuzu 均以进程内嵌入模式运行，无需独立服务。

#### Scenario: Zero-configuration startup
- **WHEN** 系统启动
- **THEN** OpenViking 和 Kuzu 作为 Python 模块直接初始化
- **AND** 不需要额外启动数据库服务
- **AND** 数据文件存储在本地项目目录中
