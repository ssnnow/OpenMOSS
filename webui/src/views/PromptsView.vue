<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { marked } from 'marked'
import { promptsApi, adminRuleApi } from '@/api/client'
import type { AgentPromptMeta, PromptTemplate } from '@/api/client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Plus, Copy, Pencil, Trash2, FileText, Check, Loader2,
  ChevronLeft, Code, Eye, ChevronRight, Download,
  Compass, Zap, SearchCheck, ShieldCheck, Bot,
  Users, ScrollText, LayoutTemplate,
} from 'lucide-vue-next'

// ── 状态 ────────────────────────────────────────────────
const loading = ref(true)
const agents = ref<AgentPromptMeta[]>([])
const templates = ref<PromptTemplate[]>([])

// 视图模式
const mode = ref<'list' | 'create' | 'edit' | 'preview' | 'template' | 'agent-view'>('list')
const editSlug = ref('')
const form = ref({
  slug: '',
  name: '',
  role: '',
  description: '',
})

// 创建/编辑的两个文本域
const promptContent = ref('')
const onboardingContent = ref('')
const isRoleLoading = ref(false)

// 角色切换确认弹窗
const showRoleConfirm = ref(false)
const roleConfirmTarget = ref('')
const roleConfirmPrevious = ref('')

// 删除确认弹窗
const showDeleteConfirm = ref(false)
const deleteTarget = ref('')

// 模板查看/编辑
const templateForm = ref({ role: '', content: '', filename: '' })
const templateEditing = ref(false)

// 组合预览
const composedPrompt = ref('')
const copied = ref(false)
const previewMode = ref<'rendered' | 'source'>('rendered')

// 操作中
const saving = ref(false)
const deleting = ref('')

// 消息
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

function showMessage(text: string, type: 'success' | 'error' = 'success') {
  message.value = text
  messageType.value = type
  setTimeout(() => { message.value = '' }, 3000)
}


// ── 全局规则 ──────────────────────────────────────────
interface RuleItem {
  id: string
  scope: string
  content: string
  created_at?: string
  updated_at?: string
}

const rules = ref<RuleItem[]>([])
const rulesLoading = ref(false)
const ruleSaving = ref(false)
const ruleDeleting = ref('')

// 规则编辑器弹窗（统一用于新建和编辑）
const showRuleEditor = ref(false)
const ruleEditorId = ref<string | null>(null)  // null = 新建模式
const ruleEditorContent = ref('')
const ruleEditorPreviewMode = ref<'split' | 'edit' | 'preview'>('split')

// 渲染规则编辑器的预览
const renderedRulePreview = computed(() => {
  if (!ruleEditorContent.value) return ''
  return marked(ruleEditorContent.value) as string
})

// 删除规则确认弹窗
const showRuleDeleteConfirm = ref(false)
const ruleDeleteTarget = ref('')

async function loadRules() {
  rulesLoading.value = true
  try {
    const { data } = await adminRuleApi.list('global')
    rules.value = data
  } catch (e) {
    console.error('加载规则失败', e)
  } finally {
    rulesLoading.value = false
  }
}

function openRuleEditor(rule?: RuleItem) {
  ruleEditorId.value = rule?.id ?? null
  ruleEditorContent.value = rule?.content ?? ''
  ruleEditorPreviewMode.value = 'split'
  showRuleEditor.value = true
}

function closeRuleEditor() {
  showRuleEditor.value = false
  ruleEditorId.value = null
  ruleEditorContent.value = ''
}

async function saveRuleEditor() {
  if (!ruleEditorContent.value.trim()) return
  ruleSaving.value = true
  try {
    if (ruleEditorId.value) {
      // 编辑模式
      await adminRuleApi.update(ruleEditorId.value, ruleEditorContent.value)
      showMessage('规则已更新')
    } else {
      // 新建模式
      await adminRuleApi.create({ scope: 'global', content: ruleEditorContent.value })
      showMessage('规则已创建')
    }
    closeRuleEditor()
    await loadRules()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showMessage(err.response?.data?.detail || '保存失败', 'error')
  } finally {
    ruleSaving.value = false
  }
}

function confirmRuleDelete(id: string) {
  ruleDeleteTarget.value = id
  showRuleDeleteConfirm.value = true
}

async function doRuleDelete() {
  showRuleDeleteConfirm.value = false
  const id = ruleDeleteTarget.value
  ruleDeleting.value = id
  try {
    await adminRuleApi.delete(id)
    showMessage('规则已删除')
    await loadRules()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showMessage(err.response?.data?.detail || '删除失败', 'error')
  } finally {
    ruleDeleting.value = ''
  }
}

// ── 角色选项 ────────────────────────────────────────────
const roleOptions = [
  { value: 'planner', label: '规划者 Planner' },
  { value: 'executor', label: '执行者 Executor' },
  { value: 'reviewer', label: '审查者 Reviewer' },
  { value: 'patrol', label: '巡查者 Patrol' },
]

const roleLabel = (role: string) =>
  roleOptions.find(r => r.value === role)?.label || role

const templateDescriptions: Record<string, string> = {
  'planner': '负责任务拆解与规划，将大目标分解为可执行的子任务',
  'executor': '负责具体执行任务，产出内容、代码或操作结果',
  'reviewer': '负责审核执行结果，确保产出质量达标',
  'patrol': '负责系统巡查和异常检测，维护运行稳定性',
}

// 必需角色配置
const requiredRoles = [
  { role: 'planner', label: '规划者 Planner', desc: '拆解任务、制定计划、分配子任务', single: true },
  { role: 'reviewer', label: '审查者 Reviewer', desc: '审核执行者产出，通过或打回返工', single: true },
  { role: 'patrol', label: '巡查者 Patrol', desc: '系统巡查、异常检测、维护稳定', single: true },
  { role: 'executor', label: '执行者 Executor', desc: '实际执行子任务，可创建多个不同专长的执行者', single: false },
]

// 角色状态检查
const roleStatus = computed(() => {
  return requiredRoles.map(r => ({
    ...r,
    count: agents.value.filter(a => a.role === r.role).length,
    done: agents.value.some(a => a.role === r.role),
  }))
})

const hasMissingRoles = computed(() => roleStatus.value.some(r => !r.done))

// 按角色分组，每组内按创建时间倒序
const groupedAgents = computed(() => {
  const groups: Record<string, AgentPromptMeta[]> = {}
  for (const a of agents.value) {
    const key = a.role || '未知'
    if (!groups[key]) groups[key] = []
    groups[key].push(a)
  }
  // 每组按 created_at 倒序
  for (const key of Object.keys(groups)) {
    groups[key]?.sort((a, b) => {
      const ta = a.created_at || ''
      const tb = b.created_at || ''
      return tb.localeCompare(ta)
    })
  }
  return groups
})

// ── Markdown 渲染 ────────────────────────────────────────
const renderedMarkdown = computed(() => {
  if (!composedPrompt.value) return ''
  return marked(composedPrompt.value) as string
})

const renderedTemplateContent = computed(() => {
  if (!templateForm.value.content) return ''
  return marked(templateForm.value.content) as string
})

const agentViewData = ref({ slug: '', name: '', role: '', description: '', content: '' })
const renderedAgentContent = computed(() => {
  if (!agentViewData.value.content) return ''
  return marked(agentViewData.value.content) as string
})

