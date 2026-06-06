## Context

Amphoreus 项目已具备完整的后端（FastAPI + Kuzu + OpenAI）和前端（Vue 3 + Tailwind），但缺少项目根目录的 README.md。README 是开源项目的第一入口，决定协作者的第一印象和上手速度。

## Goals / Non-Goals

**Goals:**
- 创建中英双语 README.md，让中文和英文使用者都能快速了解项目
- 覆盖项目简介、技术栈、功能特性、快速开始、项目结构
- 内容准确反映当前代码状态

**Non-Goals:**
- 不包含详细的 API 文档（后续通过 OpenAPI/Swagger 提供）
- 不包含贡献指南（后续单独创建 CONTRIBUTING.md）
- 不修改任何现有代码

## Decisions

1. **中英双语结构**：先中文后英文，两个语言版本各自完整，用 `---` 分隔。这样两种语言的读者都能获得完整信息，无需跳转。

2. **内容范围**：聚焦于"这是什么、怎么跑起来"，而非详细设计文档。详细文档留在 openspec 和代码注释中。

3. **不包含 badges**：项目尚在早期开发阶段，CI/CD 和覆盖率 badges 尚未就绪，暂不添加。

## Risks / Trade-offs

- 双语维护成本：后续功能变更需同时更新两处 → 接受，当前功能变更不频繁
