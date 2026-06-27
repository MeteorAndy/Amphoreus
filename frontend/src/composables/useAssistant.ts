import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export interface AssistantAction {
  id: string
  label: string
  icon?: string
  description?: string
  primary?: boolean
  handler: () => void
}

export interface AssistantSuggestion {
  text: string
  action: () => void
}

export interface PageContext {
  pageId: string
  title: string
  subtitle?: string
  tips?: string[]
  actions?: AssistantAction[]
  suggestions?: AssistantSuggestion[]
}

export interface AssistantMessage {
  id: string
  role: 'assistant' | 'user' | 'system' | 'action'
  content: string
  actions?: AssistantAction[]
  timestamp: number
}

let msgCounter = 0
function genId(): string {
  msgCounter += 1
  return 'assistant-msg-' + Date.now() + '-' + msgCounter
}

const HELP_RESPONSES: Record<string, string> = {
  help: '我是 Amphoreus AI 助手，可以帮你：\n- 快速跳转到各创作阶段\n- 触发当前页面常用操作\n- 了解各阶段功能说明\n\n直接点击下方的建议问题或快捷操作开始吧。',
  project: '项目页是你的创作起点。点击"新建项目"开始一个新故事，或从已有项目继续。\n\n推荐路径：\n1. 一键生成 - 自动完成世界-角色-剧情-场景-初稿\n2. 互动创作 - 引导式对话，一步步打磨细节\n3. 叙事写作 - 如果你已有大纲，直接进入写作',
  pipeline: '一键生成是全自动流水线：\n\n世界观 -> 角色 -> 关系网络 -> 剧情架构 -> 场景演绎 -> 初稿生成\n\n适合想快速看到完整初稿时使用，过程中你可以随时暂停和调整。',
  interactive: '互动创作是引导式创作流程：\n\n从一个灵感种子出发，AI会引导你：\n1. 对话式完善世界观\n2. 生成并编辑角色\n3. 选择结构模板生成剧情\n4. 逐场景模拟角色对话\n5. 转换成小说/剧本正文\n\n每一步都可以对话调整和手动编辑。',
  world: '世界构建是故事舞台搭建：\n\n- 可上传PDF/Word/TXT参考文档\n- 通过对话描述你的想法\n- AI整理成结构化设定：规则、地点、势力、时间线\n- 完成后可直接进入角色或剧情阶段',
  characters: '角色管理展示所有已创建角色：\n\n- 自动生成角色档案\n- 支持手动编辑角色信息\n- 力导向图可视化关系网络\n- 查询任意两个角色间的关系路径',
  plot: '剧情架构基于经典叙事结构：\n\n支持模板：三幕式 / 英雄之旅 / 救猫咪 / 起承转合\n\n- AI生成大纲后可增删场景、调整顺序\n- 可对话式润色某一幕剧情\n- 完成后进入场景演绎或直接写作',
  scene: '场景执行是故事演绎台：\n\n- 选择场景后AI模拟角色对话和行动\n- WebSocket实时推送演绎结果\n- 可以干预场景走向，跳过或重做\n- 全部场景完成后进入叙事写作',
  writer: '叙事写作把大纲转换成正文：\n\n- 选择小说或剧本格式\n- 选择叙事视角（第一/第三人称）\n- 选择视角角色\n- 散文质量增强让文笔更细腻\n- 生成后提供多个候选标题\n- 导出为Markdown或Fountain格式',
  quality: '质量审稿台（Guardian）分析文本质量：\n\n10+维度评估：情节逻辑、人物一致性、节奏张力、对话质量、描写质量等\n\n给出评分和具体修改建议，可反复修改审稿。',
  export: '导出功能：\n\n- 小说 -> Markdown (.md)\n- 剧本 -> Fountain (.fountain)\n\n导出按钮在叙事写作页面右上角，Fountain格式可导入Final Draft、WriterSolo等专业编剧软件。',
  tip: '小贴士：\n- 拖拽右侧面板边缘调整宽度\n- 双击分隔条重置宽度\n- 侧栏底部按钮切换纸色/墨色主题\n- 右上角按钮可折叠AI面板节省空间',
}

