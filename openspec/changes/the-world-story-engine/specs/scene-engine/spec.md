## ADDED Requirements

### Requirement: Scene Setup
系统 SHALL 在每场戏开始前由 Director 完成场景设置，包括地点选择、场景描写、角色召集和目标分配。

#### Scenario: Director sets up a scene
- **WHEN** 用户启动一场新场景（或系统按剧情大纲自动推进）
- **THEN** Director 从剧情大纲中读取本场目标
- **AND** Director 选择地点，生成场景描写（时间、天气、氛围）
- **AND** Director 选择在场角色并设定各角色的"本场目标"（仅角色自己知道）
- **AND** Director 设定本场的"隐藏信息"（哪些角色拥有其他人不知道的信息）
- **AND** Director 注入至少一个"潜在冲突源"
- **AND** Director 设定场景结束条件

#### Scenario: User manually adjusts scene setup
- **WHEN** 用户在 Director 完成设置后调整场景参数
- **THEN** 系统接受用户的修改（增加/移除角色、更改地点、调整目标）
- **AND** Director 基于修改后的参数重新评估冲突源和结束条件

### Requirement: Interaction Loop - Environment Perception
系统 SHALL 在每轮交互开始时由 Environment Agent 更新当前场景的环境状态。

#### Scenario: Environment agent describes current atmosphere
- **WHEN** 新的一轮交互开始
- **THEN** Environment Agent 生成当前环境更新（光线变化、天气、背景声音、路人活动等）
- **AND** 环境描述注入到所有在场角色的场景上下文中
- **AND** 若环境发生变化（如"窗外开始下雨"），变化也被注入

### Requirement: Interaction Loop - Active Character Selection
系统 SHALL 在每轮交互中由 Director 选择本轮的"主动角色"。

#### Scenario: Director selects speaker based on context
- **WHEN** 上一轮交互完成
- **THEN** Director 评估当前局势（谁刚被 cue？冲突在哪？谁的动机最强？）
- **AND** Director 选定 1 个主动角色作为本轮行动者
- **AND** 若对话僵持超过 2 轮，Director 优先选择立场对立的角色打破沉默

#### Scenario: Director injects external event
- **WHEN** Director 判断冲突升级不足或对话陷入循环
- **THEN** Director 可注入外部事件（敲门声、消息到达、意外人物登场）
- **AND** 外部事件作为场景上下文注入给所有在场角色

### Requirement: Interaction Loop - Action Generation
系统 SHALL 为选定的主动角色组装上下文并通过 LLM 生成行动（对话 + 动作 + 内心活动）。

#### Scenario: Character generates action
- **WHEN** 主动角色被选中
- **THEN** 系统为该角色组装上下文：
  - L0：核心身份 + 当前目标 + 当前情绪
  - L1：完整性格 + 在场角色关系详情 + 近期 3-5 场场景完整记忆
  - 场景层：场景描写 + 在场角色最近发言 + 本场目标
- **AND** 角色上下文包含其"隐藏信息"（只有该角色知道的事）
- **AND** LLM 以 JSON 格式返回：对话内容、身体动作、内心活动、情绪状态
- **AND** 角色的行动基于其自身认知而非全知视角

#### Scenario: Character action respects knowledge boundaries
- **WHEN** 角色 A 不知道角色 B 的秘密身份
- **THEN** 角色 A 的行动中不包含对该秘密的认知
- **AND** 若 Director 判定角色 A 的回应中隐含了不应知道的信息，标记为轻微 OOC 并记录

### Requirement: Interaction Loop - Reaction Generation
系统 SHALL 在被主动角色行动影响后，并行生成其他在场角色的反应。

#### Scenario: Multiple characters react to action
- **WHEN** 主动角色完成行动（如"主角对李四说了挑衅的话"）
- **THEN** Director 判断哪些角色需要回应（被直接对话→必须回应，被动作影响→可能需要回应，旁观者→内心反应）
- **AND** 需要回应的角色并行生成各自的反应
- **AND** Director 合并所有反应，检查一致性

#### Scenario: Parallel reaction generation
- **WHEN** 3 个角色需要同时回应
- **THEN** 系统使用 asyncio.gather() 并行调用 LLM
- **AND** 每个角色的上下文包含其他角色的最近行动
- **AND** 在合理超时（30 秒）内返回所有结果

### Requirement: Interaction Loop - Director Adjudication
系统 SHALL 在每轮交互结束后由 Director 评估当前场景状态并做出裁决。

#### Scenario: Director evaluates round
- **WHEN** 一轮交互（行动 + 反应）完成
- **THEN** Director 评估：冲突是否进化、角色是否 OOC、节奏是否合理
- **AND** 若角色轻微 OOC，Director 可选择重试该角色的行动
- **AND** 若冲突不足，Director 在下轮或注入意外事件或选择对立角色
- **AND** 若节奏太快，Director 下轮优先环境描写放慢
- **AND** 若节奏太慢，Director 注入意外事件加速

#### Scenario: Director ends scene
- **WHEN** 场景结束条件触发（关键信息已揭露 / 情绪高潮已过 / 角色离场）
- **THEN** Director 判定场景结束
- **AND** 触发 Scene Resolution 流程

### Requirement: Scene Resolution
系统 SHALL 在每场场景结束后执行记忆更新和状态归档。

#### Scenario: Character memory update after scene
- **WHEN** 场景结束
- **THEN** 系统为每个参与角色独立生成记忆更新：
  - 本场经历摘要→L0（如情绪/目标有重大变化）
  - 详细经历+情绪变化→L1
  - 完整交互记录→L2
  - 关系变化→更新 Kuzu 图
- **AND** 记忆更新写入 OpenViking

#### Scenario: World state update after scene
- **WHEN** 场景结束
- **THEN** 系统更新世界状态：地点变化（如"酒馆被打烂了"）、物品转移、新事件加入时间线
- **AND** 写入 OpenViking 世界状态目录

#### Scenario: Narrative log archiving
- **WHEN** 场景结束
- **THEN** 系统将完整的原始交互 JSON 日志归档
- **AND** 日志包含所有轮次、所有角色的行动/反应、Director 裁决记录
- **AND** 作为 Narrative Writer 的输入源

### Requirement: Information Asymmetry Management
系统 SHALL 由 Director 维护角色间的信息不对称矩阵，确保每个角色仅基于自身认知行动。

#### Scenario: Director maintains knowledge matrix
- **WHEN** 场景中存在秘密或隐藏信息
- **THEN** Director 维护"谁知道什么"矩阵
- **AND** 在组装角色上下文时，仅注入该角色有权知道的信息
- **AND** 当某个角色的信息被揭露给其他角色时，Director 更新矩阵
