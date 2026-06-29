# AMPHOREUS 视觉风格与设计规范

## 1. 设计灵感与整体基调

致敬米哈游《崩坏：星穹铁道》（Honkai: Star Rail）的视觉语言。整体基调是**深空科幻 + 奢华金饰**——深邃的宇宙背景上点缀着精致的金色 UI 元素，营造出一种"在星海中书写史诗"的仪式感。不是冰冷的硬科幻，而是带有浪漫主义色彩的太空幻想。

---

## 2. 色彩体系

### 背景层级（从深到浅）

| 变量 | 色值 | 用途 |
|------|------|------|
| `--bg-primary` | `#0b0d1a` | 最深底色，近乎纯黑的深蓝 |
| `--bg-secondary` | `#111428` | 次级背景 |
| `--bg-tertiary` | `#181c35` | 第三层背景 |
| `--bg-card` | `rgba(20, 24, 50, 0.85)` | 卡片背景，半透明深蓝 |
| `--bg-glass` | `rgba(15, 18, 40, 0.7)` | 毛玻璃面板背景 |
| `--bg-hover` | `rgba(30, 35, 70, 0.9)` | 悬停态背景 |

### 文字层级

| 变量 | 色值 | 用途 |
|------|------|------|
| `--text-primary` | `#e8e6f0` | 主文字，淡紫白 |
| `--text-secondary` | `#a09cb8` | 次要文字，灰紫 |
| `--text-muted` | `#6b6780` | 弱化文字，暗紫灰 |
| `--text-gold` | `#d4a843` | 金色文字 |

### 强调色（6色功能色板）

| 变量 | 色值 | 语义 |
|------|------|------|
| `--accent-gold` | `#d4a843` | 主品牌色，标题/主按钮/选中态/Logo |
| `--accent-gold-light` | `#f0d078` | 金色高光 |
| `--accent-gold-dark` | `#a07820` | 金色暗部 |
| `--accent-blue` | `#4a7fff` | 角色对话、对话事件 |
| `--accent-purple` | `#8b5cf6` | 旁白叙述、记忆系统 |
| `--accent-cyan` | `#38bdf8` | 信息提示 |
| `--accent-green` | `#34d399` | 成功状态、活跃指示 |
| `--accent-pink` | `#f472b6` | 用户干预、危险操作 |
| `--accent-red` | `#f87171` | OOC 警告、终止按钮、错误 |

### 边框层级

| 变量 | 色值 | 用途 |
|------|------|------|
| `--border-color` | `rgba(212, 168, 67, 0.15)` | 默认边框，极淡金 |
| `--border-gold` | `rgba(212, 168, 67, 0.4)` | 强调边框，可见金 |
| `--border-subtle` | `rgba(100, 95, 128, 0.2)` | 弱化边框，灰紫 |

### 辉光

| 变量 | 值 | 用途 |
|------|------|------|
| `--glow-gold` | `0 0 20px rgba(212, 168, 67, 0.2)` | 金色辉光 |
| `--glow-blue` | `0 0 20px rgba(74, 127, 255, 0.2)` | 蓝色辉光 |
| `--glow-purple` | `0 0 20px rgba(139, 92, 246, 0.2)` | 紫色辉光 |

### 渐变

| 变量 | 值 | 用途 |
|------|------|------|
| `--gradient-gold` | `linear-gradient(135deg, #d4a843, #f0d078, #d4a843)` | 主按钮、金色文字 |
| `--gradient-starfield` | `linear-gradient(180deg, #0b0d1a 0%, #111428 30%, #181c35 60%, #0b0d1a 100%)` | 星空背景底色 |
| `--gradient-card` | `linear-gradient(135deg, rgba(20, 24, 50, 0.9), rgba(25, 30, 60, 0.8))` | 卡片渐变 |

---

## 3. 星空背景（Starfield）

整个应用的基础氛围层，由三层构成：

### 渐变底色

```
linear-gradient(180deg, #0b0d1a → #111428 → #181c35 → #0b0d1a)
```

