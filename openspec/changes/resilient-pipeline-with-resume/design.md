## Context

用户实测 CLI 后发现两大痛点：场景执行无进度反馈、API 额度耗尽后进度丢失。需要场景流式显示 + 断点续传。

## Decisions

### 1. 场景流式显示

**选择**：CLI 改用 `SceneEngine.run_scene_stream()` 替代 `run_scene()`
**理由**：流式 API 已实现，只需 CLI 消费。每轮对话实时打印，用户立即看到角色互动。

### 2. LLM 错误分类

在 `LLMClient` 中捕获 OpenAI SDK 异常并归类：

| 异常类型 | 错误码 | 用户提示 |
|---------|--------|---------|
| `insufficient_quota` / 402 | `QUOTA_EXHAUSTED` | "API 额度已用尽" |
| `rate_limit` / 429 | `RATE_LIMITED` | "请求过快，已自动等待重试" |
| `timeout` / 网络错误 | `NETWORK_ERROR` | "网络错误，自动重试中" |
| 其他 | `UNKNOWN` | 显示原始错误 |

`chat_json()` 内置重试逻辑：配额错误不重试（避免浪费），网络/超时自动重试 3 次。

### 3. 细粒度保存

每次 API 调用成功后立即保存 CLI 会话状态。新增 `last_step` 枚举：

```
"world_started" → "world_rules" → "world_locations" → "world_done"
→ "characters_generated" → "relationships_done" → "plot_done"
→ "scene_{scene_id}_round_{n}" → "writing_done"
```

### 4. 断点恢复

CLI 启动时检测 `last_step`：
- `world_started` 或更早：从世界构建恢复
- `world_done`：跳过世界构建，从角色生成继续
- `characters_generated`：跳过世界+角色，继续关系推断
- `scene_xxx_round_n`：重新加载已完成场景，从中断的场景继续
- `writing_done`：从导出步骤继续
