## Context

基于探索阶段达成的共识，本项目是一个小说/剧本生成引擎。核心技术路线：

- **叙事模式**：角色驱动 + Director 导演干预（方案 B）
- **用户体验**：混合模式（一键生成 + 互动创作 + 沙盒观察）
- **记忆系统**：OpenViking（结构化上下文管理）+ Kuzu（图数据库关系管理）
- **LLM**：DeepSeek-V4-Flash（1M 上下文窗口）
- **输出格式**：小说体 + 剧本体
- **参考项目**：MiroFish（架构范式）、SillyTavern（角色卡/Lorebook 设计）、OpenClaw（Agent 自主行动参考）

**发展路径**：先自用验证（Phase 0） → 功能完善 → 商业化（桌面版 + Web 版）。个人开发者业余项目，LLM API 成本由用户承担（自带 API Key），从根本上避免 SaaS 模式下 API 成本失控的结构性问题。

**部署策略**：Tauri 桌面应用作为主产品，Python FastAPI 以 Sidecar 模式嵌入。代码 95% 与 Web 版共享，后续可快速部署 Web Demo。

**OpenClaw 整合潜力**：后期可将项目整合为 OpenClaw 的 Agent 插件，实现"赛博作家"——自主监控创作进度、定时推送新章节、跨平台发布。

关键约束：1M 上下文窗口改变了设计假设——瓶颈从"上下文空间"转为"Token 成本控制"。

## Goals / Non-Goals

**Goals:**
- 提供从 idea 到完整小说/剧本的全链路自动化
- 角色能在场景中自主、一致地互动，展现戏剧张力
- 用户可在任意时刻介入（修改剧情、调整角色、干预场景）
- Story Guardian 能有效防止角色 OOC 和叙事崩塌
- 支持小说体和剧本体两种输出格式
- **Phase 0：开发者自用跑通全流程，验证引擎质量和故事产出效果**
- **用户自带 LLM API Key，零服务端 API 成本**
- 桌面版（Tauri）作为主产品，Web 版作为 Demo/试用入口

**Non-Goals:**
- 不考虑多用户协作/社区功能（MVP 阶段单用户）
- 不支持实时协同编辑
- 不支持多媒体生成（插图、配音等）
- 不做模型训练/微调（纯 prompt engineering + RAG）
- 不托管用户 API 调用（用户直接调 DeepSeek API）

## Decisions

### 1. 后端框架：FastAPI（非 Flask）

**选择**：FastAPI
**理由**：
- 原生异步支持——场景引擎需要大量并发 LLM 调用，异步是关键
- 自动 OpenAPI 文档——前后端协作效率高
- Pydantic 模型——与 OpenViking/Kuzu 的数据结构天然契合
- WebSocket 支持——场景执行是长时间流式过程，WS 推送进度优于轮询

**替代方案**：Flask（MiroFish 使用）——缺原生异步和 WebSocket，需额外扩展。

### 2. 记忆系统：OpenViking + Kuzu 双轨

**选择**：OpenViking 主记忆 + Kuzu 关系管理
**理由**：
- OpenViking 的 L0/L1/L2 分层天然匹配角色记忆的需求（核心身份→详细信息→完整历史）
- OpenViking 的文件系统范式（`viking://chars/{id}/`）使角色档案层级化
- OpenViking 不是图数据库，角色关系查询需要 Kuzu 补充
- Kuzu 嵌入式部署（`pip install`）、多跳查询快 374x（vs Neo4j），适合 MVP
- 两者都能嵌入 Python 进程，零运维成本

**OpenViking 的 LLM 成本**：

OpenViking 自身的 VLM（记忆摘要/分层）和 Embedding（语义检索）需要 LLM 能力。由于 OpenViking 是字节项目，其 VLM 和 Embedding 均围绕火山引擎豆包模型深度优化，推荐使用原生方案：

| OpenViking 组件 | 方案 | 模型 | 成本 |
|---------------|------|------|------|
| VLM（摘要/分层） | 火山引擎 API | `doubao-seed-2-0-pro-260215` | 极低，每次记忆更新 ~500-2000 tokens |
| Embedding（语义检索） | 火山引擎 API | `doubao-embedding-vision-251215` | 极低，语义检索用量小 |

