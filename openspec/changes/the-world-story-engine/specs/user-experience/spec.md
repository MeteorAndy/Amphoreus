## ADDED Requirements

### Requirement: One-Click Generation Mode
系统 SHALL 支持"一键生成"模式，用户输入 idea 后系统全自动完成世界构建→角色生成→剧情规划→场景执行→叙事输出的完整流程。

#### Scenario: Full auto generation
- **WHEN** 用户选择一键生成模式并输入初始 idea
- **THEN** 系统自动执行全流程，不中断询问用户
- **AND** 在各阶段之间展示进度（"世界构建中…"→"角色生成中…"→"场景 3/10…"）
- **AND** 完成后展示最终输出，用户可选择编辑

#### Scenario: Auto-generation with pre-configured settings
- **WHEN** 用户在启动一键生成前设置了偏好（叙事结构、输出格式、角色数量等）
- **THEN** 系统按照用户预设的参数执行

### Requirement: Interactive Creation Mode
系统 SHALL 支持"互动式创作"模式，用户在各阶段可介入并调整。

#### Scenario: User intervenes at any stage
- **WHEN** 用户处于互动创作模式
- **THEN** 用户可在世界构建、角色生成、剧情规划、场景执行的任意阶段暂停并修改
- **AND** 修改后系统重新评估受影响的下游内容

#### Scenario: User guides scene direction
- **WHEN** 场景正在执行
- **THEN** 用户可通过导演面板注入指令（"让张三发现李四的秘密"、"引入一个新角色"）
- **AND** 注入的指令经过 Story Guardian 校验后才执行
- **AND** Director 将指令融入当前场景的后续交互

### Requirement: Sandbox Observation Mode
系统 SHALL 支持"沙盒观察"模式，用户以上帝视角观察角色在世界中的自主互动。

#### Scenario: Passive observation of character interactions
- **WHEN** 用户进入沙盒观察模式
- **THEN** 角色在世界中自主行动（不限于固定的剧情大纲）
- **AND** 用户界面展示实时角色活动提要
- **AND** 用户可点击任意角色查看其当前状态、记忆、关系

#### Scenario: User injects world event in sandbox
- **WHEN** 用户在沙盒中注入世界事件（如"地震袭击主城"）
- **THEN** 事件广播给所有受影响角色
- **AND** 系统观察并记录角色的自发反应
- **AND** 用户可选择将沙盒中发生的精彩事件"提升"为正式剧情的一部分

### Requirement: Mode Switching
系统 SHALL 支持用户在三种体验模式之间无缝切换。

#### Scenario: Switch from auto to interactive mode
- **WHEN** 用户在一键生成完成后切换到互动创作模式
- **THEN** 系统保留已生成的所有内容
- **AND** 用户可在此基础上进行修改和继续创作

#### Scenario: Switch from interactive to sandbox mode
- **WHEN** 用户将某场景中的角色投入沙盒观察
- **THEN** 角色保留在互动创作中建立的记忆和关系
- **AND** 沙盒产生的状态变化可选择是否写回正式剧情

### Requirement: Progress Persistence
系统 SHALL 持久化所有创作进度，支持中断后恢复。

#### Scenario: User resumes after interruption
- **WHEN** 用户关闭系统后重新打开
- **THEN** 系统加载所有已保存的项目状态（世界构建进度、角色档案、已完成场景、输出内容）
- **AND** 用户可从上次中断的步骤继续

### Requirement: UI Design Quality
系统 SHALL 提供高质量、非通用 AI 风格的前端 UI 设计。

#### Scenario: UI meets design quality standards
- **WHEN** 前端界面实现
- **THEN** UI 设计应避免通用 AI 生成风格的组件（单调的灰白配色、默认字体、缺乏视觉层次）
- **AND** 采用独特的视觉风格，与"故事世界"主题契合
- **AND** 关系图、时间线等数据可视化应有良好的交互设计
