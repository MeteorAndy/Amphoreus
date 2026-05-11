## ADDED Requirements

### Requirement: Character Consistency Validation
系统 SHALL 在用户干预剧情走向时校验干预内容与受影响角色的核心人设是否一致。

#### Scenario: User proposes character-breaking action
- **WHEN** 用户安排"复仇驱动的反派突然无条件原谅所有人"
- **THEN** Guardian 加载该反派的核心欲望（复仇）和性格档案
- **AND** 判定该安排与角色核心欲望根本冲突
- **AND** 返回 CRITICAL 级别拒绝 + 修改建议（如"需要先安排一个动摇其复仇信念的事件"）

#### Scenario: User proposes consistent action
- **WHEN** 用户安排符合角色人设的剧情
- **THEN** Guardian 返回 APPROVED，不阻塞执行

### Requirement: Relationship Logic Validation
系统 SHALL 校验用户干预中涉及的角色互动是否与角色间的关系历史一致。

#### Scenario: Characters trust without foundation
- **WHEN** 用户安排"主角将秘密告诉曾3次背叛自己的角色"
- **THEN** Guardian 从 Kuzu 加载两人的关系历史
- **AND** 检测到关系强度不足以支持此行为
- **AND** 返回 WARNING 级别警告 + 关系历史摘要

### Requirement: World Rules Compliance
系统 SHALL 校验用户安排的情节是否符合已建立的世界观规则。

#### Scenario: Action violates world rules
- **WHEN** 用户安排"凡人一拳击败元婴期修仙者"
- **THEN** Guardian 从 OpenViking 加载世界规则（修炼等级体系）
- **AND** 检测到该行为违反硬规则
- **AND** 返回 CRITICAL 级别拒绝 + 引用具体违规规则

#### Scenario: Action bends soft rules with explanation
- **WHEN** 用户安排的行为违反软规则但附带了合理情境说明
- **THEN** Guardian 判定情境是否充分支撑该例外
- **AND** 若充分则返回 APPROVED（附注：已记录该例外）
- **AND** 若不充分则返回 WARNING + 建议补充情境

### Requirement: Pacing Evaluation
系统 SHALL 评估用户安排的剧情节奏是否合理，识别过快或过慢的叙事节奏。

#### Scenario: Plot moves too fast
- **WHEN** 用户安排"角色初次见面→立刻结婚"
- **THEN** Guardian 检测到关系发展缺少中间场景
- **AND** 返回 WARNING 级别 + 建议插入 1-2 场过渡场景

#### Scenario: Healthy pacing
- **WHEN** 用户安排的剧情节奏合理
- **THEN** Guardian 不做节奏相关的阻塞

### Requirement: Character Arc Integrity Check
系统 SHALL 检查用户干预是否会破坏已规划的角色弧光。

#### Scenario: Intervention flattens character growth
- **WHEN** 用户安排"主角开局获得无敌力量"
- **THEN** Guardian 检查该安排与角色弧光规划的冲突
- **AND** 若检测到后续成长空间被破坏，返回 CRITICAL 级别拒绝
- **AND** 提供替代方案（如"可改为获得有限力量，仍有成长空间"）

### Requirement: Tiered Response System
系统 SHALL 按严重程度对校验结果进行分级响应。

#### Scenario: CRITICAL issue detected
- **WHEN** 检测到角色彻底 OOC 或世界观破坏
- **THEN** 硬拒绝执行，不允许用户绕过
- **AND** 返回具体冲突说明和修改建议

#### Scenario: WARNING issue detected
- **WHEN** 检测到节奏问题或关系逻辑存疑
- **THEN** 警告用户但不阻塞执行
- **AND** 用户可选择"忽略并继续"或"采纳建议修改"

#### Scenario: SUGGESTION only
- **WHEN** 检测到可以优化但不影响一致性的点
- **THEN** 以信息提示形式展示建议
- **AND** 不中断用户操作流程

### Requirement: Guardian Context Loading
系统 SHALL 在每次执行 Guardian 校验时加载所需的完整评估上下文。

#### Scenario: Guardian loads evaluation context
- **WHEN** 用户提交剧情干预
- **THEN** Guardian 加载：受影响角色的完整档案（OpenViking）、角色间关系网络（Kuzu）、相关世界观规则（OpenViking）、近期叙事历史（最近 5 场场景摘要）
- **AND** 逐维度执行评估
- **AND** 汇总结果并返回分级响应
