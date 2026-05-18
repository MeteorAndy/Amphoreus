# Amphoreus Story Engine — 综合分析报告

**分析日期**：2026-03-18
**项目路径**：Z:\TheWorld\
**技术栈**：Python/FastAPI + Vue.js 3/Vite + OpenViking/Kuzu + OpenSpec

---

## 一、项目全貌

Amphoreus 是一个 AI 驱动的交互式故事生成系统，核心工作流为：

```
世界构建 → 角色生成 → 剧情架构 → 场景执行 → 叙事写作
```

覆盖从「种子 Idea」到「可导出小说/剧本」的完整创作链。

---

## 二、完成度总览

| 模块 | 完成度 | 状态 |
|------|--------|------|
| World Building | **95%** | 对话式构建 + 文档上传 + 阶段推进，接近完整 |
| Character Manager | **90%** | CRUD + Big5/大五人格 + 关系网络 + Refine |
| Plot Architect | **85%** | 4种叙事结构 + 场景管理 + 一致性检查 |
| Scene Engine | **90%** | WebSocket 流式执行 + 导演干预 + 知识矩阵 |
| Story Guardian | **100%** | 内容校验就绪 |
| Memory System | **80%** | OpenViking + Kuzu 双存储可用，集成待验证 |
| Narrative Writer | **60%** | 核心逻辑存在，3项重构待执行 |
| CLI | **95%** | Rich 驱动交互式 CLI，功能完整 |
| **Backend 总体** | **~85%** | |
| World View | **95%** | 欢迎页→聊天构建→阶段指示器→完成→跳转 |
| Character View | **85%** | 卡片网格 + 编辑弹窗 + 关系图 + Refine |
| Plot View | **85%** | 大纲侧栏 + Timeline + 场景增删改 + 一致性 |
| Scene View | **90%** | WebSocket 实时流 + Director Panel + 配置 |
| Writer View | **70%** | 格式切换 + 标题候选 + 导出，但依赖后端重构 |
| **Frontend 总体** | **~80%** | |
| **项目总体** | **~75%** | 核心骨架完整，叙事写作层是最大瓶颈 |

---

## 三、分模块深度分析

### 3.1 后端（Python/FastAPI）

**已完成部分**：
- `world_builder.py`：对话式渐进构建（rules→locations→factions→timeline 四阶段），支持文档上传解析和增量合并，含场景丰富度评估
- `character_manager.py`：Big5/大五人格模型 + MBTI + 角色弧（arc_stage）+ core_desire/deep_fear + secrets/knowledge_scope，完整 CRUD
- `relationship_builder.py`：角色关系自动发现与构建，图路径查询
- `plot_architect.py`：支持 Three-Act / Hero's Journey / Save the Cat / 起承转合 四种叙事结构
- `story_guardian.py`：内容安全与世界观一致性校验
- `scene_engine/`：Director（全局调度）+ Interactor（角色互动）+ Knowledge Matrix（知识管理）+ Resolution（场景结算），WebSocket 流式推送
- `memory/`：OpenViking RAG 向量存储（3 scope: world/chars/story）+ Kuzu 图数据库（节点: Character/Location/Faction/Event，边: RELATES_TO/BELONGS_TO/LOCATED_AT/CAUSED_BY）
- `cli.py`（55KB）：Rich 驱动的完整 CLI，覆盖所有工作流
- `llm_client.py`：OpenAI 兼容 API + Volcengine Ark，含重试和模型切换

**待补齐**：
- **Narrative Writer 重构**（最大技术债）：3个 OpenSpec 变更待执行
  - `fix-narrative-output-quality`：标题生成、章回结构、逐章写作、排版后处理（7任务，0完成）
  - `fix-screenplay-format-and-depth`：禁止LLM输出格式标记、心理活动注入、格式清理（5任务，0完成）
  - `fix-screenplay-output-quality`：场次编号、幕结构、编剧prompt重建、格式统一（7任务，0完成）
- **持久化层缺失**：当前所有数据存于内存 dict，无数据库集成
- **测试覆盖为零**：无 unit test / integration test
- **认证/用户系统**：无任何用户管理