const messages = ref<AssistantMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const currentContext = ref<PageContext>({ pageId: 'unknown', title: '', actions: [] })
const pageActions = ref<AssistantAction[]>([])
const pageSuggestions = ref<AssistantSuggestion[]>([])
const eventHandlers = new Map<string, Set<(payload?: unknown) => void>>()

function pushMessage(msg: Omit<AssistantMessage, 'id' | 'timestamp'>): void {
  messages.value.push({ ...msg, id: genId(), timestamp: Date.now() })
}

export function useAssistant() {
  const route = useRoute()
  const router = useRouter()

  function nav(p: string) {
    return () => router.push(p)
  }

  function pushHelpReply(key: string): void {
    pushMessage({ role: 'user', content: key === 'help' ? '帮助' : key === 'tip' ? '小贴士' : key })
    loading.value = true
    setTimeout(() => {
      const reply = HELP_RESPONSES[key] || '我暂时无法回答这个问题，试试点击下方的建议操作。'
      pushMessage({ role: 'assistant', content: reply })
      loading.value = false
    }, 400)
  }

  function getRouteSuggestions(path: string): AssistantSuggestion[] {
    const base: AssistantSuggestion[] = [
      { text: '如何开始创作？', action: () => pushHelpReply('help') },
      { text: '使用小贴士', action: () => pushHelpReply('tip') },
    ]
    const pageMap: Record<string, AssistantSuggestion[]> = {
      '/projects': [
        { text: '一键生成完整故事', action: nav('/pipeline') },
        { text: '从互动创作开始', action: nav('/interactive') },
        { text: '直接进入写作', action: nav('/writer') },
        { text: '项目页说明', action: () => pushHelpReply('project') },
      ],
      '/pipeline': [
        { text: '改用互动创作', action: nav('/interactive') },
        { text: '直接去叙事写作', action: nav('/writer') },
        { text: '一键生成说明', action: () => pushHelpReply('pipeline') },
      ],
      '/interactive': [
        { text: '世界构建说明', action: () => pushHelpReply('world') },
        { text: '角色生成说明', action: () => pushHelpReply('characters') },
        { text: '剧情架构说明', action: () => pushHelpReply('plot') },
        { text: '互动创作说明', action: () => pushHelpReply('interactive') },
      ],
      '/world': [
        { text: '去管理角色', action: nav('/characters') },
        { text: '去搭建剧情', action: nav('/plot') },
        { text: '世界构建说明', action: () => pushHelpReply('world') },
      ],
      '/characters': [
        { text: '去搭建剧情', action: nav('/plot') },
        { text: '回到世界构建', action: nav('/world') },
        { text: '角色管理说明', action: () => pushHelpReply('characters') },
      ],
      '/plot': [
        { text: '去执行场景', action: nav('/scene') },
        { text: '直接生成正文', action: nav('/writer') },
        { text: '剧情架构说明', action: () => pushHelpReply('plot') },
      ],
      '/scene': [
        { text: '生成叙事文本', action: nav('/writer') },
        { text: '审稿评估质量', action: nav('/quality') },
        { text: '场景执行说明', action: () => pushHelpReply('scene') },
      ],
      '/writer': [
        { text: '前往质量审稿', action: nav('/quality') },
        { text: '返回项目列表', action: nav('/projects') },
        { text: '如何导出作品？', action: () => pushHelpReply('export') },
        { text: '叙事写作说明', action: () => pushHelpReply('writer') },
      ],
      '/quality': [
        { text: '返回修改正文', action: nav('/writer') },
        { text: '返回项目', action: nav('/projects') },
        { text: '质量审稿说明', action: () => pushHelpReply('quality') },
      ],
    }
    for (const prefix of Object.keys(pageMap)) {
      if (path.startsWith(prefix)) return [...pageSuggestions.value, ...pageMap[prefix], ...base]
    }
    return [...pageSuggestions.value, ...base]
  }

  const suggestions = computed(() => getRouteSuggestions(route.path))

  function matchPageContext(path: string): PageContext {
    const PAGE_CONTEXTS: Record<string, Omit<PageContext, 'actions' | 'suggestions'>> = {
      '/projects': {
        pageId: 'projects',
        title: '我的项目',
        subtitle: '创作的起点',
        tips: ['点击"新建项目"开始新故事', '也可以通过"互动创作"引导式创建'],
      },
      '/pipeline': {
        pageId: 'pipeline',
        title: '一键生成',
        subtitle: '自动流水线：世界-角色-剧情-场景-初稿',
        tips: ['适合快速看到完整初稿', '可随时暂停和中途调整'],
      },
      '/interactive': {
        pageId: 'interactive',
        title: '互动创作',
        subtitle: '引导式对话创作',
        tips: ['从一个灵感开始，对话逐步完善', '世界、角色、剧情、场景一步到位'],
      },
      '/world': {
        pageId: 'world',
        title: '世界构建',
        subtitle: '搭建你的故事舞台',
        tips: ['可上传PDF/Word/TXT参考文档', '对话式逐步完善设定'],
      },
      '/characters': {
        pageId: 'characters',
        title: '角色管理',
        subtitle: '人物档案与关系网络',
        tips: ['查看角色关系力导向图', '查询任意两个角色间的关系路径'],
      },
      '/plot': {
        pageId: 'plot',
        title: '剧情架构',
        subtitle: '三幕式/英雄之旅/救猫咪',
        tips: ['选择结构模板生成大纲', '可对话润色单幕剧情'],
      },
      '/scene': {
        pageId: 'scene',
        title: '场景执行',
        subtitle: 'AI模拟角色对话与行动',
        tips: ['WebSocket实时推送演绎结果', '可干预场景走向'],
      },
      '/writer': {
        pageId: 'writer',
        title: '叙事写作',
        subtitle: '大纲转换为小说/剧本正文',
        tips: ['选择叙事视角和视角角色', '增强散文质量让文笔更细腻', '生成后候选标题任选'],
      },
      '/quality': {
        pageId: 'quality',
        title: '质量审稿',
        subtitle: '10+维度质量评估',
        tips: ['情节逻辑、人物一致性、节奏张力', '给出评分和具体修改建议'],
      },
      '/sandbox': {
        pageId: 'sandbox',
        title: '沙盒推演',
        subtitle: '自由场景推演实验',
        tips: ['选择角色和初始场景自由推演', '可注入事件观察故事走向'],
      },
    }

    for (const prefix of Object.keys(PAGE_CONTEXTS)) {
      if (path.startsWith(prefix)) {
        const ctx = PAGE_CONTEXTS[prefix]
        return {
          ...ctx,
          actions: [...pageActions.value],
          suggestions: [...pageSuggestions.value],
        }
      }
    }
    return {
      pageId: 'unknown',
      title: 'Amphoreus',
      subtitle: '故事创作引擎',
      tips: [],
      actions: [...pageActions.value],
      suggestions: [...pageSuggestions.value],
    }
  }

  function updateContext(path: string): void {
    pageActions.value = []
    pageSuggestions.value = []
    const ctx = matchPageContext(path)
    currentContext.value = ctx
    if (messages.value.length === 0) {
      pushWelcomeMessage(ctx)
    } else {
      pushMessage({
        role: 'system',
        content: '已切换到' + ctx.title + (ctx.subtitle ? ' - ' + ctx.subtitle : ''),
      })
    }
  }

  function pushWelcomeMessage(ctx: PageContext): void {
    const welcome = ctx.pageId === 'projects' || ctx.pageId === 'unknown'
      ? '你好，我是 Amphoreus AI 助手。\n\n我会根据你当前所在的创作阶段提供引导和快捷操作。你可以随时向我提问，或点击下方建议开始。'
      : '欢迎来到' + ctx.title + (ctx.subtitle ? ' - ' + ctx.subtitle : '') + '。\n\n' + (ctx.tips ?? []).map((t, i) => (i + 1) + '. ' + t).join('\n')
    pushMessage({ role: 'assistant', content: welcome, actions: ctx.actions })
  }

  function sendMessage(text: string): void {
    const trimmed = text.trim()
    if (!trimmed || loading.value) return
    pushMessage({ role: 'user', content: trimmed })
    loading.value = true

    setTimeout(() => {
      let reply = '我理解你的意思，但目前我主要提供页面导航和快捷操作支持。\n\n你可以尝试点击下方的建议按钮，或描述你想做什么（如"去写作"、"查看角色"、"一键生成"）。'

      if (/帮助|help|怎么用|如何|开始/.test(trimmed)) {
        reply = HELP_RESPONSES.help
      } else if (/贴士|tip|技巧|小技巧/.test(trimmed)) {
        reply = HELP_RESPONSES.tip
      } else if (/项目|project|首页|我的项目/.test(trimmed)) {
        reply = HELP_RESPONSES.project
      } else if (/一键|流水线|pipeline|自动|生成完整|完整故事/.test(trimmed)) {
        reply = HELP_RESPONSES.pipeline
      } else if (/互动|引导|interactive|对话创作/.test(trimmed)) {
        reply = HELP_RESPONSES.interactive
      } else if (/世界|设定|世界观|world|舞台/.test(trimmed)) {
        reply = HELP_RESPONSES.world
      } else if (/角色|人物|character|关系/.test(trimmed)) {
        reply = HELP_RESPONSES.characters
      } else if (/剧情|大纲|plot|结构|三幕|英雄/.test(trimmed)) {
        reply = HELP_RESPONSES.plot
      } else if (/场景|scene|演绎|模拟|对话/.test(trimmed)) {
        reply = HELP_RESPONSES.scene
      } else if (/导出|export|下载|保存/.test(trimmed)) {
        reply = HELP_RESPONSES.export
      } else if (/质量|审稿|guardian|评估|评分|修改建议/.test(trimmed)) {
        reply = HELP_RESPONSES.quality
      } else if (/写作|正文|writer|小说|剧本|写/.test(trimmed)) {
        reply = HELP_RESPONSES.writer
      } else if (/去|跳转|打开|进入|导航/.test(trimmed)) {
        const navMap: Array<[RegExp, string, string]> = [
          [/项目|首页/, '/projects', '项目页'],
          [/一键|流水线|pipeline/, '/pipeline', '一键生成'],
          [/互动|interactive/, '/interactive', '互动创作'],
          [/世界|world/, '/world', '世界构建'],
          [/角色|character/, '/characters', '角色管理'],
          [/剧情|plot/, '/plot', '剧情架构'],
          [/场景|scene/, '/scene', '场景执行'],
          [/写作|writer|正文/, '/writer', '叙事写作'],
          [/质量|审稿|guardian/, '/quality', '质量审稿'],
        ]
        let navigated = false
        for (const [pattern, path, name] of navMap) {
          if (pattern.test(trimmed)) {
            router.push(path)
            reply = '好的，正在带你前往' + name + '...'
            navigated = true
            break
          }
        }
        if (!navigated) {
          reply = '你想去哪里？可以说"去写作"、"去角色"、"去一键生成"等。'
        }
      }

      pushMessage({ role: 'assistant', content: reply })
      loading.value = false
    }, 500)
  }

  function registerPageAction(action: AssistantAction): () => void {
    if (!pageActions.value.find((a) => a.id === action.id)) {
      pageActions.value.push(action)
    }
    currentContext.value.actions = [...pageActions.value]
    return () => {
      pageActions.value = pageActions.value.filter((a) => a.id !== action.id)
      currentContext.value.actions = [...pageActions.value]
    }
  }

  function registerPageSuggestion(suggestion: AssistantSuggestion): () => void {
    if (!pageSuggestions.value.find((s) => s.text === suggestion.text)) {
      pageSuggestions.value.push(suggestion)
    }
    return () => {
      pageSuggestions.value = pageSuggestions.value.filter((s) => s.text !== suggestion.text)
    }
  }

  function clearMessages(): void {
    messages.value = []
    pushWelcomeMessage(currentContext.value)
  }

  function triggerEvent(name: string, payload?: unknown): void {
    const handlers = eventHandlers.get(name)
    if (handlers) handlers.forEach((h) => h(payload))
  }

  function onEvent(name: string, handler: (payload?: unknown) => void): () => void {
    if (!eventHandlers.has(name)) eventHandlers.set(name, new Set())
    eventHandlers.get(name)!.add(handler)
    return () => {
      eventHandlers.get(name)?.delete(handler)
    }
  }

  watch(
    () => route.path,
    (path) => updateContext(path),
    { immediate: true },
  )

  return {
    messages,
    inputText,
    loading,
    currentContext,
    suggestions,
    pageActions,
    sendMessage,
    registerPageAction,
    registerPageSuggestion,
    clearMessages,
    triggerEvent,
    onEvent,
  }
}