// 编辑器实时预览：提示词 + 对接指引合并
const fullEditorContent = computed(() => {
  const parts: string[] = []
  if (promptContent.value.trim()) parts.push(promptContent.value.trim())
  if (onboardingContent.value.trim()) parts.push(onboardingContent.value.trim())
  return parts.join('\n\n---\n\n')
})

const renderedEditorPreview = computed(() => {
  if (!fullEditorContent.value) return ''
  return marked(fullEditorContent.value) as string
})

const editorCopied = ref(false)

// ── 数据加载 ─────────────────────────────────────────────
async function loadData() {
  loading.value = true
  try {
    const [agentsRes, templatesRes] = await Promise.all([
      promptsApi.listAgents(),
      promptsApi.listTemplates(),
    ])
    agents.value = agentsRes.data
    templates.value = templatesRes.data
  } catch {
    showMessage('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
  loadRules()
})

// ── 角色切换 → 自动加载模板和对接指引 ────────────────────
async function loadRoleContent(role: string) {
  isRoleLoading.value = true
  try {
    const templateRes = await promptsApi.getTemplate(role)
    promptContent.value = templateRes.data.content
  } catch {
    promptContent.value = ''
  }
  try {
    const onboardingRes = await promptsApi.getOnboarding(role)
    onboardingContent.value = onboardingRes.data.content
  } catch {
    onboardingContent.value = ''
  }
  isRoleLoading.value = false
}

function handleRoleChange(event: Event) {
  const newRole = (event.target as HTMLSelectElement).value
  if (!newRole) return

  // 如果已有内容，弹出自定义确认框
  if (form.value.role && promptContent.value.trim()) {
    roleConfirmPrevious.value = form.value.role
    roleConfirmTarget.value = newRole
    // 先恢复 select 的值（因为 v-model 已经改了）
    form.value.role = roleConfirmPrevious.value
    showRoleConfirm.value = true
    return
  }

  form.value.role = newRole
  loadRoleContent(newRole)
}

function confirmRoleSwitch() {
  showRoleConfirm.value = false
  form.value.role = roleConfirmTarget.value
  loadRoleContent(roleConfirmTarget.value)
}

function cancelRoleSwitch() {
  showRoleConfirm.value = false
}

// ── 新建 ────────────────────────────────────────────
function startCreate(presetRole?: string) {
  form.value = { slug: '', name: '', role: presetRole || '', description: '' }
  promptContent.value = ''
  onboardingContent.value = ''
  mode.value = 'create'
  if (presetRole) {
    loadRoleContent(presetRole)
  }
}

async function handleCreate() {
  if (!form.value.slug || !form.value.name || !form.value.role || !promptContent.value) {
    showMessage('请填写必填项', 'error')
    return
  }
  saving.value = true
  try {
    await promptsApi.createAgent({
      slug: form.value.slug,
      name: form.value.name,
      role: form.value.role,
      description: form.value.description,
      content: fullEditorContent.value,
    })
    showMessage('创建成功')
    mode.value = 'list'
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showMessage(err.response?.data?.detail || '创建失败', 'error')
  } finally {
    saving.value = false
  }
}

// ── 编辑 ────────────────────────────────────────────────
// ONBOARDING_MARKER 已在一键复制区声明

async function startEdit(slug: string) {
  try {
    const { data } = await promptsApi.getAgent(slug)
    editSlug.value = slug
    form.value = {
      slug: data.slug,
      name: data.name,
      role: data.role,
      description: data.description,
    }

    // 拆分内容：如果包含对接指引标记，分到两个文本域
    const content = data.content
    const markerIdx = content.indexOf(ONBOARDING_MARKER)
    if (markerIdx > 0) {
      // 找到标记前的分隔线 ---
      let splitIdx = markerIdx
      const before = content.substring(0, markerIdx)
      const lastSep = before.lastIndexOf('---')
      if (lastSep > 0) splitIdx = lastSep

      promptContent.value = content.substring(0, splitIdx).trim()
      onboardingContent.value = content.substring(markerIdx).trim()
    } else {
      promptContent.value = content
      // 自动生成对接指引
      try {
        const { data: ob } = await promptsApi.getOnboarding(data.role)
        onboardingContent.value = ob.content
      } catch {
        onboardingContent.value = ''
      }
    }

    mode.value = 'edit'
  } catch {
    showMessage('加载失败', 'error')
  }
}

async function handleUpdate() {
  saving.value = true
  try {
    await promptsApi.updateAgent(editSlug.value, {
      name: form.value.name,
      role: form.value.role,
      description: form.value.description,
      content: fullEditorContent.value,
    })
    showMessage('保存成功')
    mode.value = 'list'
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showMessage(err.response?.data?.detail || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// ── 删除 ────────────────────────────────────────────────

async function handleDelete(slug: string, event: Event) {
  event.stopPropagation()
  deleteTarget.value = slug
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  showDeleteConfirm.value = false
  const slug = deleteTarget.value
  deleting.value = slug
  try {
    await promptsApi.deleteAgent(slug)
    showMessage('已删除')
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showMessage(err.response?.data?.detail || '删除失败', 'error')
  } finally {
    deleting.value = ''
  }
}

// ── 模板查看/编辑 ────────────────────────────────────────
async function openTemplate(role: string) {
  try {
    const { data } = await promptsApi.getTemplate(role)
    templateForm.value = { role: data.role, content: data.content, filename: data.filename }
    templateEditing.value = false
    mode.value = 'template'
  } catch {
    showMessage('加载模板失败', 'error')
  }
}

async function saveTemplate() {
  saving.value = true
  try {
    await promptsApi.updateTemplate(templateForm.value.role, templateForm.value.content)
    showMessage('模板已保存')
    templateEditing.value = false
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showMessage(err.response?.data?.detail || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// ── Agent 查看 ───────────────────────────────────────────
async function openAgentView(slug: string) {
  try {
    const { data } = await promptsApi.getAgent(slug)
    agentViewData.value = {
      slug: data.slug,
      name: data.name,
      role: data.role,
      description: data.description,
      content: data.content,
    }
    mode.value = 'agent-view'
  } catch {
    showMessage('加载失败', 'error')
  }
}

// ── 一键复制 ─────────────────────────────────────────────
const previewRole = ref('')

const roleLabels: Record<string, string> = {
  planner: '规划者',
  executor: '执行者',
  reviewer: '审查者',
  patrol: '巡查者',
}

const ONBOARDING_MARKER = '## 🔧 平台对接'

// 从 composedPrompt 中提取对接指引部分
const onboardingSection = computed(() => {
  const idx = composedPrompt.value.indexOf(ONBOARDING_MARKER)
  if (idx < 0) return ''
  return composedPrompt.value.substring(idx).trim()
})

// 生成 OpenClaw 快速复制前缀
function buildQuickCopyPrefix(role: string): string {
  const label = roleLabels[role] || role
  return (
    `🦞 **OpenClaw 快速对接** — 请按以下步骤完成配置：\n\n` +
    `1. 将下方「角色提示词」**完整替换**到你的 **AGENTS.md**（角色：${label}）\n` +
    `2. 根据新的 AGENTS.md 内容，自行更新你的 **SOUL.md**（提炼核心身份和行为准则）\n` +
    `3. 按底部「平台对接」指引完成注册，获取 API Key\n` +
    `4. 按指引下载并保存 Skill 工具包\n` +
    `5. 完成后**删除**底部「平台对接」部分，只保留角色提示词\n\n` +
    `---\n\n`
  )
}

async function showCompose(slug: string) {
  composedPrompt.value = ''
  copied.value = false
  previewMode.value = 'rendered'
  // 查找 agent 的 role
  const agent = agents.value.find(a => a.slug === slug)
  previewRole.value = agent?.role || ''
  try {
    const { data } = await promptsApi.compose(slug)
    composedPrompt.value = data.prompt
    editSlug.value = slug
    mode.value = 'preview'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    showMessage(err.response?.data?.detail || '生成失败', 'error')
  }
}

// 🦞 OpenClaw 快速复制（带前缀引导）
const lobsterCopied = ref(false)
async function copyWithPrefix() {
  try {
    const text = buildQuickCopyPrefix(previewRole.value) + composedPrompt.value
    await navigator.clipboard.writeText(text)
    lobsterCopied.value = true
    showMessage('🦞 已复制（含对接引导）')
    setTimeout(() => { lobsterCopied.value = false }, 2000)
  } catch {
    showMessage('复制失败，请手动选中复制', 'error')
  }
}

// 普通复制（仅提示词）
async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(composedPrompt.value)
    copied.value = true
    showMessage('已复制到剪贴板')
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    showMessage('复制失败，请手动选中复制', 'error')
  }
}

// 复制平台对接指引
const onboardingCopied = ref(false)
async function copyOnboarding() {
  if (!onboardingSection.value) {
    showMessage('未找到对接指引内容', 'error')
    return
  }
  try {
    await navigator.clipboard.writeText(onboardingSection.value)
    onboardingCopied.value = true
    showMessage('已复制平台对接指引')
    setTimeout(() => { onboardingCopied.value = false }, 2000)
  } catch {
    showMessage('复制失败', 'error')
  }
}

async function copyEditorContent() {
  try {
    await navigator.clipboard.writeText(fullEditorContent.value)
    editorCopied.value = true
    showMessage('已复制到剪贴板')
    setTimeout(() => { editorCopied.value = false }, 2000)
  } catch {
    showMessage('复制失败', 'error')
  }
}


function goBack() {
  mode.value = 'list'
}
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">

    <!-- 消息提示 -->
    <Transition name="toast">
      <div v-if="message"
        class="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2.5 rounded-xl px-5 py-3 text-sm font-medium shadow-xl ring-1 ring-black/5 backdrop-blur-md"
        :class="messageType === 'success'
          ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/90 dark:text-emerald-200'
          : 'bg-red-50 text-red-800 dark:bg-red-950/90 dark:text-red-200'">
        <span class="text-base">{{ messageType === 'success' ? '✅' : '❌' }}</span>
        {{ message }}
      </div>
    </Transition>

    <!-- 视图过渡动画 -->
    <Transition name="view" mode="out-in" appear>

      <div v-if="mode === 'list'" key="list" class="space-y-4 max-w-5xl mx-auto">

        <Tabs default-value="agents" class="w-full">
          <TabsList class="w-full justify-start bg-muted/50 p-1 h-auto gap-1">
            <TabsTrigger value="agents"
              class="text-xs px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm flex items-center gap-1.5">
              <Users class="h-3.5 w-3.5" />
              Agent 对接
              <span class="text-muted-foreground">({{ agents.length }})</span>
            </TabsTrigger>
            <TabsTrigger value="rules"
              class="text-xs px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm flex items-center gap-1.5">
              <ScrollText class="h-3.5 w-3.5" />
              全局规则
              <span class="text-muted-foreground">({{ rules.length }})</span>
            </TabsTrigger>
            <TabsTrigger value="templates"
              class="text-xs px-4 py-2 data-[state=active]:bg-background data-[state=active]:shadow-sm flex items-center gap-1.5">
              <LayoutTemplate class="h-3.5 w-3.5" />
              角色模板
            </TabsTrigger>
          </TabsList>

          <!-- Tab: Agent 对接 -->
          <TabsContent value="agents" class="mt-5 space-y-5">

            <!-- 标题 + 进度 + 新建 -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <h2 class="text-xl font-bold">Agent 对接</h2>
                <div v-if="!loading && hasMissingRoles"
                  class="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 rounded-full px-2.5 py-1">
                  <div class="h-1.5 w-10 rounded-full bg-muted overflow-hidden">
                    <div class="h-full rounded-full bg-emerald-500 transition-all duration-500"
                      :style="{ width: `${(roleStatus.filter(r => r.done).length / roleStatus.length) * 100}%` }" />
                  </div>
                  {{roleStatus.filter(r => r.done).length}}/{{ roleStatus.length }} 角色
                </div>
              </div>
              <Button @click="startCreate()">
                <Plus class="mr-1.5 h-4 w-4" />
                新建提示词
              </Button>
            </div>

            <!-- 缺失角色 -->
            <div v-if="!loading && hasMissingRoles" class="flex items-center gap-2 flex-wrap text-sm">
              <span class="text-muted-foreground text-xs">缺少以下角色，点击可快速创建：</span>
              <template v-for="r in roleStatus.filter(r => !r.done)" :key="r.role">
                <button
                  class="inline-flex items-center gap-1.5 rounded-full border border-dashed px-3 py-1 text-xs font-medium transition-all duration-200 hover:shadow-sm"
                  :class="{
                    'border-blue-300 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950': r.role === 'planner',
                    'border-amber-300 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950': r.role === 'executor',
                    'border-purple-300 text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-950': r.role === 'reviewer',
                    'border-emerald-300 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950': r.role === 'patrol',
                  }"
                  @click="startCreate(r.role)">
                  <Compass v-if="r.role === 'planner'" class="h-3 w-3" />
                  <Zap v-else-if="r.role === 'executor'" class="h-3 w-3" />
                  <SearchCheck v-else-if="r.role === 'reviewer'" class="h-3 w-3" />
                  <ShieldCheck v-else-if="r.role === 'patrol'" class="h-3 w-3" />
                  {{ r.label }}
                  <Plus class="h-3 w-3 opacity-50" />
                </button>
              </template>
              <span v-for="r in roleStatus.filter(r => r.done)" :key="'done-' + r.role"
                class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
                :class="{
                  'bg-blue-500/10 text-blue-600 dark:text-blue-400': r.role === 'planner',
                  'bg-amber-500/10 text-amber-600 dark:text-amber-400': r.role === 'executor',
                  'bg-purple-500/10 text-purple-600 dark:text-purple-400': r.role === 'reviewer',
                  'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400': r.role === 'patrol',
                }">
                <Check class="h-3 w-3" />
                {{ r.role === 'planner' ? '规划者' : r.role === 'reviewer' ? '审查者' : r.role === 'patrol' ? '巡查者' :
                  `执行者×${r.count}` }}
              </span>
            </div>

            <!-- 使用说明 -->
            <details class="group" :open="(agents.length === 0 || hasMissingRoles) || undefined">
              <summary
                class="flex items-center gap-1.5 cursor-pointer text-xs text-muted-foreground hover:text-foreground transition-colors select-none list-none [&::-webkit-details-marker]:hidden">
                <ChevronRight class="h-3.5 w-3.5 transition-transform group-open:rotate-90" />
                使用说明
              </summary>
              <Card class="mt-2 bg-muted/30 border-dashed">
                <CardContent class="py-3 px-4 text-sm text-muted-foreground leading-relaxed space-y-2.5">
                  <p>管理 Agent 提示词，hover 翻转卡片查看详情和操作按钮。</p>
                  <div class="rounded-md bg-primary/5 border border-primary/20 px-3 py-2.5 space-y-1.5">
                    <p><strong class="text-foreground">OpenClaw 对接</strong></p>
                    <p>1. 点击 🦞 <strong class="text-foreground">快速复制</strong>，内容已包含完整对接引导</p>
                    <p>2. 发送给 Agent，它会自动完成：替换 AGENTS.md → 更新 SOUL.md → 注册 → 下载 Skill</p>
                    <p>3. 已有提示词的 Agent，可用「<strong class="text-foreground">Agent 入职包</strong>」单独补发注册 + Skill 指引</p>
                  </div>
                  <p><strong class="text-foreground">其他平台</strong> — 使用普通「复制」按钮，自行配置即可。</p>
                </CardContent>
              </Card>
            </details>

            <!-- 加载中 -->
            <div v-if="loading" class="flex justify-center py-16">
              <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
            </div>

            <!-- 空状态 -->
            <Card v-else-if="agents.length === 0" class="border-dashed">
              <CardContent class="flex flex-col items-center justify-center py-16 text-center">
                <FileText class="h-14 w-14 text-muted-foreground/40 mb-4" />
                <p class="text-lg font-semibold text-muted-foreground">还没有 Agent 提示词</p>
                <p class="text-sm text-muted-foreground mt-1.5 max-w-sm">
                  创建提示词后，可以复制并发送给 Agent 完成对接
                </p>
                <Button class="mt-5" @click="startCreate()">
                  <Plus class="mr-1.5 h-4 w-4" />
                  创建第一个
                </Button>
              </CardContent>
            </Card>

            <!-- Agent 翻转卡片（按角色分组） -->
            <div v-else class="space-y-8">
              <div v-for="(items, role) in groupedAgents" :key="role" class="space-y-4">
                <h3 class="text-sm font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <span class="inline-block w-2 h-2 rounded-full" :class="{
                    'bg-blue-500': role === 'planner',
                    'bg-amber-500': role === 'executor',
                    'bg-purple-500': role === 'reviewer',
                    'bg-emerald-500': role === 'patrol',
                    'bg-muted-foreground': !['planner','executor','reviewer','patrol'].includes(String(role)),
                  }" />
                  {{ roleLabel(String(role)) }}
                  <span class="text-xs font-normal">({{ items.length }})</span>
                </h3>

                <!-- 卡片网格 -->
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  <div v-for="item in items" :key="item.slug" class="flip-card" style="perspective: 1200px;">
                    <div class="flip-card-inner relative w-full" style="transform-style: preserve-3d;"
                      :style="{ minHeight: '200px' }">

                      <!-- 正面 -->
                      <div class="flip-card-front absolute inset-0 rounded-xl border bg-card overflow-hidden flex flex-col"
                        style="backface-visibility: hidden;">
                        <!-- 顶部渐变条 -->
                        <div class="h-1.5" :class="{
                          'bg-gradient-to-r from-blue-400 to-indigo-500': item.role === 'planner',
                          'bg-gradient-to-r from-amber-400 to-orange-500': item.role === 'executor',
                          'bg-gradient-to-r from-violet-400 to-purple-500': item.role === 'reviewer',
                          'bg-gradient-to-r from-emerald-400 to-teal-500': item.role === 'patrol',
                          'bg-gradient-to-r from-gray-400 to-gray-500': !['planner','executor','reviewer','patrol'].includes(item.role),
                        }" />
                        <div class="p-5 flex flex-col justify-between flex-1">
                          <div>
                            <div class="flex items-start justify-between">
                              <!-- 图标圆形 -->
                              <div class="h-11 w-11 rounded-xl flex items-center justify-center shadow-sm" :class="{
                                'bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-950 dark:to-indigo-900': item.role === 'planner',
                                'bg-gradient-to-br from-amber-50 to-orange-100 dark:from-amber-950 dark:to-orange-900': item.role === 'executor',
                                'bg-gradient-to-br from-violet-50 to-purple-100 dark:from-violet-950 dark:to-purple-900': item.role === 'reviewer',
                                'bg-gradient-to-br from-emerald-50 to-teal-100 dark:from-emerald-950 dark:to-teal-900': item.role === 'patrol',
                                'bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800': !['planner','executor','reviewer','patrol'].includes(item.role),
                              }">
                                <Compass v-if="item.role === 'planner'" class="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                <Zap v-else-if="item.role === 'executor'" class="h-5 w-5 text-amber-600 dark:text-amber-400" />
                                <SearchCheck v-else-if="item.role === 'reviewer'" class="h-5 w-5 text-purple-600 dark:text-purple-400" />
                                <ShieldCheck v-else-if="item.role === 'patrol'" class="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                                <Bot v-else class="h-5 w-5 text-gray-600 dark:text-gray-400" />
                              </div>
                              <!-- 状态标签 -->
                              <div class="flex gap-1">
                                <span v-if="item.example"
                                  class="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-600 border border-blue-500/20 font-medium">
                                  示例
                                </span>
                                <span v-if="item.status === 'unconfigured'"
                                  class="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-500/10 text-yellow-600 border border-yellow-500/20 font-medium">
                                  未配置
                                </span>
                              </div>
                            </div>
                            <h4 class="text-lg font-bold mt-3 truncate">{{ item.name || item.slug }}</h4>
                            <p class="text-xs text-muted-foreground mt-1 truncate">{{ item.description || item.filename }}</p>
                          </div>
                          <div class="flex items-center justify-between mt-3">
                            <span class="text-xs px-2.5 py-1 rounded-full font-medium" :class="{
                              'bg-blue-500/10 text-blue-600 dark:text-blue-400': item.role === 'planner',
                              'bg-amber-500/10 text-amber-600 dark:text-amber-400': item.role === 'executor',
                              'bg-purple-500/10 text-purple-600 dark:text-purple-400': item.role === 'reviewer',
                              'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400': item.role === 'patrol',
                            }">{{ roleLabel(item.role) }}</span>
                            <span class="text-[10px] text-muted-foreground/40 italic">hover →</span>
                          </div>
                        </div>
                      </div>

                      <!-- 背面 -->
                      <div class="flip-card-back absolute inset-0 rounded-xl border bg-card overflow-hidden flex flex-col"
                        style="backface-visibility: hidden; transform: rotateY(180deg);">
                        <!-- 顶部彩条 -->
                        <div class="h-1.5" :class="{
                          'bg-gradient-to-r from-blue-400 to-indigo-500': item.role === 'planner',
                          'bg-gradient-to-r from-amber-400 to-orange-500': item.role === 'executor',
                          'bg-gradient-to-r from-violet-400 to-purple-500': item.role === 'reviewer',
                          'bg-gradient-to-r from-emerald-400 to-teal-500': item.role === 'patrol',
                          'bg-gradient-to-r from-gray-400 to-gray-500': !['planner','executor','reviewer','patrol'].includes(item.role),
                        }" />
                        <div class="p-5 flex flex-col justify-between flex-1">
                          <div class="space-y-2 flex-1 overflow-hidden">
                            <div class="flex items-center gap-2">
                              <h4 class="text-sm font-bold truncate">{{ item.name || item.slug }}</h4>
                              <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium" :class="{
                                'bg-blue-500/10 text-blue-600': item.role === 'planner',
                                'bg-amber-500/10 text-amber-600': item.role === 'executor',
                                'bg-purple-500/10 text-purple-600': item.role === 'reviewer',
                                'bg-emerald-500/10 text-emerald-600': item.role === 'patrol',
                              }">{{ roleLabel(item.role) }}</span>
                            </div>
                            <p class="text-xs text-muted-foreground leading-relaxed line-clamp-4">
                              {{ item.description || '暂无描述' }}
                            </p>
                            <p class="text-[10px] text-muted-foreground/50 font-mono truncate pt-1">{{ item.filename }}</p>
                          </div>
                          <div class="flex items-center gap-1.5 pt-3 border-t border-border/40 mt-2">
                            <Button size="sm" class="flex-1 h-7 text-xs bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white border-0 shadow-sm"
                              @click.stop="showCompose(item.slug)">
                              <span class="mr-1">🦞</span> 快速复制
                            </Button>
                            <Button variant="outline" size="icon" class="h-7 w-7" title="查看"
                              @click.stop="openAgentView(item.slug)">
                              <Eye class="h-3 w-3" />
                            </Button>
                            <Button variant="outline" size="icon" class="h-7 w-7" title="编辑"
                              @click.stop="startEdit(item.slug)">
                              <Pencil class="h-3 w-3" />
                            </Button>
                            <Button variant="ghost" size="icon" class="h-7 w-7" title="删除"
                              :disabled="deleting === item.slug"
                              @click.stop="handleDelete(item.slug, $event)">
                              <Loader2 v-if="deleting === item.slug" class="h-3 w-3 animate-spin" />
                              <Trash2 v-else class="h-3 w-3 text-destructive/70" />
                            </Button>
                          </div>
                        </div>
                      </div>

                    </div>
                  </div>
                </div>
              </div>
            </div>

          </TabsContent>

          <!-- Tab: 全局规则 -->
          <TabsContent value="rules" class="mt-4 space-y-4">
            <!-- 加载中 -->
            <div v-if="rulesLoading" class="flex justify-center py-12">
              <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
            </div>

            <template v-else>
              <!-- 空状态 -->
              <Card v-if="rules.length === 0" class="border-dashed">
                <CardContent class="flex flex-col items-center justify-center py-12 text-center">
                  <FileText class="h-12 w-12 text-muted-foreground/50 mb-4" />
                  <p class="text-lg font-medium text-muted-foreground">暂无全局规则</p>
                  <p class="text-sm text-muted-foreground mt-1">
                    Agent 每次执行任务时会通过 API 获取全局规则，用于约束行为规范
                  </p>
                  <Button class="mt-4" variant="outline" @click="openRuleEditor()">
                    <Plus class="mr-1.5 h-4 w-4" />
                    创建全局规则
                  </Button>
                </CardContent>
              </Card>

              <!-- 已有规则（只允许一条） -->
              <template v-if="rules.length > 0">
                <Card v-for="rule in rules" :key="rule.id"
                  class="transition-all duration-200 hover:shadow-sm">
                  <CardContent class="p-4">
                    <div class="flex items-start gap-3">
                      <!-- 内容 -->
                      <div class="flex-1 min-w-0 prose prose-sm dark:prose-invert max-w-none"
                        v-html="marked(rule.content)" />
                      <!-- 操作按钮（始终可见） -->
                      <div class="flex items-center gap-1 flex-shrink-0">
                        <Button variant="ghost" size="icon" class="h-7 w-7" title="编辑"
                          @click="openRuleEditor(rule)">
                          <Pencil class="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" class="h-7 w-7" title="删除"
                          :disabled="ruleDeleting === rule.id" @click="confirmRuleDelete(rule.id)">
                          <Loader2 v-if="ruleDeleting === rule.id" class="h-3.5 w-3.5 animate-spin" />
                          <Trash2 v-else class="h-3.5 w-3.5 text-destructive/70" />
                        </Button>
                      </div>
                    </div>
                    <p v-if="rule.updated_at" class="text-xs text-muted-foreground mt-2 opacity-50">
                      更新于 {{ rule.updated_at }}
                    </p>
                  </CardContent>
                </Card>
              </template>
            </template>
          </TabsContent>

          <!-- Tab: 角色模板 -->
          <TabsContent value="templates" class="mt-5 space-y-5">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-xl font-bold">角色模板</h2>
                <p class="text-sm text-muted-foreground mt-0.5">
                  定义每种角色的通用行为规范，新建提示词时自动填入
                </p>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div v-for="tmpl in templates" :key="tmpl.role"
                class="group cursor-pointer rounded-xl border bg-card overflow-hidden transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5"
                @click="openTemplate(tmpl.role)">
                <!-- 顶部渐变条 -->
                <div class="h-1.5" :class="{
                  'bg-gradient-to-r from-blue-400 to-indigo-500': tmpl.role === 'planner',
                  'bg-gradient-to-r from-amber-400 to-orange-500': tmpl.role === 'executor',
                  'bg-gradient-to-r from-violet-400 to-purple-500': tmpl.role === 'reviewer',
                  'bg-gradient-to-r from-emerald-400 to-teal-500': tmpl.role === 'patrol',
                  'bg-gradient-to-r from-gray-400 to-gray-500': !['planner','executor','reviewer','patrol'].includes(tmpl.role),
                }" />
                <div class="p-5 flex items-start gap-4">
                  <!-- 图标 -->
                  <div class="h-12 w-12 rounded-xl flex items-center justify-center shadow-sm flex-shrink-0" :class="{
                    'bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-950 dark:to-indigo-900': tmpl.role === 'planner',
                    'bg-gradient-to-br from-amber-50 to-orange-100 dark:from-amber-950 dark:to-orange-900': tmpl.role === 'executor',
                    'bg-gradient-to-br from-violet-50 to-purple-100 dark:from-violet-950 dark:to-purple-900': tmpl.role === 'reviewer',
                    'bg-gradient-to-br from-emerald-50 to-teal-100 dark:from-emerald-950 dark:to-teal-900': tmpl.role === 'patrol',
                    'bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800': !['planner','executor','reviewer','patrol'].includes(tmpl.role),
                  }">
                    <Compass v-if="tmpl.role === 'planner'" class="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    <Zap v-else-if="tmpl.role === 'executor'" class="h-6 w-6 text-amber-600 dark:text-amber-400" />
                    <SearchCheck v-else-if="tmpl.role === 'reviewer'" class="h-6 w-6 text-purple-600 dark:text-purple-400" />
                    <ShieldCheck v-else-if="tmpl.role === 'patrol'" class="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                    <Bot v-else class="h-6 w-6 text-gray-600 dark:text-gray-400" />
                  </div>
                  <!-- 文本 -->
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <p class="text-base font-bold">{{ roleLabel(tmpl.role) || tmpl.role }}</p>
                      <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium" :class="{
                        'bg-blue-500/10 text-blue-600': tmpl.role === 'planner',
                        'bg-amber-500/10 text-amber-600': tmpl.role === 'executor',
                        'bg-purple-500/10 text-purple-600': tmpl.role === 'reviewer',
                        'bg-emerald-500/10 text-emerald-600': tmpl.role === 'patrol',
                      }">{{ tmpl.filename }}</span>
                    </div>
                    <p class="text-xs text-muted-foreground mt-1.5 leading-relaxed">
                      {{ templateDescriptions[tmpl.role] || '通用角色模板' }}
                    </p>
                  </div>
                  <!-- 箭头 -->
                  <ChevronRight class="h-4 w-4 text-muted-foreground/30 group-hover:text-muted-foreground transition-colors flex-shrink-0 mt-1" />
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>

      </div>

      <!-- ============================================================ -->
      <!-- 模板查看/编辑 -->
      <!-- ============================================================ -->
      <div v-else-if="mode === 'template'" key="template" class="space-y-4 max-w-5xl mx-auto">
        <div class="flex items-center gap-3">
          <Button variant="ghost" size="icon" @click="goBack">
            <ChevronLeft class="h-5 w-5" />
          </Button>
          <div class="flex-1">
            <h1 class="text-2xl font-bold">{{ roleLabel(templateForm.role) }}</h1>
            <p class="text-sm text-muted-foreground">
              {{ templateDescriptions[templateForm.role] || templateForm.filename }}
            </p>
          </div>
          <Button v-if="!templateEditing" variant="outline" @click="templateEditing = true">
            <Pencil class="mr-1.5 h-4 w-4" />
            编辑
          </Button>
          <div v-else class="flex gap-2">
            <Button variant="outline" @click="templateEditing = false">取消</Button>
            <Button @click="saveTemplate" :disabled="saving">
              <Loader2 v-if="saving" class="mr-1.5 h-4 w-4 animate-spin" />
              {{ saving ? '保存中...' : '保存' }}
            </Button>
          </div>
        </div>

        <Card>
          <CardContent class="p-0">
            <textarea v-if="templateEditing" v-model="templateForm.content"
              class="w-full min-h-[500px] p-6 text-sm font-mono bg-background border-0 rounded-lg resize-y focus:outline-none focus:ring-0" />
            <div v-else class="p-6 prose prose-sm dark:prose-invert max-w-none" v-html="renderedTemplateContent" />
          </CardContent>
        </Card>
      </div>

      <!-- ============================================================ -->
      <!-- Agent 提示词查看 -->
      <!-- ============================================================ -->
      <div v-else-if="mode === 'agent-view'" key="agent-view" class="space-y-4 max-w-5xl mx-auto">
        <div class="flex items-center gap-3">
          <Button variant="ghost" size="icon" @click="goBack">
            <ChevronLeft class="h-5 w-5" />
          </Button>
          <div class="flex-1">
            <h1 class="text-2xl font-bold">{{ agentViewData.name || agentViewData.slug }}</h1>
            <p class="text-sm text-muted-foreground">
              {{ roleLabel(agentViewData.role) }} · {{ agentViewData.description }}
            </p>
          </div>
          <Button variant="outline" @click="showCompose(agentViewData.slug)">
            <span class="mr-1.5">🦞</span>
            OpenClaw 快速复制
          </Button>
          <Button variant="outline" @click="startEdit(agentViewData.slug)">
            <Pencil class="mr-1.5 h-4 w-4" />
            编辑
          </Button>
        </div>

        <Card>
          <CardContent class="p-0">
            <div class="p-6 prose prose-sm dark:prose-invert max-w-none max-h-[70vh] overflow-y-auto"
              v-html="renderedAgentContent" />
          </CardContent>
        </Card>
      </div>

      <!-- ============================================================ -->
      <!-- 新建 / 编辑  —— 左右分栏布局 -->
      <!-- ============================================================ -->
      <div v-else-if="mode === 'create' || mode === 'edit'" :key="mode">
        <!-- 顶部栏 -->
        <div class="flex items-center gap-3 mb-4">
          <Button variant="ghost" size="icon" @click="goBack">
            <ChevronLeft class="h-5 w-5" />
          </Button>
          <h1 class="text-2xl font-bold flex-1">{{ mode === 'create' ? '新建提示词' : '编辑提示词' }}</h1>
          <Button variant="outline" @click="goBack">取消</Button>
          <Button @click="mode === 'create' ? handleCreate() : handleUpdate()" :disabled="saving">
            <Loader2 v-if="saving" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ saving ? '保存中...' : '保存' }}
          </Button>
        </div>

        <!-- 角色选择 -->
        <div class="space-y-2 mb-4">
          <Label class="text-xs">角色模板 *</Label>
          <div class="grid grid-cols-4 gap-2">
            <button v-for="opt in roleOptions" :key="opt.value" type="button"
              class="flex items-center gap-2 rounded-lg border px-3 py-2.5 text-xs font-medium transition-all duration-200"
              :class="form.role === opt.value ? {
                'border-blue-400 bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-600 shadow-sm': opt.value === 'planner',
                'border-amber-400 bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-600 shadow-sm': opt.value === 'executor',
                'border-purple-400 bg-purple-50 text-purple-700 dark:bg-purple-950 dark:text-purple-300 dark:border-purple-600 shadow-sm': opt.value === 'reviewer',
                'border-emerald-400 bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-600 shadow-sm': opt.value === 'patrol',
              } : 'border-border hover:bg-muted/50 text-muted-foreground hover:text-foreground'"
              @click="handleRoleChange({ target: { value: opt.value } } as any)">
              <div class="h-7 w-7 rounded-md flex items-center justify-center flex-shrink-0" :class="form.role === opt.value ? {
                'bg-blue-100 dark:bg-blue-900': opt.value === 'planner',
                'bg-amber-100 dark:bg-amber-900': opt.value === 'executor',
                'bg-purple-100 dark:bg-purple-900': opt.value === 'reviewer',
                'bg-emerald-100 dark:bg-emerald-900': opt.value === 'patrol',
              } : 'bg-muted/50'">
                <Compass v-if="opt.value === 'planner'" class="h-3.5 w-3.5" />
                <Zap v-else-if="opt.value === 'executor'" class="h-3.5 w-3.5" />
                <SearchCheck v-else-if="opt.value === 'reviewer'" class="h-3.5 w-3.5" />
                <ShieldCheck v-else-if="opt.value === 'patrol'" class="h-3.5 w-3.5" />
                <Bot v-else class="h-3.5 w-3.5" />
              </div>
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- 元信息行 -->
        <div class="grid grid-cols-3 gap-3 mb-4">
          <div class="space-y-1">
            <Label for="p-name" class="text-xs">显示名称 *</Label>
            <Input id="p-name" v-model="form.name" placeholder="示例：AI酱瓜" class="h-9" />
          </div>
          <div class="space-y-1">
            <Label for="p-slug" class="text-xs">标识名（文件名） *</Label>
            <Input id="p-slug" v-model="form.slug" placeholder="示例：jianggua" :disabled="mode === 'edit'" class="h-9" />
          </div>
          <div class="space-y-1">
            <Label for="p-desc" class="text-xs">简介</Label>
            <Input id="p-desc" v-model="form.description" placeholder="示例：新媒体写手" class="h-9" />
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="isRoleLoading" class="flex justify-center py-12">
          <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
        </div>

        <!-- 左右分栏 -->
        <div v-else class="grid grid-cols-2 gap-4" style="height: calc(100vh - 220px);">
          <!-- 左侧：编辑 -->
          <div class="flex flex-col gap-3 min-h-0">
            <!-- 提示词内容 -->
            <div class="flex flex-col space-y-1" style="flex: 2;">
              <Label class="text-xs text-muted-foreground flex-shrink-0">
                📝 提示词内容
                <span v-if="form.role" class="text-primary ml-1">
                  (已基于「{{ roleLabel(form.role) }}」模板)
                </span>
              </Label>
              <textarea v-model="promptContent"
                class="flex-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none min-h-0"
                placeholder="选择角色后将自动填入模板内容，你可以在此基础上修改..." />
            </div>

            <!-- 平台对接指引 -->
            <div class="flex flex-col space-y-1" style="flex: 1;">
              <Label class="text-xs text-muted-foreground flex-shrink-0">🔧 平台对接指引（自动生成，可修改）</Label>
              <textarea v-model="onboardingContent"
                class="flex-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none min-h-0"
                placeholder="选择角色后将自动生成对接指引..." />
            </div>
          </div>

          <!-- 右侧：实时预览 -->
          <div class="flex flex-col min-h-0">
            <div class="flex items-center justify-between mb-1 flex-shrink-0">
              <Label class="text-xs text-muted-foreground">👁 完整提示词预览</Label>
              <Button size="sm" variant="ghost" class="h-7 text-xs" @click="copyEditorContent">
                <Check v-if="editorCopied" class="mr-1 h-3 w-3" />
                <Copy v-else class="mr-1 h-3 w-3" />
                {{ editorCopied ? '已复制' : '复制' }}
              </Button>
            </div>
            <Card class="flex-1 overflow-hidden min-h-0">
              <CardContent class="p-0 h-full">
                <div v-if="fullEditorContent"
                  class="p-4 prose prose-sm dark:prose-invert max-w-none h-full overflow-y-auto"
                  v-html="renderedEditorPreview" />
                <div v-else class="flex items-center justify-center h-full text-sm text-muted-foreground">
                  选择角色后将在此显示预览
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <!-- 角色切换确认弹窗 -->
        <Transition name="view">
          <div v-if="showRoleConfirm"
            class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <Card class="w-full max-w-sm shadow-xl">
              <CardContent class="p-6 space-y-4">
                <div>
                  <h3 class="text-lg font-semibold">切换角色模板</h3>
                  <p class="text-sm text-muted-foreground mt-2">
                    切换将用「{{ roleLabel(roleConfirmTarget) }}」的模板覆盖当前已编辑的内容，无法撤销。
                  </p>
                </div>
                <div class="flex justify-end gap-2">
                  <Button variant="outline" @click="cancelRoleSwitch">取消</Button>
                  <Button variant="destructive" @click="confirmRoleSwitch">确定切换</Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </Transition>
      </div>

      <!-- ============================================================ -->
      <!-- 预览 / 一键复制（含 Markdown 渲染切换） -->
      <!-- ============================================================ -->
      <div v-else-if="mode === 'preview'" key="preview" class="space-y-5 max-w-5xl mx-auto">

        <!-- 标题行 -->
        <div class="flex items-center gap-3">
          <Button variant="ghost" size="icon" @click="goBack">
            <ChevronLeft class="h-5 w-5" />
          </Button>
          <div class="flex-1">
            <h1 class="text-2xl font-bold">完整提示词预览</h1>
            <p class="text-sm text-muted-foreground mt-0.5">
              {{ editSlug }} · 角色模板 + 专属内容 + 平台对接指引
            </p>
          </div>
          <Button variant="outline" size="sm" @click="startEdit(editSlug)">
            <Pencil class="mr-1.5 h-3.5 w-3.5" />
            编辑
          </Button>
        </div>

        <!-- 操作栏：复制按钮组 + 视图切换 -->
        <div class="flex items-center justify-between rounded-xl border bg-muted/20 px-4 py-3">
          <!-- 左：复制按钮组 -->
          <TooltipProvider :delay-duration="200">
            <div class="flex items-center gap-2">
              <!-- 🦞 OpenClaw 快速复制 — 主按钮 -->
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button @click="copyWithPrefix"
                    :class="lobsterCopied
                      ? 'bg-emerald-500 hover:bg-emerald-600 text-white border-emerald-500'
                      : 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white border-0 shadow-md shadow-orange-500/20'"
                    class="transition-all duration-300">
                    <Check v-if="lobsterCopied" class="mr-1.5 h-4 w-4" />
                    <span v-else class="mr-1.5 text-base leading-none">🦞</span>
                    {{ lobsterCopied ? '已复制 ✓' : 'OpenClaw 快速复制' }}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p>含完整对接引导，发给 Agent 后自动完成：</p>
                  <p>更新提示词 → 注册 → 下载 Skill</p>
                </TooltipContent>
              </Tooltip>

              <div class="w-px h-6 bg-border" />

              <!-- 普通复制 -->
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button variant="outline" size="sm" @click="copyToClipboard"
                    :class="copied ? 'border-emerald-500 text-emerald-600' : ''">
                    <Check v-if="copied" class="mr-1 h-3.5 w-3.5" />
                    <Copy v-else class="mr-1 h-3.5 w-3.5" />
                    {{ copied ? '已复制' : '复制' }}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  仅复制提示词内容，不含对接引导
                </TooltipContent>
              </Tooltip>

              <!-- Agent 入职包 -->
              <Tooltip v-if="onboardingSection">
                <TooltipTrigger as-child>
                  <Button variant="outline" size="sm" @click="copyOnboarding"
                    :class="onboardingCopied ? 'border-emerald-500 text-emerald-600' : ''">
                    <Check v-if="onboardingCopied" class="mr-1 h-3.5 w-3.5" />
                    <Download v-else class="mr-1 h-3.5 w-3.5" />
                    {{ onboardingCopied ? '已复制' : 'Agent 入职包' }}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  仅复制注册 + Skill 下载指引，发给已有提示词的 Agent 完成对接
                </TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>

          <!-- 右：视图切换 -->
          <div class="flex items-center border rounded-lg overflow-hidden">
            <button class="px-3 py-1.5 text-xs flex items-center gap-1.5 transition-colors"
              :class="previewMode === 'rendered' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
              @click="previewMode = 'rendered'">
              <Eye class="h-3.5 w-3.5" />
              预览
            </button>
            <button class="px-3 py-1.5 text-xs flex items-center gap-1.5 transition-colors"
              :class="previewMode === 'source' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
              @click="previewMode = 'source'">
              <Code class="h-3.5 w-3.5" />
              源码
            </button>
          </div>
        </div>

        <!-- 内容区 -->
        <Card>
          <CardContent class="p-0">
            <div v-if="previewMode === 'rendered'"
              class="p-6 prose prose-sm dark:prose-invert max-w-none max-h-[70vh] overflow-y-auto"
              v-html="renderedMarkdown" />
            <pre v-else
              class="p-6 text-sm whitespace-pre-wrap break-words font-mono max-h-[70vh] overflow-y-auto bg-muted/30 rounded-lg">{{ composedPrompt }}</pre>
          </CardContent>
        </Card>

        <!-- 底部说明 -->
        <div class="grid grid-cols-3 gap-3">
          <div class="flex items-start gap-2 rounded-lg border border-orange-500/20 bg-orange-500/5 px-3 py-2.5">
            <span class="text-base leading-none mt-0.5">🦞</span>
            <div>
              <p class="text-xs font-medium text-foreground">快速复制</p>
              <p class="text-xs text-muted-foreground mt-0.5">含对接引导，发给 Agent 一键完成配置</p>
            </div>
          </div>
          <div class="flex items-start gap-2 rounded-lg border bg-muted/30 px-3 py-2.5">
            <Copy class="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div>
              <p class="text-xs font-medium text-foreground">普通复制</p>
              <p class="text-xs text-muted-foreground mt-0.5">仅提示词，适合手动配置或其他平台</p>
            </div>
          </div>
          <div class="flex items-start gap-2 rounded-lg border bg-muted/30 px-3 py-2.5">
            <Download class="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div>
              <p class="text-xs font-medium text-foreground">Agent 入职包</p>
              <p class="text-xs text-muted-foreground mt-0.5">发给 Agent 完成注册 + 下载 Skill 工具</p>
            </div>
          </div>
        </div>
      </div>

    </Transition>

    <!-- 删除确认弹窗 -->
    <Transition name="view">
      <div v-if="showDeleteConfirm"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <Card class="w-full max-w-sm shadow-xl">
          <CardContent class="p-6 space-y-4">
            <div>
              <h3 class="text-lg font-semibold">确认删除</h3>
              <p class="text-sm text-muted-foreground mt-2">
                确定要删除提示词「{{ deleteTarget }}」吗？此操作不可撤销。
              </p>
            </div>
            <div class="flex justify-end gap-2">
              <Button variant="outline" @click="showDeleteConfirm = false">取消</Button>
              <Button variant="destructive" @click="confirmDelete">确定删除</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </Transition>

    <!-- 规则编辑器弹窗（新建 / 编辑共用） -->
    <Teleport to="body">
      <Transition name="view">
        <div v-if="showRuleEditor"
          class="fixed inset-0 z-[100] flex items-center justify-center">
          <!-- 遮罩 -->
          <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeRuleEditor()" />
          <!-- 弹窗主体 -->
          <div class="relative z-10 w-full max-w-4xl mx-6 bg-background rounded-xl shadow-2xl border flex flex-col overflow-hidden"
            style="height: 75vh; max-height: 75vh;">
            <!-- 头部 -->
            <div class="flex items-center justify-between px-5 py-3 border-b flex-shrink-0">
              <div>
                <h3 class="text-base font-semibold">
                  {{ ruleEditorId ? '编辑全局规则' : '新建全局规则' }}
                </h3>
                <p class="text-xs text-muted-foreground mt-0.5">支持 Markdown 格式</p>
              </div>
              <!-- 视图模式切换 -->
              <div class="flex items-center border rounded-lg overflow-hidden">
                <button class="px-3 py-1.5 text-xs flex items-center gap-1.5 transition-colors"
                  :class="ruleEditorPreviewMode === 'edit' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
                  @click="ruleEditorPreviewMode = 'edit'">
                  <Code class="h-3.5 w-3.5" />
                  编辑
                </button>
                <button class="px-3 py-1.5 text-xs flex items-center gap-1.5 transition-colors"
                  :class="ruleEditorPreviewMode === 'split' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
                  @click="ruleEditorPreviewMode = 'split'">
                  分栏
                </button>
                <button class="px-3 py-1.5 text-xs flex items-center gap-1.5 transition-colors"
                  :class="ruleEditorPreviewMode === 'preview' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
                  @click="ruleEditorPreviewMode = 'preview'">
                  <Eye class="h-3.5 w-3.5" />
                  预览
                </button>
              </div>
            </div>

            <!-- 编辑区域 -->
            <div class="flex-1 flex min-h-0">
              <!-- 编辑器 -->
              <div v-if="ruleEditorPreviewMode !== 'preview'"
                :class="ruleEditorPreviewMode === 'split' ? 'w-1/2 border-r' : 'w-full'"
                class="h-full">
                <textarea v-model="ruleEditorContent"
                  class="w-full h-full px-4 py-3 text-sm font-mono bg-background border-0 resize-none focus:outline-none focus:ring-0"
                  placeholder="输入规则内容，支持 Markdown 格式..." />
              </div>
              <!-- 预览 -->
              <div v-if="ruleEditorPreviewMode !== 'edit'"
                :class="ruleEditorPreviewMode === 'split' ? 'w-1/2' : 'w-full'"
                class="h-full overflow-y-auto">
                <div v-if="renderedRulePreview"
                  class="p-4 prose prose-sm dark:prose-invert max-w-none"
                  v-html="renderedRulePreview" />
                <div v-else class="flex items-center justify-center h-full text-sm text-muted-foreground">
                  输入内容后在此显示预览
                </div>
              </div>
            </div>

            <!-- 底部操作栏 -->
            <div class="flex items-center justify-end gap-2 px-5 py-3 border-t bg-muted/30 flex-shrink-0">
              <Button variant="outline" @click="closeRuleEditor()">取消</Button>
              <Button :disabled="ruleSaving || !ruleEditorContent.trim()" @click="saveRuleEditor">
                <Loader2 v-if="ruleSaving" class="mr-1.5 h-4 w-4 animate-spin" />
                {{ ruleSaving ? '保存中...' : '保存' }}
              </Button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 规则删除确认弹窗 -->
    <Transition name="toast">
      <div v-if="showRuleDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showRuleDeleteConfirm = false" />
        <Card class="relative z-10 w-full max-w-sm shadow-2xl">
          <CardContent class="p-6 text-center space-y-4">
            <div
              class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400">
              <Trash2 class="h-5 w-5" />
            </div>
            <div>
              <p class="font-semibold text-foreground">确定删除此规则？</p>
              <p class="text-sm text-muted-foreground mt-1">删除后不可恢复</p>
            </div>
            <div class="flex gap-3 justify-center">
              <Button variant="outline" @click="showRuleDeleteConfirm = false">取消</Button>
              <Button variant="destructive" @click="doRuleDelete">确认删除</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.view-enter-active {
  transition: all 0.25s ease-out;
}

.view-leave-active {
  transition: all 0.15s ease-in;
}

.view-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.view-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.toast-enter-active {
  transition: all 0.3s ease-out;
}

.toast-leave-active {
  transition: all 0.2s ease-in;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(-12px) scale(0.95);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.95);
}

/* 翻转卡片 */
.flip-card:hover .flip-card-inner {
  transform: rotateY(180deg);
}

.flip-card-inner {
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.flip-card-front,
.flip-card-back {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.3s ease;
}

.flip-card:hover .flip-card-front,
.flip-card:hover .flip-card-back {
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08), 0 4px 10px rgba(0, 0, 0, 0.04);
}

.line-clamp-4 {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