### 3.2 前端（Vue.js 3 + TypeScript + Vite + Tailwind CSS）

**已完成部分**：
- **API Client**（`client.ts`）：完整的类型安全 HTTP 客户端，覆盖 World/Character/Plot/Scene/Guardian/Writer 全部端点 + WebSocket 连接
- **Type System**（`api.ts`, 329行）：完整的 TypeScript 类型定义，与后端 Pydantic 模型精确对应
- **5 个 Composables**（Composition API 状态管理）：
  - `useWorldBuilder`：含 `withRetry` 重试逻辑、增量合并 `mergeExtractedData`、localStorage 持久化 session
  - `useCharacters`：含 `generateCharacters` 生成并去重合并、`fetchCharacterNetwork` 关系网络
  - `usePlotArchitect`：含 `mapResponseToDisplay` API→显示层映射、`checkConsistency` 一致性检查
  - `useSceneEngine`：WebSocket 实时流处理、`handleStreamMessage` 分类型路由、自动重连机制
  - `useNarrativeWriter`：格式切换 + 导出 + 标题管理
- **8 个 Vue 组件**：AppLayout（侧边导航+HMR）、ChatPanel（自动滚动+dots动画）、CharacterCard（展开详情+特质标签）、SceneFeed（轮次流）、DirectorPanel（状态机驱动UI）、PlotTimeline（场景排序+移动）、RelationshipGraph（SVG力导向布局）、WritingPreview（格式切换+导出）
- **5 个 View 页面**：WorldBuilderView（欢迎页+阶段指示器+上传+完成）、CharacterView（网格+编辑弹窗+Refine+关系图+Proceed to Plot）、PlotView（大纲侧栏+Timeline+场景弹窗+一致性检查）、SceneView（选择器+WebSocket流+Director+配置）、WriterView（大纲选择+标题候选+预览+导出）
- **i18n**：中英双语，119条翻译条目，localStorage 持久化
- **路由**：5条路由（/world, /characters, /plot, /scene, /writer），hash history
- **视觉**：暗色主题（gray-950/900）+ indigo 品牌色 + Tailwind CSS 4，风格一致

**待补齐**：
- **无 Pinia/Vuex 状态管理**：全部使用 composables + localStorage，跨页面状态共享依赖手动传递
- **无加载骨架屏**：仅使用 loading spinner，体验可优化
- **无错误边界**：error 仅通过 banner 展示，无全局处理
- **Writer View 功能受限**：标题候选展示完整但生成依赖后端重构
- **Responsive 设计不完整**：移动端适配未验证
- **无 E2E 测试**：Playwright/Cypress 皆无
- **CSS 极简**：仅 `@import "tailwindcss"`，无自定义 Design Token 或主题系统

### 3.3 OpenSpec 规范管理

**已记录**：
- 主变更 `the-world-story-engine`：proposal + design + tasks + 8 spec 子模块
- 3 个叙事修复变更：各有 proposal + design + tasks + spec delta

**待改进**：
- Tasks 中的 checkbox 全部未勾选（`[ ]`），无法反映实际进度
- 缺少 `ARCHITECTURE.md` 或系统级架构文档
- 缺少 API 文档（OpenAPI/Swagger 未配置）

---

## 四、改进方向与优先级

### P0 — 阻塞性（叙事写作层）

| # | 改进项 | 影响范围 | 预估工作量 |
|---|--------|---------|-----------|
| 1 | 执行 `fix-narrative-output-quality` | narrative_writer.py 60% | 2-3天 |
| 2 | 执行 `fix-screenplay-output-quality` | narrative_writer.py 40% | 1-2天 |
| 3 | 执行 `fix-screenplay-format-and-depth` | narrative_writer.py 30% | 1天 |

这三个变更合并执行，总工作量约 4-6 天，是项目从「可用」到「可交付」的关键。

### P1 — 高优先级（工程质量）

