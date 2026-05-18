# Amphoreus Story Engine — 长期记忆

## 项目概况
- **名称**：Amphoreus Story Engine / The World
- **定位**：AI 驱动的交互式故事生成系统
- **路径**：Z:\TheWorld\
- **技术栈**：Python/FastAPI + Vue.js 3/Vite/Tailwind CSS + OpenViking/Kuzu
- **规范框架**：OpenSpec（the-world-story-engine + 3 个叙事修复变更）

## 核心工作流
世界构建 → 角色生成 → 剧情架构 → 场景执行 → 叙事写作

## 完成度（2026-03-18）
- Backend: ~85%（叙事写作层是最大瓶颈）
- Frontend: ~80%
- 总体: ~75%
- 3 个 OpenSpec 叙事修复变更待执行（19个任务，0完成）

## 关键文件
- Backend 核心：`backend/app/services/narrative_writer.py`（55KB，需重构）
- CLI：`backend/cli.py`（55KB，Rich 驱动）
- 记忆系统：OpenViking（RAG 向量）+ Kuzu（图数据库）
- 场景引擎：Director/Interactor/KnowledgeMatrix/Resolution 四组件

## 优先路线
1. 执行 3 个叙事修复 OpenSpec 变更（P0，4-6天）
2. 数据库持久化（P1）
3. 前端 Pinia 重构 + Writer View 增强（P1）
4. 测试覆盖 + 部署配置（P2+）