从顶到底再回到深色，形成微妙的明暗过渡。

### 星点层（::before）

10 个 `radial-gradient` 模拟散布的星星，混合四种颜色：

- 金色：`rgba(212, 168, 67, 0.3)`
- 蓝色：`rgba(74, 127, 255, 0.2)`
- 白色：`rgba(255, 255, 255, 0.15)`
- 紫色：`rgba(139, 92, 246, 0.2)`

大小 1px–1.5px，`pointer-events: none` 不阻挡交互。

### 网格层（::after）

极淡的金色网格线 `rgba(212, 168, 67, 0.02)`，60px 间距，营造科幻全息投影感。

---

## 4. 毛玻璃卡片（Glass Card）

核心容器样式 `.glass-card`：

```css
.glass-card {
  background: rgba(20, 24, 50, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(212, 168, 67, 0.15);
  border-radius: 12px;
}
```

悬停态：边框变为 `--border-gold`，加上金色辉光 `box-shadow: 0 0 20px rgba(212, 168, 67, 0.2)`。

---

## 5. 按钮系统

### 主按钮 `.btn-hsr-primary`

```css
.btn-hsr-primary {
  background: linear-gradient(135deg, #d4a843, #f0d078, #d4a843);
  color: #0b0d1a;
  font-weight: 600;
  border-radius: 8px;
  padding: 10px 24px;
  border: none;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}
```

**光泽扫过动画：** `::before` 伪元素是一个从左到右扫过的白色高光条（`translateX(-100%) → translateX(100%)`，0.6s），模拟金属光泽。

**悬停态：** 金色辉光扩散 + 微上浮 `translateY(-1px)`。

### 次按钮 `.btn-hsr-secondary`

- 透明背景，金色文字，金色边框
- 悬停时填充淡金背景 + 辉光

### 危险按钮（终止模拟等）

- 红色系：`bg-[var(--accent-red)]/10` + `border-[var(--accent-red)]/30` + 红色文字
- 悬停加深红色背景

---

## 6. 文字效果

### 金色渐变文字 `.text-gold-gradient`

```css
.text-gold-gradient {
  background: linear-gradient(135deg, #d4a843, #f0d078, #d4a843);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
```

用于 Logo "AMPHOREUS"、页面标题、章节标题。

### 金色辉光文字 `.text-glow-gold`

```css
.text-glow-gold {
  text-shadow: 0 0 20px rgba(212, 168, 67, 0.4);
}
```

用于首页 Hero 区的 Orbit 图标。

---

## 7. 分割线

```css
.divider-hsr {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(212, 168, 67, 0.4), transparent);
  border: none;
}
```

从两端透明渐变到中间金色，优雅的分隔。

---

## 8. 动画

| 类名 | 效果 | 周期 | 用途 |
|------|------|------|------|
| `animate-float` | 上下 6px 缓动浮动 | 4s | 首页装饰轨道环 |
| `animate-gold-pulse` | 金色辉光脉冲（10px–25px 呼吸） | 2s | 宇宙列表活跃状态指示点 |
| `typing-dot` | 三个圆点依次上弹（0s/0.2s/0.4s 延迟） | 1.4s | AI 回复加载态 |
| `fade` | opacity 渐入渐出 | 0.3s | Vue Transition |
| `slide` | 从右侧 20px 滑入 + 渐显 | 0.3s | Vue Transition（模态框） |

---

## 9. 滚动条

```css
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(212, 168, 67, 0.2);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(212, 168, 67, 0.4);
}
```

极细滚动条（5px 宽），轨道透明，滑块为半透明金色。

---

## 10. 布局结构

### 整体框架

左侧固定侧边栏 + 右侧主内容区，`h-screen flex`，`overflow: hidden`。

### 侧边栏（260px / 折叠 56px）

- 毛玻璃背景 `bg-[var(--bg-glass)] backdrop-blur-xl`
- 顶部：AMPHOREUS Logo（金色渐变文字 + Orbit 图标）+ 折叠按钮
- 中部：「开拓新宇宙」虚线按钮 + 宇宙列表（每个宇宙有状态指示点）
- 底部：功能导航（模拟控制台、角色管理、时间线、导出、设置），当前页面高亮为金色背景

