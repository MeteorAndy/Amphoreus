## ADDED Requirements

### Requirement: 中英双语 README
项目根目录 SHALL 包含一个 `README.md` 文件，使用中文和英文分别完整描述项目。

#### Scenario: 中文读者访问 README
- **WHEN** 中文读者打开项目首页
- **THEN** 能看到中文版本的项目介绍、技术栈、功能特性、快速开始和项目结构

#### Scenario: 英文读者访问 README
- **WHEN** 英文读者打开项目首页
- **THEN** 能看到英文版本的项目介绍、技术栈、功能特性、快速开始和项目结构

### Requirement: README 内容覆盖
README SHALL 包含以下章节（中英各一份）：
- 项目名称与一句话简介（Amphoreus — AI-Powered Story Engine / AI 驱动的故事引擎）
- 技术栈（后端：Python/FastAPI/Kuzu/OpenAI，前端：Vue 3/Vite/TailwindCSS）
- 核心功能（世界观构建、角色管理、剧情架构、场景流式生成、AI 协作写作）
- 快速开始（环境要求、后端启动步骤、前端启动步骤）
- 项目结构（顶层目录说明）

#### Scenario: 新开发者按照 README 启动项目
- **WHEN** 开发者按照快速开始步骤操作
- **THEN** 应能成功启动后端和前端服务

### Requirement: 内容准确性
README 中的技术栈版本和功能描述 SHALL 与 `pyproject.toml` 和 `package.json` 中的实际配置一致。

#### Scenario: 依赖版本校验
- **WHEN** 项目依赖更新
- **THEN** README 中的技术栈描述应同步更新
