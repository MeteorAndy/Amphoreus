# Amphoreus 前端全面重构 - The Implementation Plan (Decomposed and Prioritized Task List)

## [x] Task 1: 升级设计Token系统与全局视觉氛围
- **Priority**: high
- **Depends On**: None
- **Acceptance Criteria Addressed**: AC-1, AC-8, NFR-1
- **Status**: 完成 - @theme扩展至250+行，包括多层级颜色、阴影系统、动效曲线、排版尺度、装饰元素类、双主题变量

## [x] Task 2: 重构基础组件样式系统
- **Priority**: high
- **Depends On**: Task 1
- **Acceptance Criteria Addressed**: AC-3, NFR-4
- **Status**: 完成 - btn/input/card/chip/badge/modal/tooltip/stepper/skeleton/error-banner/empty-state全量重构，添加manuscript-rail、drop-cap、seal-glow等主题类

## [x] Task 3: 重构侧栏导航AppLayout
- **Priority**: high
- **Depends On**: Task 2
- **Acceptance Criteria Addressed**: AC-2
- **Status**: 完成 - 印章Logo(BookOpen渐变+seal-glow)、发光导航项(左侧条+渐变背景)、分组标签装饰、底部控制按钮精致化

## [x] Task 4: 增强页面过渡与动效系统
- **Priority**: high
- **Depends On**: Task 2
- **Acceptance Criteria Addressed**: AC-4
- **Status**: 完成 - page-lift过渡增强、stagger-children/fade-in-up工具类、inkDrip墨滴/brush-stroke笔触关键帧、微交互动效、prefers-reduced-motion支持

## [x] Task 5: 升级Toast通知组件
- **Priority**: medium
- **Depends On**: Task 4
- **Acceptance Criteria Addressed**: AC-3, AC-4
- **Status**: 完成 - 渐变色条+图标容器+圆环倒计时进度条+slideIn+scaleOut动画+hover暂停

## [x] Task 6: 重构ProjectsView首页
- **Priority**: high
- **Depends On**: Task 3, Task 4
- **Acceptance Criteria Addressed**: AC-5
- **Status**: 完成 - hero欢迎区(大印章BookOpen+font-display标题+rule-ornament装饰)、项目卡片升级(渐变图标+阶段彩色徽章+hover上浮+chop-glow光晕)、shimmer骨架屏、FolderOpen空状态

## [x] Task 7: 升级WriterView写作界面
- **Priority**: high
- **Depends On**: Task 4
- **Acceptance Criteria Addressed**: AC-6
- **Status**: 完成 - WritingPreview手稿排版(朱红双线边框+大页边距+章节首字下沉drop-cap+装饰分隔+inkDrip loading)、WriterView控制面板chip统一化+btn-lg生成按钮+stagger入场

## [x] Task 8: 升级ChatPanel对话面板
- **Priority**: medium
- **Depends On**: Task 4
- **Acceptance Criteria Addressed**: AC-3
- **Status**: 完成 - 用户消息(朱红渐变+非对称圆角+阴影)、AI消息(ink-elevated+反向圆角)、系统消息(金色斜体)、inkDrip小点loading、消息fadeInUp动画

## [x] Task 9: 优化QualityView质量分析界面
- **Priority**: high
- **Depends On**: Task 4
- **Acceptance Criteria Addressed**: AC-7
- **Status**: 完成 - ShieldCheck印章masthead、10种报告专属配色(圆形图标容器+顶部色条+辉光)、dot-pass/warn/fail状态点带辉光、TensionCurve双主题配色、空状态装饰

## [x] Task 10: 优化其他工作台页面
- **Priority**: medium
- **Depends On**: Task 4
- **Acceptance Criteria Addressed**: AC-3, NFR-4
- **Status**: 完成 - WorldBuilder/Character/Plot/Scene视图统一印章图标头部+font-display标题+rule-ornament分隔+card/chip/btn类+fade-in-up入场

## [x] Task 11: 优化Sandbox/Interactive/Pipeline页面
- **Priority**: medium
- **Depends On**: Task 8, Task 10
- **Acceptance Criteria Addressed**: AC-3
- **Status**: 完成 - Pipeline step progress优化、Sandbox FlaskConical金色图标+stylized布局、Interactive MessageSquare金色头部

## [x] Task 12: 升级通用组件与细节打磨
- **Priority**: medium
- **Depends On**: All previous tasks
- **Acceptance Criteria Addressed**: AC-3, NFR-4
- **Status**: 完成 - CharacterCard/DirectorPanel/PlotTimeline/RelationshipGraph/SceneFeed/EnvironmentPanel/SandboxFeedItem/SkeletonCard/模态框类全量升级，统一card/chip/btn/badge/input类，添加入场动画

## [x] Task 13: 完善浅色主题与最终验证
- **Priority**: high
- **Depends On**: All previous tasks
- **Acceptance Criteria Addressed**: AC-8, AC-9, AC-10, AC-11, NFR-1, NFR-2, NFR-3
- **Status**: 完成 - pnpm test 31/31通过、pnpm build构建成功、双主题完整CSS变量覆盖、全局theme-transition