VLM 成本估算：一场场景 5 角色 × 1000 tokens = 5000 tokens。完整故事（15 场）约 75K tokens，火山引擎豆包 lite 模型价格极低（~¥0.0008/千 tokens），总计不到 ¥0.1。

**用户需要两个 API Key**：
```
DeepSeek API Key    → 故事引擎主力模型 (deepseek-v4-flash)
火山引擎 API Key     → OpenViking VLM + Embedding (豆包系列)
```

首次启动时引导用户分别配置，存储在本地配置文件。两个 Key 的获取都有免费额度。

**替代方案（降级）**：若用户不想注册火山引擎，OpenViking 可通过 `openai` provider 回退到 DeepSeek API（VLM）+ 本地 Ollama bge-m3（Embedding）。效果略差但可用。

**替代方案**：
- Neo4j：功能强大但部署太重（JVM），MVP 阶段杀鸡用牛刀
- Zep Cloud：SaaS 闭源，商业化成本不可控

### 3. 场景引擎：自研（不基于 OASIS）

**选择**：自研 Scene Engine
**理由**：OASIS 是为社交媒体模拟设计的（发帖/评论/点赞/信息流），原语与叙事场景（对话/动作/情绪/空间）完全不同。自研引擎的核心设计：

```
场景设置 → 交互循环(环境感知→角色选择→行动生成→反应生成→导演裁决) → 记忆更新
```

**参考 OASIS 的**：Round-based 多 Agent 并行、动作日志格式（.jsonl）、子进程隔离
**自己做的**：叙事逻辑（冲突升级、节奏控制、信息不对称管理）、角色上下文组装、Director 导演系统

详见 Scene Engine 专节。

### 4. LLM 选型：双 Provider 策略

**选择**：故事引擎用 DeepSeek-V4-Flash，OpenViking 用火山引擎豆包系列
**理由**：

| 用途 | Provider | 模型 | 原因 |
|------|---------|------|------|
| 故事引擎主力 | DeepSeek | `deepseek-v4-flash` | 1M 上下文、成本低、中文强 |
| OpenViking VLM | 火山引擎 | `doubao-seed-2-0-pro-260215` | OpenViking 字节原生，Seed 2.0 Pro 效果最优 |
| OpenViking Embedding | 火山引擎 | `doubao-embedding-vision-251215` | 同上，推荐的原生配套 Embedding 版本 |

**用户配置成本**：两个 API Key（DeepSeek + 火山引擎），首次启动引导分别配置。两者都有免费额度，OpenViking 用量极小（一整篇小说不到 ¥0.1）。

**降级方案**：若用户不想注册火山引擎，OpenViking 可通过 openai provider 回退 DeepSeek + 本地 Ollama bge-m3 Embedding。

### 5. 项目结构：Monorepo（前后端分离）

```
TheWorld/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI 路由
│   │   ├── core/          # 配置、依赖注入
│   │   ├── models/        # Pydantic 数据模型
│   │   ├── services/      # 核心业务逻辑
│   │   │   ├── world_builder.py
│   │   │   ├── character_manager.py
│   │   │   ├── plot_architect.py
│   │   │   ├── story_guardian.py
│   │   │   ├── scene_engine/
│   │   │   │   ├── director.py
│   │   │   │   ├── interactor.py
│   │   │   │   └── environment.py
│   │   │   ├── memory/
│   │   │   │   ├── openviking_store.py
│   │   │   │   └── kuzu_store.py
│   │   │   └── narrative_writer.py
│   │   └── utils/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── WorldBuilderView.vue
│       │   ├── CharacterView.vue
│       │   ├── PlotView.vue
│       │   ├── SceneView.vue
│       │   └── WriterView.vue
│       ├── components/
│       └── api/
└── openspec/

# Tauri 桌面版时新增:
├── desktop/              # Tauri 项目 (Rust shell)
│   ├── src-tauri/        # Rust 配置 + sidecar 管理
│   ├── src/              # 窗口入口（指向 frontend/）
│   └── tauri.conf.json
└── scripts/
    └── build.py          # PyInstaller 打包脚本
```

### 6. 部署模式：Tauri 桌面版（主）+ Web（辅）

