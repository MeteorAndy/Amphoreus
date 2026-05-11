## Why

现有的 AI 写作工具多停留在"文案辅助"或"单轮续写"层面，缺乏一个能够从简单 idea 出发、构建完整世界、让 LLM 角色自主互动并产出结构化长篇叙事（小说/剧本）的商业化引擎。MiroFish 证明了"世界构建 + 多 Agent 互动 + 叙事产出"这条路径的可行性（如红楼梦续写），但其聚焦于社交媒体预测场景。我们需要将这套范式迁移到虚构叙事领域，构建一个面向创作者的全栈故事引擎。

## What Changes

- 新增**对话式世界构建系统**：LLM 递进式引导用户完善世界观，同时支持上传已有草稿/设定文档进行自动解析
- 新增**角色管理系统**：基于世界观生成完整的角色群（身份、性格、核心欲望、深层恐惧、关系网络）
- 新增**剧情架构系统**：支持多种叙事结构模板（三幕、英雄之旅、Save the Cat、起承转合），输出分场大纲
- 新增**故事守护者（Story Guardian）**：在用户干预剧情走向时校验角色一致性、世界观合规性、叙事节奏，对破坏性安排可拒绝并给出修改建议
- 新增**场景交互引擎（Scene Engine）**：自研的"角色驱动 + Director 导演干预"叙事引擎，替代 OASIS 式社交媒体模拟，实现场景化角色自主互动
- 新增**分层记忆系统**：OpenViking（文件系统范式上下文管理）+ Kuzu（嵌入式图数据库）双轨记忆，支持 L0/L1/L2 分层加载和关系图谱查询
- 新增**叙事写作器**：将原始场景交互日志文学化，输出小说体或剧本体
- 新增**混合体验模式**：支持一键生成、互动式创作（关键节点用户决策）、沙盒观察（上帝视角）三种模式自由切换

## Capabilities

### New Capabilities

- `world-building`: 对话式世界构建 + 文档上传解析，输出结构化世界观数据存储到 OpenViking
- `character-management`: 角色群生成、档案管理、关系图谱构建（Kuzu），支持用户二次编辑
- `plot-architecture`: 多模板叙事结构规划，输出分场大纲，支持拖拽调整
- `story-guardian`: 剧情干预时的角色一致性、世界观合规、叙事节奏校验，分级响应（拒绝/警告/建议）
- `scene-engine`: 自研场景交互引擎，Director + 多角色交替行动循环，管理信息不对称和冲突升级
- `memory-system`: OpenViking L0/L1/L2 分层记忆 + Kuzu 图数据库关系管理，支持角色记忆独立更新
- `narrative-writer`: 场景日志到文学化叙事的转换，支持小说体和剧本体两种输出格式
- `user-experience`: 一键生成 / 互动创作 / 沙盒观察三种模式的统一体验框架

### Modified Capabilities

无（全新项目，无需修改现有能力）

## Impact

- 技术栈：Python 后端（FastAPI）+ TypeScript 前端（Vue 3）+ OpenViking + Kuzu + DeepSeek-V4-Flash
- 外部依赖：DeepSeek API（LLM）、OpenViking（记忆管理，Apache 2.0）、Kuzu（图数据库，MIT）
- 自研模块：Scene Engine、Story Guardian、Narrative Writer、World Builder 对话系统
- 部署：需支持本地部署 + Docker 化，为商业化预留 SaaS 架构空间
