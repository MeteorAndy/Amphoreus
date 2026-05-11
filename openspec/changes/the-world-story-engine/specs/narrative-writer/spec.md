## ADDED Requirements

### Requirement: Scene Log to Novel Conversion
系统 SHALL 将场景交互的原始日志转换为小说体叙事文本。

#### Scenario: Generate novel prose from scene log
- **WHEN** 一个或多个场景执行完成，用户请求输出小说体
- **THEN** Narrative Writer 读取场景原始日志（角色对话+动作+环境描写+内心活动）
- **AND** LLM 将日志转换为文学化的小说叙事，包含：描写性段落、对话、内心独白、叙述视角
- **AND** 保持原始场景中的关键对话和情节不变
- **AND** 输出可按章节/场景分段

#### Scenario: Narrative voice consistency
- **WHEN** 连续多个场景转换为小说体
- **THEN** Writer 保持一致的叙事语调（由用户在世界构建阶段或写作前选定）
- **AND** 若用户切换叙事视角（第一人称/第三人称有限/第三人称全知），全域统一应用

### Requirement: Scene Log to Screenplay Conversion
系统 SHALL 将场景交互的原始日志转换为剧本体文本。

#### Scenario: Generate screenplay from scene log
- **WHEN** 用户请求输出剧本体
- **THEN** Writer 将场景日志转换为标准剧本格式：
  - 场景标题：[内景/外景] 地点 - 时间
  - 动作描写（大写角色名首次出场）
  - 角色名（居中）+ 对话
  - 括号内的表情/动作指示
- **AND** 格式符合行业标准剧本规范

### Requirement: Output Format Selection
系统 SHALL 允许用户在小说体和剧本体之间自由选择，并在生成后切换查看。

#### Scenario: User switches output format
- **WHEN** 用户已生成小说体输出，切换为剧本体
- **THEN** Writer 基于同一份场景日志重新生成剧本体
- **AND** 不改变原始场景日志数据

#### Scenario: Partial output generation
- **WHEN** 用户只完成了部分场景（如 3/10 场）
- **THEN** Writer 支持仅对已完成的场景生成输出
- **AND** 后续场景完成后可追加生成

### Requirement: Output Quality Enhancement
系统 SHALL 在基础转换之上提供文学质量增强选项。

#### Scenario: Basic conversion vs enhanced output
- **WHEN** 用户选择"增强输出"模式
- **THEN** Writer 额外执行：
  - 文本节奏调整（长短句交替）
  - 感官细节丰富化（视觉/听觉/触觉/嗅觉）
  - 对话润色（去除冗余、增强个性）
  - 转场过渡优化
- **AND** 增强过程不改变情节和角色行为

### Requirement: Export Functionality
系统 SHALL 支持将最终输出导出为常见文件格式。

#### Scenario: Export novel
- **WHEN** 用户完成小说体输出并选择导出
- **THEN** 系统提供 Markdown（.md）和纯文本（.txt）格式下载
- **AND** Markdown 格式保留章节标题和段落结构

#### Scenario: Export screenplay
- **WHEN** 用户完成剧本体输出并选择导出
- **THEN** 系统提供纯文本（.txt）和 Fountain（.fountain）格式下载
- **AND** Fountain 格式兼容后续导入专业编剧软件