**选择**：Tauri 桌面应用，Python 后端以 PyInstaller Sidecar 模式嵌入
**理由**：
- 用户自带 API Key → 无需服务端中转 → API 成本由用户承担 → 零边际成本
- 个人开发者无法承担 SaaS 模式下的大规模 LLM API 费用（一篇小说约 $32 API 成本）
- Tauri 安装包小（~10MB shell + Python sidecar）vs Electron（~200MB+）
- Vue 3 前端 100% 复用于桌面版和 Web 版
- 后续 Web 版可作为 Demo/试用入口，引导购买桌面版

**架构**：
```
┌──────────────────────────────────────┐
│           Tauri Shell (Rust)          │
│  窗口管理 / 自动更新 / 系统托盘 / 打包    │
│                                      │
│  ┌──────────────────────────────┐   │
│  │  Vue 3 前端 (Tauri WebView)    │   │
│  │  与 Web 版 100% 共享代码       │   │
│  └──────────┬───────────────────┘   │
│             │ HTTP (localhost:5001)  │
│  ┌──────────▼───────────────────┐   │
│  │  Python FastAPI Sidecar       │   │
│  │  PyInstaller 打包为独立可执行   │   │
│  │  • OpenViking (本地嵌入)      │   │
│  │  • Kuzu (本地嵌入)            │   │
│  │  • Scene Engine              │   │
│  │  • 直接调用 DeepSeek API       │   │
│  └──────────────────────────────┘   │
└──────────────────────────────────────┘
```

**Sidecar 生命周期**：Tauri 启动时 spawn Python 进程，监听 stdout/stderr，关闭时 kill。通过 HTTP（localhost）通信。

**Python Sidecar 打包**：PyInstaller 将整个 Python 环境 + 依赖打包为单个可执行文件（~150-250MB）。OpenViking 和 Kuzu 的本地数据存储在用户目录（`~/.the-world/`）。

**替代方案**：
- Electron：生态更成熟但安装包大、内存高，对这类非 Web 原生的应用过重
- 纯 Rust 重写：性能最优但开发成本高，LLM 工具链（openai sdk, openviking, kuzu）在 Python 生态更成熟

### 7. API Key 管理

**选择**：用户本地配置双 Provider Key，应用分别调用
**理由**：
- OpenViking 是字节项目，VLM + Embedding 围绕豆包模型深度优化，用原生方案效果最佳
- 故事引擎主力用 DeepSeek（1M 上下文、成本低），OpenViking 用火山引擎豆包（字节原生推荐）
- 两个 Key 获取均有免费额度，总成本透明
- 用户数据（故事、世界设定、记忆）完全本地存储，隐私零泄露

**实现**：首次启动引导用户分别输入 DeepSeek API Key 和火山引擎 API Key（均可跳过用降级方案）。Key 加密存储在本地 `~/.the-world/config.json`。后续支持更多 Provider 切换。

**OpenViking 降级方案**：若用户不想注册火山引擎 → VLM 回退 DeepSeek（openai provider）+ Embedding 回退本地 Ollama bge-m3。

### 8. 自用验证策略（Phase 0）

### 8. 自用验证策略（Phase 0）

在商业化之前，开发者自己先用这套流程跑通完整的故事生成：

1. **最小目标**：用引擎生成一个 5-8 角色的中篇故事（3-5 场关键场景），输出小说体
2. **验证维度**：
   - 角色在场景中的互动是否自然、有戏剧张力？
   - Director 的节奏控制和冲突管理是否有效？
   - Story Guardian 能否实际拦截 OOC 行为？
   - 最终输出的文学质量是否达到可阅读标准？
3. **迭代节奏**：先用纯命令行或最小 UI 跑通 → 确认引擎质量 → 再投入前端和 Tauri 打包
4. **OpenClaw 整合**：验证引擎稳定后，可封装为 OpenClaw Agent 插件，实现"赛博作家"——定时续写章节、自主管理角色状态、跨平台发布

### 9. Scene Engine 详细设计

**核心循环**：