### 宇宙状态指示点

| 状态 | 颜色 | 动画 |
|------|------|------|
| draft | `bg-gray-500` | 无 |
| building | `bg-amber-400` | 无 |
| ready | `bg-emerald-400` | 无 |
| simulating | `bg-blue-400` | `animate-gold-pulse` |
| paused | `bg-purple-400` | 无 |
| completed | `bg-indigo-400` | 无 |

### 页面头部（Header）

- 固定在页面顶部，`shrink-0`
- 毛玻璃背景 + 底部金色边框
- 左侧：返回箭头 + Orbit 图标 + 页面标题
- 右侧：操作按钮（启动模拟/终止、导出等）

### 内容区

- `flex-1 overflow-y-auto`，可滚动
- 内边距 `px-6 py-4`，事件流 `space-y-3`

---

## 11. 页面特定设计

### 首页（Home）

- 75vh 高的 Hero 区，居中布局
- 装饰性双圆轨道环（`border-gold` 嵌套圆 + `animate-float`）包裹 Orbit 图标
- 标题 "AMPHOREUS" 使用 `text-6xl font-bold text-gold-gradient`
- 三个功能卡片使用 `glass-card`，图标使用不同色系的渐变背景（琥珀→黄、蓝→靛、紫→粉），悬停时图标放大 `scale-110`
- 底部 "FORGED IN THE STARS" 极小字 `tracking-widest`

### 宇宙构建（Build）

- 聊天界面，用户消息靠右（金色半透明气泡），AI 消息靠左（毛玻璃卡片）
- 进度条显示四个阶段：世界观、角色、地理、历史（星形图标）
- 加载态：三个金色圆点依次跳动

### 模拟控制台（Simulate）

- 左侧主区域：事件流，每条事件左侧有 3px 彩色边框
- 右侧面板（320px）：上方角色列表（紧凑横向卡片），下方记忆系统（关系图谱 Tab + 记忆回溯 Tab）
- 底部输入区：粉色系干预输入框

#### 事件类型边框色

| 事件类型 | CSS 类 | 颜色 |
|----------|--------|------|
| dialogue | `.event-dialogue` | `--accent-blue` |
| narration | `.event-narration` | `--accent-purple` |
| action | `.event-action` | `--accent-gold` |
| intervention | `.event-intervention` | `--accent-pink` |
| system | `.event-system` | `--text-muted` |
| ooc_warning | `.event-ooc-warning` | `--accent-red` |

### 角色管理（Characters）

- 星空背景全屏
- 角色卡片网格（1/2/3 列响应式），每张卡片包含：金色渐变头像（首字）、名称、角色类型、状态徽章、性格/背景/动机描述
- 点击展开外观和能力详情

### 时间线（Timeline）

- 星空背景全屏
- 左侧垂直金色渐变线（`from border-gold via border-color to transparent`）
- 每个事件节点为圆形（4x4），边框颜色对应事件类型
- 玻璃卡片展示事件内容

### 导出（Export）

- 左侧设置面板（320px）：格式选择（小说/剧本，2x2 网格按钮）、风格选择列表、生成按钮
- 右侧预览区：Markdown 内容渲染，`leading-[1.9]` 宽行距

### 设置（Settings）

- 星空背景全屏
- 最大宽度 `max-w-2xl mx-auto` 居中
- 分区用 `.divider-hsr` 分隔：API 密钥、模型配置、保存按钮、关于信息
- 输入框统一样式：深色背景 + 细边框 + 金色 focus 态

---

## 12. 图标系统

使用 `@lucide/vue`（Lucide 图标库），线性风格，与整体精致感匹配。

