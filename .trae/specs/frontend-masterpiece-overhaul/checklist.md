# Amphoreus 前端全面重构 - 验证清单

## 设计系统
- [x] 背景有可见但不突兀的纸张纹理和暗角
- [x] 朱红(chop)色有光泽感，印章效果明显
- [x] 多层阴影系统（内阴影/环境阴影/辉光）
- [x] 动效使用editorial缓动曲线
- [x] Source Serif 4衬线字体作为display字体
- [x] Source Sans 3作为body字体

## 基础组件
- [x] 按钮：hover/active/disabled状态都有反馈
- [x] 输入框：focus光晕效果
- [x] 卡片：hover上浮+边框高亮
- [x] chip选择器：激活状态明确
- [x] badge系统：accent/gold/editor/muted/danger多种变体
- [x] 模态框：backdrop模糊+入场动画
- [x] 空状态：优雅的图标+文案
- [x] 骨架屏：shimmer流光效果

## 侧栏导航
- [x] Logo区印章质感
- [x] 激活导航项发光条指示
- [x] 导航项hover反馈
- [x] 底部主题/语言切换按钮精致

## 页面与动效
- [x] 页面切换page-lift过渡
- [x] stagger-children错落入场动画
- [x] Toast通知滑入/倒计时进度条
- [x] loading动画主题化（inkDrip墨滴）
- [x] 尊重prefers-reduced-motion

## 首页(Projects)
- [x] Hero欢迎区仪式感
- [x] 项目卡片设计精致
- [x] 新建项目入口醒目

## 写作界面(Writer)
- [x] WritingPreview手稿排版（双线边框+页边距+首字下沉）
- [x] 控制面板沉浸感
- [x] ChatPanel对话气泡区分清晰

## 质量分析(Quality)
- [x] 报告卡片专属配色
- [x] 状态点带辉光
- [x] TensionCurve双主题配色

## 通用页面
- [x] 所有页面page-header风格统一
- [x] card/btn/chip使用统一
- [x] 模态框/图表/Feed项视觉一致

## 双主题
- [x] 墨色(ink)主题完整
- [x] 纸色(paper)主题完整
- [x] 主题切换平滑过渡

## 技术验证
- [x] pnpm test 31/31通过
- [x] pnpm build构建成功
- [x] TypeScript类型正确