| # | 改进项 | 说明 |
|---|--------|------|
| 4 | **数据持久化** | 引入 SQLite/PostgreSQL，替换内存 dict；World State + Characters + Plots 都需要持久化 |
| 5 | **后端测试** | pytest + pytest-asyncio，核心服务至少 70% 覆盖率 |
| 6 | **前端状态管理** | 引入 Pinia，统一管理 worldId/characters/plots 等跨页面状态 |
| 7 | **API 文档** | 配置 FastAPI OpenAPI，自动生成 Swagger UI |
| 8 | **错误处理增强** | 后端统一异常处理中间件 + 前端全局错误边界 |

### P2 — 中优先级（体验与扩展）

| # | 改进项 | 说明 |
|---|--------|------|
| 9 | **记忆系统集成验证** | 确认 OpenViking + Kuzu 在整个工作流中正确读写 |
| 10 | **章节编辑器** | 前端新增章节级别的编辑/重排/单独重新生成 |
| 11 | **导出格式扩展** | 除 .md/.fountain 外，增加 .epub/.docx 导出 |
| 12 | **用户系统** | 多用户支持、项目保存/加载、历史版本 |
| 13 | **前端测试** | Vitest + Vue Test Utils + Playwright E2E |
| 14 | **响应式优化** | 移动端适配、PWA 支持 |

### P3 — 低优先级（锦上添花）

| # | 改进项 | 说明 |
|---|--------|------|
| 15 | **主题系统** | 暗色/亮色切换 + 自定义 Design Token |
| 16 | **性能优化** | LLM 响应流式传输到前端（SSE）、虚拟滚动（长文本） |
| 17 | **部署配置** | Docker Compose + CI/CD Pipeline |
| 18 | **协作功能** | 多人协作编辑、评论、版本 diff |

---

## 五、技术架构评价

### 优势

1. **模块化设计优秀**：8 个 spec 子模块职责清晰，Scene Engine 的 Director/Interactor/Knowledge Matrix/Resolution 四组件设计尤为出色
2. **类型安全贯穿全栈**：后端 Pydantic ↔ 前端 TypeScript 类型精确对应
3. **Composition API 使用得当**：composables 封装良好，状态管理逻辑清晰
4. **OpenSpec 规范先行**：设计文档与代码基本对应，有利于长期维护
5. **记忆系统双存储**：向量检索（OpenViking）+ 图数据库（Kuzu）组合是故事引擎的理想架构

### 风险点

1. **Narrative Writer 技术债集中**：`narrative_writer.py`（55KB）承载过多逻辑，3 个 OpenSpec 变更同时修改同一文件，存在合并冲突风险
2. **无持久化**：所有数据内存存储，重启即丢失，这是生产化的最大障碍
3. **CLI 代码量大**：`cli.py`（55KB）与 `narrative_writer.py`（55KB）均为大文件，需要拆分
4. **前端无 Pinia**：当前 composables 模式对当前规模尚可，但随着功能增加会越来越难维护

---

## 六、文件统计

| 类别 | 数量 | 总大小（估） |
|------|------|------------|
| 后端 Python | ~15 文件 | ~150KB |
| 前端 Vue/TS | ~25 文件 | ~80KB |
| OpenSpec 文档 | ~35 文件 | ~100KB |
| 配置文件 | ~5 文件 | ~5KB |
| **合计** | **~80 文件** | **~335KB** |

---

## 七、结论

Amphoreus Story Engine 是一个 **架构设计优秀、核心骨架完整** 的 AI 故事生成系统。项目最突出的特点是严格的模块化设计和全栈类型安全，这在大语言模型应用项目中较为罕见。

当前最大瓶颈是 **叙事写作层**——它是整个工作流的最终产出环节，但恰好是完成度最低的部分。一旦 3 个 OpenSpec 变更执行完毕，项目即可进入可演示的 Alpha 阶段。

建议开发路线：
1. **Week 1-2**：执行 3 个叙事修复 OpenSpec 变更
2. **Week 3**：引入数据库持久化 + 后端基础测试
3. **Week 4**：前端 Pinia 重构 + Writer View 增强
4. **Week 5+**：P2/P3 改进项按需推进
