## MODIFIED Requirements

### Requirement: Scene Log to Novel Conversion
系统 SHALL 将场景交互的原始日志转换为具有完整结构的小说体叙事文本，包括 LLM 生成的书名和章回结构。

#### Scenario: Title generation
- **WHEN** 一个或多个场景执行完成，用户请求输出小说体
- **THEN** TitleGenerator 基于世界摘要+角色摘要+剧情大纲生成 3-5 个备选书名
- **AND** 当前语言为中文时，书名 SHALL 使用简体中文
- **AND** 当前语言为英文时，书名 SHALL 使用英文
- **AND** 用户可选择或自定义书名

#### Scenario: Chapter structure planning
- **WHEN** 书名确定后
- **THEN** ChapterPlanner 根据剧情大纲和场景列表，规划章节划分
- **AND** 每章包含 2-4 个相关场景
- **AND** 当前语言为中文时，章标题 SHALL 为 "第X章 篇名"
- **AND** 当前语言为英文时，章标题 SHALL 为 "Chapter X: Title"
- **AND** 每章有文学性篇名

#### Scenario: Per-chapter prose generation
- **WHEN** 章节规划完成
- **THEN** NarrativeWriter 逐章调用 LLM：传入整章所有场景日志+章标题+前后章节摘要
- **AND** LLM 输出完整章散文，包含场景间过渡段落
- **AND** 保留原始对话和关键动作不变
- **AND** 当前语言为中文时，所有散文SHALL使用简体中文
- **AND** 当前语言为英文时，所有散文SHALL使用英文

#### Scenario: Novel assembly
- **WHEN** 所有章节散文生成完成
- **THEN** 组装为完整小说：书名 → 各章散文（按章节编号排列）
- **AND** 无硬编码英文标题（"Generated Narrative"、"Part I" 等已移除）
- **AND** 所有静态文本通过 i18n 系统输出

### Requirement: Scene Log to Screenplay Conversion
系统 SHALL 将场景交互的原始日志转换为剧本体文本。标题和场景标记遵循当前语言。

#### Scenario: Generate screenplay from scene log
- **WHEN** 用户请求输出剧本体
- **THEN** Writer 将场景日志转换为标准剧本格式：
  - 场景标题：`[内景/外景] 地点 - 时间`（中文）或 `[INT./EXT.] Location - Time`（英文）
  - 动作描写（中文或英文，大写角色名首次出场）
  - 角色名（居中）+ 对话
  - 括号内的表情/动作指示
- **AND** 格式符合行业标准
- **AND** 剧本标题通过 i18n 输出（非硬编码 "SCREENPLAY"）

#### Scenario: Bilingual screenplay heading
- **WHEN** 当前语言为中文且用户请求剧本体
- **THEN** 场景标题使用中文标记：`[内景]` / `[外景]`，时间使用中文
- **WHEN** 当前语言为英文且用户请求剧本体
- **THEN** 场景标题使用英文标记：`[INT.]` / `[EXT.]`，时间使用英文

### Requirement: Output Quality Enhancement
系统 SHALL 在基础转换之上提供文学质量增强选项。增强过程遵守当前语言的文学惯例。

#### Scenario: Enhanced output follows language conventions
- **WHEN** 用户选择"增强输出"模式且语言为中文
- **THEN** Writer 额外执行：
  - 标点规范化（中文引号「」或「」，省略号……，破折号——）
  - 段落长度适配中文阅读习惯
  - 对话格式统一为中文惯例
- **WHEN** 用户选择"增强输出"模式且语言为英文
- **THEN** Writer 执行英文对应的增强规则

### Requirement: Export Functionality
系统 SHALL 支持将最终输出导出为常见文件格式。文件名和元数据遵守当前语言。

#### Scenario: Export novel — Chinese filename
- **WHEN** 用户完成中文小说体输出并选择导出
- **THEN** 文件名使用书名（中文字符允许）
- **AND** 默认导出格式为 Markdown（.md）

#### Scenario: Export novel — English filename
- **WHEN** 用户完成英文小说体输出并选择导出
- **THEN** 文件名使用书名（英文字符）
- **AND** 默认导出格式为 Markdown（.md）

## ADDED Requirements

### Requirement: Title Generation
系统 SHALL 使用 LLM 根据故事内容自动生成备选书名。

#### Scenario: Chinese title generation
- **WHEN** 当前语言为中文且有场景存档
- **THEN** TitleGenerator 生成 3-5 个中文书名备选
- **AND** 书名风格多样（诗意型、悬念型、直白型至少各一）
- **AND** 书名长度 2-15 个中文字符

#### Scenario: English title generation
- **WHEN** 当前语言为英文且有场景存档
- **THEN** TitleGenerator 生成 3-5 个英文书名备选
- **AND** 书名长度 2-10 个英文单词

### Requirement: Chapter Structure Planning
系统 SHALL 使用 LLM 规划场景到章节的映射和每章标题。每章的目标字数应符合真实小说的标准。

#### Scenario: Chapter planning for Chinese novel
- **WHEN** 当前语言为中文且有 3 个以上场景
- **THEN** ChapterPlanner 将场景分组为章节，使每章预估产出 2500-4000 字
- **AND** 每章有格式为 "第X章 篇名" 的标题（不使用"第X回"）
- **AND** 篇名具有文学性
- **AND** 若预估字数不足 2500 字，规划中注明"本章需扩展描写"

#### Scenario: Chapter planning for English novel
- **WHEN** 当前语言为英文且有 3 个以上场景
- **THEN** ChapterPlanner 将场景分组为章节，使每章预估产出 2000-3500 词
- **AND** 每章有格式为 "Chapter X: Title" 的标题

#### Scenario: Word count constraint in writing prompt
- **WHEN** LLM 开始逐章写作
- **THEN** 写作 prompt 中 SHALL 包含本章目标字数范围
- **AND** 中文目标为 2500-4000 字，英文目标为 2000-3500 词
- **AND** LLM 应充分展开描写、内心独白、环境渲染以达到目标字数

#### Scenario: Short story fallback
- **WHEN** 全篇场景少于 3 场
- **THEN** ChapterPlanner 标记为"短篇"模式
- **AND** 字数要求放宽为 800-1500 字（中文）或 500-1000 词（英文）

## REMOVED Requirements

### Requirement: Scene-by-scene assembly
**Reason**: 已被逐章统一写作替代。旧方式将场景日志逐条转为散文后机械拼接，产生硬编码英文标题和断裂叙事。
**Migration**: 使用新的 ChapterPlanner + 逐章写作流程。旧 `_assemble_novel()` 中的 `"Generated Narrative"` 和 `"Part I"` / `"Chapter N"` 硬编码全部移除。
