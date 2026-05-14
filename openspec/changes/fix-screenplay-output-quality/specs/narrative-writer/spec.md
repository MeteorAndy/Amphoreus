## MODIFIED Requirements

### Requirement: Scene Log to Screenplay Conversion
系统 SHALL 将场景交互的原始日志转换为具有完整结构的剧本体文本，包括 LLM 生成的剧名、统一格式的场景标记、场次编号和幕结构。

#### Scenario: Screenplay title generation
- **WHEN** 用户请求输出剧本体
- **THEN** 系统复用 TitleGenerator 生成 3-5 个备选剧名
- **AND** 当前语言为中文时，剧名 SHALL 使用简体中文
- **AND** 当前语言为英文时，剧名 SHALL 使用英文
- **AND** 用户可选择或自定义剧名

#### Scenario: Scene heading format — Chinese
- **WHEN** 当前语言为中文且生成剧本
- **THEN** 每场 SHALL 以统一格式 `[内景] 地点名 - 时间` 或 `[外景] 地点名 - 时间` 开头
- **AND** 不得出现 `EXT.`、`内景.`、`[INT.]` 等其他格式

#### Scenario: Scene heading format — English
- **WHEN** 当前语言为英文且生成剧本
- **THEN** 每场 SHALL 以统一格式 `[INT.] Location Name - Time` 或 `[EXT.] Location Name - Time` 开头

#### Scenario: Scene numbering
- **WHEN** 生成完整剧本
- **THEN** 每场 SHALL 有编号：中文 `第X场`、英文 `Scene X`
- **AND** 编号位于场景标题之前

#### Scenario: Character name preservation
- **WHEN** 生成剧本中的角色名
- **THEN** 角色名 SHALL 始终使用原始语言的原始写法
- **AND** 中文角色名不得转换为拼音或英文大写（不能出现 `LIN CHEN`）
- **AND** 英文角色名保持原文

#### Scenario: Act structure
- **WHEN** 有 4 个以上场景
- **THEN** 场景 SHALL 按叙事弧分组为幕（3-4 幕）
- **AND** 每幕有标题和简短的幕简介
- **WHEN** 场景少于 4 场
- **THEN** 合并为单幕，不强制分幕

### Requirement: Output Format Selection
系统 SHALL 允许用户在小说体和剧本体之间自由选择，并在生成后切换查看。剧本体格式必须符合上述所有统一标准。

#### Scenario: User switches from novel to screenplay
- **WHEN** 用户已生成小说体输出，切换为剧本体
- **THEN** Writer 基于同一份场景日志重新生成剧本体
- **AND** 剧本体采用统一格式（场景标记、场次编号、幕结构）
- **AND** 剧名与小说名独立（可不同）

## REMOVED Requirements

### Requirement: Scene-by-scene screenplay assembly
**Reason**: 已被场次编号+幕结构+格式统一的剧本替代。旧方式产生混用的场景标记格式（`[内景]`/`EXT.`/`内景.`）、角色名大写转换（`LIN CHEN`）、硬编码标题（"剧本"/"SCREENPLAY"）。
**Migration**: 使用新的 ScreenplayWriter 实现。旧 `_assemble_screenplay()` 中的 `title = "剧本"` 或 `title = "SCREENPLAY"` 硬编码全部移除。

## ADDED Requirements

### Requirement: Screenplay system prompt — playwright role
系统 SHALL 使用专业编剧角色的 system prompt 进行剧本写作。

#### Scenario: Playwright system prompt
- **WHEN** LLM 被调用生成剧本
- **THEN** system prompt SHALL 引导 LLM 扮演编剧角色
- **AND** LLM 先构思角色动机、故事背景、角色对白
- **AND** 然后创作充满转折与悬念的情节主线
- **AND** 保持观众的紧张和期待直到结局
- **AND** 所有输出使用当前语言（中文或英文）

### Requirement: Script format post-processing
系统 SHALL 在后处理阶段统一剧本格式。

#### Scenario: Scene heading normalization
- **WHEN** LLM 输出的剧本包含不一致的场景标记
- **THEN** PostProcessor 检测并统一场景标记格式
- **AND** `EXT.` → `[外景]`（ZH）或 `[EXT.]`（EN）
- **AND** `内景.` → `[内景]`（ZH）
- **AND** `[INT.]` 混入中文剧本 → `[内景]`

#### Scenario: Character name normalization
- **WHEN** LLM 输出将中文角色名转换为英文大写
- **THEN** 系统在已知角色列表中检测并修复为原始中文名
- **AND** 无法匹配的角色名保留原样
