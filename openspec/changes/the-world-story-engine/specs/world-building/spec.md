## ADDED Requirements

### Requirement: Conversational World Building
系统 SHALL 通过 LLM 递进式对话引导用户从简单 idea 逐步构建完整世界观，涵盖规则体系、地理地点、历史时间线、势力派系等维度。

#### Scenario: User starts world building from idea
- **WHEN** 用户输入初始 idea（如"修仙+科技共存的世界"）
- **THEN** 系统分析 idea 中的核心概念，提出引导性问题帮助用户展开世界观设定
- **AND** 每轮对话后结构化提取用户的输入，存入 OpenViking

#### Scenario: User skips a dimension
- **WHEN** 用户在某个世界构建维度表示"暂时跳过"或"不确定"
- **THEN** 系统标记该维度为未填充，记录到待完善列表
- **AND** 用户可在后续任意时刻回到该维度补充

#### Scenario: World building reaches minimum completeness
- **WHEN** 核心维度（规则体系、主要地点、关键势力）均已填充
- **THEN** 系统提示世界构建阶段可进入下一步（角色生成）
- **AND** 用户可选择继续完善或进入下一步

### Requirement: Document Upload and Parsing
系统 SHALL 支持用户上传已有的世界观设定文档或小说/剧本草稿，通过 LLM 自动解析为结构化世界观数据，并展示给用户二次编辑确认。

#### Scenario: User uploads world setting document
- **WHEN** 用户上传包含世界观设定的文档（如"灵力分为金木水火土五行…"）
- **THEN** 系统解析文档内容，提取规则体系、地点、势力、历史事件等结构化信息
- **AND** 以分类卡片形式展示解析结果
- **AND** 用户可逐条编辑、删除、补充

#### Scenario: User uploads novel draft
- **WHEN** 用户上传已完成部分章节的小说草稿
- **THEN** 系统从草稿中提取已有角色、世界观设定、剧情进度
- **AND** 将提取内容作为世界构建的初始数据
- **AND** 用户可确认或修改提取结果

#### Scenario: Unsupported file format
- **WHEN** 用户上传系统不支持的格式文件
- **THEN** 系统返回错误提示，说明支持的格式列表

### Requirement: World Data Structure
系统 SHALL 将构建完成的世界观以结构化数据存储到 OpenViking 的文件系统层级中。

#### Scenario: World data stored after building
- **WHEN** 用户完成世界构建（或确认解析结果）
- **THEN** 世界观数据按以下结构存储：
  - `viking://world/rules/` — 规则体系（物理/魔法/修炼等）
  - `viking://world/locations/` — 地理地点详情
  - `viking://world/factions/` — 势力/派系信息
  - `viking://world/timeline/` — 历史事件时间线
- **AND** 每条数据有完整内容 + L0 摘要 + L1 概览