| 图标 | 用途 |
|------|------|
| `Orbit` | 品牌图标，Logo、页面标题、空状态 |
| `Star` | 宇宙列表项、收藏 |
| `Play` / `Square` | 启动/终止模拟 |
| `Users` | 角色管理 |
| `BookOpen` | 时间线、编年史 |
| `Brain` | 记忆系统 |
| `GitBranch` | 关系图谱 |
| `Swords` | 多 Agent 演绎功能卡片 |
| `Compass` | 演示模式、开拓宇宙 |
| `Send` | 发送消息 |
| `Loader2` | 加载态（配合 `animate-spin`） |
| `ArrowLeft` | 返回 |
| `Settings` | 设置页 |
| `Download` | 导出 |
| `Copy` / `Check` | 复制/已复制 |

---

## 13. 字体

```css
font-family: 'Inter', 'Noto Sans SC', system-ui, -apple-system, sans-serif;
```

- **Inter** — 英文和数字（精致的无衬线）
- **Noto Sans SC** — 中文（清晰的中文字体）
- 标题使用 `tracking-wider` 或 `tracking-wide` 增加字间距
- 标签使用 `uppercase` + `tracking-wider` + 极小字号（10px）
- 正文 `leading-relaxed`（1.625），导出预览 `leading-[1.9]`（更宽松）

---

## 14. 间距与圆角

### 间距

| 场景 | 值 |
|------|------|
| 页面内边距 | `px-6 py-4`（24px / 16px） |
| 卡片内边距 | `p-4` 到 `p-6` |
| 元素间距 | `gap-2` 到 `gap-6` |
| 事件流间距 | `space-y-3` |

### 圆角

| 元素 | 圆角 |
|------|------|
| 卡片 | `rounded-xl`（12px） |
| 按钮 | `rounded-lg`（8px） |
| 输入框 | `rounded-lg`（8px） |
| 小徽章/标签 | `rounded-full` 或 `rounded-md` |

---

## 15. 交互反馈

- 所有可交互元素都有 `transition-all` 或 `transition-colors`（0.3s）
- **悬停态：** 边框变亮、背景变亮、辉光出现、微位移
- **禁用态：** `opacity-40` + `cursor-not-allowed`
- **选中态：** 金色边框 + 金色背景 + 金色辉光（`border-gold-glow`）
- **加载态：** `animate-spin` 旋转图标 或 typing-dot 跳动圆点

---

## 16. 输入框统一样式

```css
input, textarea {
  padding: 10px 16px;
  border-radius: 8px;
  background: rgba(11, 13, 26, 0.8);
  border: 1px solid rgba(100, 95, 128, 0.2);
  color: #e8e6f0;
  transition: all 0.3s;
}

input:focus, textarea:focus {
  border-color: rgba(212, 168, 67, 0.5);
  outline: none;
  box-shadow: 0 0 0 1px rgba(212, 168, 67, 0.2);
}

input::placeholder, textarea::placeholder {
  color: #6b6780;
}
```

---

## 17. 状态徽章

```css
/* 活跃 */
.bg-emerald-400/10 border-emerald-400/20 text-emerald-400

/* 离线 */
.bg-gray-500/10 border-gray-500/20 text-gray-500

/* 陨落 */
.bg-red-400/10 border-red-400/20 text-red-400
```

---

## 18. 模态框

- 遮罩层：`bg-black/70 backdrop-blur-sm`
- 内容区：`glass-card`，`max-w-lg`，居中
- 进入动画：`fade`（遮罩）+ `slide`（内容从右滑入）
- 点击遮罩关闭

---

## 19. 空状态

- 大尺寸图标（`w-16 h-16`）+ `opacity-20` 极淡
- 主文字 `text-base tracking-wide`
- 副文字 `text-sm text-muted`
- 可选：图标后方加 `blur-2xl` 的淡色光晕

---

## 20. 技术栈

| 层 | 技术 |
|----|------|
| 框架 | Vue 3 Composition API + TypeScript |
| 样式 | Tailwind CSS v4（`@tailwindcss/vite` 插件） |
| 图标 | `@lucide/vue`（Lucide 线性图标） |
| 状态管理 | Pinia |
| 路由 | Vue Router 4 |
| 桌面框架 | Tauri v2（Rust 后端） |
| 构建 | Vite |