```
┌─────────────────────────────────────────────────┐
│ SCENE SETUP (Director, 每场一次)                  │
│ • 选择地点 + 生成场景描写                          │
│ • 选择在场角色 + 设置各自的本场目标                  │
│ • 设置隐藏信息（只有特定角色知道）                   │
│ • 注入潜在冲突源                                   │
│ • 设定结束条件                                     │
├─────────────────────────────────────────────────┤
│ INTERACTION LOOP (循环至结束条件触发)               │
│   Step 1 - 环境感知: Environment Agent 更新氛围     │
│   Step 2 - 角色选择: Director 选择本轮主动角色        │
│   Step 3 - 行动生成: 为主动角色组装上下文→LLM生成     │
│   Step 4 - 反应生成: 并行生成其他角色的反应           │
│   Step 5 - 导演裁决: 评估冲突/节奏/OOC→继续或结束    │
├─────────────────────────────────────────────────┤
│ SCENE RESOLUTION (每场结束)                       │
│ • 角色记忆独立更新 (OpenViking L0/L1/L2)           │
│ • 世界状态更新 (地点、关系、事件)                    │
│ • 叙事日志归档 (原始JSON → Narrative Writer 输入)   │
└─────────────────────────────────────────────────┘
```

**角色上下文组装**（利用 1M 上下文）：

| 层级 | 内容 | 估算 tokens |
|------|------|-------------|
| L0 固定 | 核心身份、当前目标、当前情绪 | ~200 |
| L1 固定 | 完整性格、与在场角色的关系详情、近期完整场景记忆(3-5场) | ~15K |
| 场景层 | 场景描写+氛围、在场角色的最近发言、本场目标 | ~8K |
| L2 按需 | 相关世界知识(触发式)、久远记忆(触发式)、角色秘密 | 按需 |

单次角色行动 ~25-40K tokens，1M 窗口绰绰有余。

**信息不对称管理**：Director 维护"谁知道什么"矩阵，每个角色只基于自己的认知行动。这是戏剧张力的核心来源。

### 10. Story Guardian 设计

评估维度：角色一致性 → 关系逻辑 → 世界观合规 → 叙事节奏 → 角色弧光完整性

分级响应：🔴 CRITICAL（硬拒绝，不允许执行）→ 🟡 WARNING（警告+建议，用户可忽略）→ 🔵 SUGGESTION（纯建议，不阻塞）

Guardian 在每次用户介入剧情走向时触发，加载受影响角色的完整档案 + 关系图 + 世界观规则 + 近期叙事历史。

### 11. 前端设计策略

**选择**：Vue 3 + Vite + Tailwind CSS
**理由**：MiroFish 已证明 Vue 3 适合此类项目；Tailwind 快速出 UI；不引入重型 UI 框架保持灵活性。

**四个核心视图**：
- WorldBuilderView：对话式引导 + 文档上传
- CharacterView：角色群展示 + 关系图可视化（vis-network）
- PlotView：剧情大纲（时间线/卡片拖拽）
- SceneView：场景执行（实时流 + 导演面板 + 干预入口）
- WriterView：输出预览（小说/剧本切换）

**前端设计质量**：按用户要求提供高设计质量的 UI，在实现阶段通过 `frontend-design` skill 系统处理。

## Risks / Trade-offs

- **[R1] 角色一致性与创意自由的冲突** → Story Guardian 分级响应 + 用户最终裁决权；WARNING 级别用户可忽略
- **[R2] 长故事累积 Token 成本** → Token 成本由用户承担（自带 API Key），引擎侧通过 OpenViking 分层 + 懒加载控制消耗
- **[R3] Director 决策质量不稳定** → Director 自身也用 LLM，设计好评估 prompt（检查清单式，非开放式）
- **[R4] 多角色并行 LLM 调用延迟** → 使用 FastAPI 异步 + asyncio.gather() 并行调用；场景间可多进程
- **[R5] OpenViking/Kuzu 作为年轻项目的稳定性风险** → 核心逻辑抽象为接口，预留替换能力；数据定期备份
- **[R6] 1M 上下文可能导致 LLM "中间丢失"现象** → 关键信息放在上下文开头和结尾（primacy/recency 效应）；重要指令在结尾重复
- **[R7] Tauri Sidecar 打包复杂度** → PyInstaller 打包 Python 后端，Tauri 负责窗口管理；先跑通纯 Web 模式再打包桌面版
- **[R8] 个人开发者精力有限** → Phase 0 先做最小可用（CLI 或极简 UI），验证引擎质量后再投入前端和打包

## Open Questions

- 文档解析器支持哪些格式？PDF + Markdown + 纯文本？需要支持 .docx 吗？
- 是否需要"版本分支"——用户可以回到之前的剧情节点分叉出不同故事线？
- OpenClaw 整合的深度：仅作为启动器（打开应用），还是深度整合（Agent 自主管理创作流程、定时续写、跨平台发布）？
