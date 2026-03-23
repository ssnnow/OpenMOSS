<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import {
    adminAgentApi,
    adminApi,
    provisionAgent,
    type AdminAgentItem,
    type AdminAgentDetail,
    type AdminPageResponse,
} from '@/api/client'
import { toast } from 'vue-sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { TooltipProvider } from '@/components/ui/tooltip'
import TextOverflowTooltip from '@/components/common/TextOverflowTooltip.vue'
import {
    Search,
    RefreshCw,
    Loader2,
    AlertCircle,
    AlertTriangle,
    Users,
    ArrowLeft,
    ArrowRight,
    KeyRound,
    Copy,
    Check,
    Pencil,
    Trash2,
    ChevronLeft,
    ToggleLeft,
    ToggleRight,
    Plus,
} from 'lucide-vue-next'

// ─── 状态 ───

const PAGE_SIZE = 20
const mode = ref<'list' | 'detail'>('list')

const keyword = ref('')
const roleFilter = ref('all')
const page = ref(1)

const loading = ref(false)
const loadingDetail = ref(false)
const listError = ref('')
const detailError = ref('')

const selectedAgentId = ref<string | null>(null)
const selectedAgent = ref<AdminAgentDetail | null>(null)

const pageData =
    ref<AdminPageResponse<AdminAgentItem>>(createEmptyPage<AdminAgentItem>())

let listRequestId = 0
let detailRequestId = 0
const detailKey = ref(0)

// ─── 选项 ───

const roleOptions = [
    { value: 'all', label: '全部角色' },
    { value: 'planner', label: '规划者' },
    { value: 'executor', label: '执行者' },
    { value: 'reviewer', label: '审查者' },
    { value: 'patrol', label: '巡查者' },
]

// ─── 工具函数 ───

function createEmptyPage<T>(): AdminPageResponse<T> {
    return { items: [], total: 0, page: 1, page_size: PAGE_SIZE, total_pages: 1, has_more: false }
}

function formatRole(role: string) {
    return ({ planner: '规划者', executor: '执行者', reviewer: '审查者', patrol: '巡查者' }[role] ?? role)
}

function getRoleBadgeClass(role: string) {
    return ({
        planner: 'border-violet-200 bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300 dark:border-violet-800',
        executor: 'border-sky-200 bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-800',
        reviewer: 'border-amber-200 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800',
        patrol: 'border-teal-200 bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 dark:border-teal-800',
    }[role] ?? 'border-border bg-muted text-muted-foreground')
}

function getRoleBarClass(role: string) {
    return ({
        planner: 'bg-violet-400 dark:bg-violet-500',
        executor: 'bg-sky-400 dark:bg-sky-500',
        reviewer: 'bg-amber-400 dark:bg-amber-500',
        patrol: 'bg-teal-400 dark:bg-teal-500',
    }[role] ?? 'bg-muted-foreground/30')
}

function formatStatus(status: string) {
    return ({ active: '工作中', disabled: '已禁用' }[status] ?? status)
}

function getStatusDotClass(status: string) {
    return ({
        active: 'bg-emerald-500',
        disabled: 'bg-gray-400',
    }[status] ?? 'bg-slate-400')
}

function formatDate(value: string | null) {
    if (!value) return '未记录'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '未记录'
    return new Intl.DateTimeFormat('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
    }).format(date)
}

function formatRelativeTime(value: string | null) {
    if (!value) return '从未'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '从未'
    const now = Date.now()
    const diff = now - date.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return '刚刚'
    if (mins < 60) return `${mins} 分钟前`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours} 小时前`
    const days = Math.floor(hours / 24)
    return `${days} 天前`
}

// ─── 数据加载 ───

const reloadDebounced = useDebounceFn(() => {
    page.value = 1
    void loadAgents()
}, 280)

watch([keyword, roleFilter], () => {
    loading.value = true
    reloadDebounced()
})

onMounted(() => {
    void loadAgents()
})

async function loadAgents() {
    const requestId = ++listRequestId
    loading.value = true
    listError.value = ''

    try {
        const response = await adminAgentApi.list({
            page: page.value,
            page_size: PAGE_SIZE,
            keyword: keyword.value.trim() || undefined,
            role: roleFilter.value === 'all' ? undefined : roleFilter.value,
            sort_by: 'created_at',
            sort_order: 'desc',
        })

        if (requestId !== listRequestId) return
        pageData.value = response.data
    } catch (error) {
        if (requestId !== listRequestId) return
        console.error('Failed to load agents', error)
        listError.value = 'Agent 列表加载失败，请稍后再试。'
        pageData.value = createEmptyPage<AdminAgentItem>()
    } finally {
        if (requestId === listRequestId) loading.value = false
    }
}

async function loadAgentDetail(agentId: string) {
    const requestId = ++detailRequestId
    loadingDetail.value = true
    detailError.value = ''

    try {
        const response = await adminAgentApi.get(agentId)
        if (requestId !== detailRequestId || selectedAgentId.value !== agentId) return
        selectedAgent.value = response.data
        detailKey.value++
    } catch (error) {
        if (requestId !== detailRequestId) return
        console.error('Failed to load agent detail', error)
        detailError.value = 'Agent 详情加载失败，请重试。'
        selectedAgent.value = null
    } finally {
        if (requestId === detailRequestId) loadingDetail.value = false
    }
}

function openDetail(agentId: string) {
    selectedAgentId.value = agentId
    void loadAgentDetail(agentId)
    mode.value = 'detail'
}

function goBackToList() {
    mode.value = 'list'
}

function goToPage(p: number) {
    if (p < 1 || p > pageData.value.total_pages || p === page.value) return
    page.value = p
    void loadAgents()
}

function refreshList() {
    void loadAgents()
}

// ─── 计算属性 ───

const workloadTotal = computed(() => {
    if (!selectedAgent.value) return 0
    return selectedAgent.value.open_sub_task_count
})

// ─── 操作 ───

const showResetKeyConfirm = ref(false)
const showNewKeyDialog = ref(false)
const newApiKey = ref('')
const resettingKey = ref(false)
const keyCopied = ref(false)
const togglingStatus = ref(false)

// 改名/改角色/改描述
const showEditDialog = ref(false)
const editName = ref('')
const editRole = ref('')
const editDescription = ref('')
const editError = ref('')
const savingEdit = ref(false)

const roleChanged = computed(() =>
    selectedAgent.value ? editRole.value !== selectedAgent.value.role : false
)

function openEditDialog() {
    if (!selectedAgent.value) return
    editName.value = selectedAgent.value.name
    editRole.value = selectedAgent.value.role
    editDescription.value = selectedAgent.value.description ?? ''
    editError.value = ''
    showEditDialog.value = true
}

// 也支持从卡片直接编辑
function openEditDialogForAgent(agent: AdminAgentItem) {
    selectedAgentId.value = agent.id
    selectedAgent.value = agent as unknown as AdminAgentDetail
    editName.value = agent.name
    editRole.value = agent.role
    editDescription.value = agent.description ?? ''
    editError.value = ''
    showEditDialog.value = true
}

async function handleSaveEdit() {
    if (!selectedAgentId.value) return
    const name = editName.value.trim()
    if (!name) { editError.value = '名称不能为空'; return }
    savingEdit.value = true
    editError.value = ''
    try {
        await adminAgentApi.updateProfile(selectedAgentId.value, {
            name,
            role: roleChanged.value ? editRole.value : undefined,
            description: editDescription.value,
        })
        showEditDialog.value = false
        toast(`${editName.value} 信息已更新`)
        if (mode.value === 'detail') {
            void loadAgentDetail(selectedAgentId.value)
        }
        void loadAgents()
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        editError.value = msg ?? '保存失败，请重试'
        toast.error(editError.value)
    } finally {
        savingEdit.value = false
    }
}

// 启用/禁用确认
const showToggleConfirm = ref(false)
const toggleTarget = ref<{ id: string; name: string; status: string } | null>(null)

function confirmToggleStatus(agent: { id: string; name?: string; status: string }) {
    toggleTarget.value = { id: agent.id, name: agent.name ?? selectedAgent.value?.name ?? '', status: agent.status }
    showToggleConfirm.value = true
}

async function handleToggleStatus() {
    if (!toggleTarget.value) return
    showToggleConfirm.value = false
    togglingStatus.value = true
    const newStatus = toggleTarget.value.status === 'active' ? 'disabled' : 'active'
    try {
        await adminAgentApi.updateStatus(toggleTarget.value.id, newStatus)
        if (mode.value === 'detail' && selectedAgentId.value === toggleTarget.value.id) {
            void loadAgentDetail(toggleTarget.value.id)
        }
        void loadAgents()
        toast(newStatus === 'active' ? `${toggleTarget.value.name} 已被启用` : `${toggleTarget.value.name} 已被禁用`)
    } catch (err) {
        console.error('Failed to toggle status', err)
        toast.error('状态切换失败')
    } finally {
        togglingStatus.value = false
    }
}

async function handleResetKey() {
    if (!selectedAgentId.value) return
    resettingKey.value = true
    try {
        const response = await adminApi.resetKey(selectedAgentId.value)
        newApiKey.value = response.data.new_api_key
        showResetKeyConfirm.value = false
        showNewKeyDialog.value = true
    } catch (error) {
        console.error('Failed to reset key', error)
    } finally {
        resettingKey.value = false
    }
}

async function copyNewKey() {
    try {
        await navigator.clipboard.writeText(newApiKey.value)
        keyCopied.value = true
        setTimeout(() => { keyCopied.value = false }, 2000)
    } catch {
        // fallback: select text
    }
}

// ─── 新建 Agent ───

const showCreateDialog = ref(false)
const createName = ref('')
const createRole = ref('executor')
const createWakeInterval = ref('1h')
const createError = ref('')
const creatingAgent = ref(false)

const wakeIntervalOptions = [
    { value: '15m', label: '15 分钟' },
    { value: '30m', label: '30 分钟' },
    { value: '1h', label: '1 小时' },
    { value: '4h', label: '4 小时' },
    { value: '24h', label: '24 小时' },
]

function openCreateDialog() {
    createName.value = ''
    createRole.value = 'executor'
    createWakeInterval.value = '1h'
    createError.value = ''
    showCreateDialog.value = true
}

async function handleCreateAgent() {
    const name = createName.value.trim()
    const role = createRole.value.trim()
    if (!name) { createError.value = '名称不能为空'; return }
    if (!role) { createError.value = '角色/目标不能为空'; return }

    creatingAgent.value = true
    createError.value = ''
    try {
        await provisionAgent({
            name,
            role,
            wake_interval: createWakeInterval.value,
        })
        showCreateDialog.value = false
        toast('Agent 创建成功')
        void loadAgents()
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        createError.value = msg ?? '创建失败，请重试'
    } finally {
        creatingAgent.value = false
    }
}

// 删除 Agent
const showDeleteDialog = ref(false)
const deleteConfirmInput = ref('')
const deletingAgent = ref(false)
const deleteError = ref('')
const relatedCounts = ref<Record<string, number> | null>(null)
const loadingCounts = ref(false)

const deleteConfirmValid = computed(() =>
    selectedAgent.value
        ? deleteConfirmInput.value.trim() === `确认删除${selectedAgent.value.name}`
        : false
)

async function openDeleteDialog() {
    if (!selectedAgentId.value || !selectedAgent.value) return
    deleteConfirmInput.value = ''
    deleteError.value = ''
    relatedCounts.value = null
    showDeleteDialog.value = true
    loadingCounts.value = true
    try {
        const res = await adminAgentApi.relatedCounts(selectedAgentId.value)
        relatedCounts.value = res.data
    } catch {
        relatedCounts.value = null
    } finally {
        loadingCounts.value = false
    }
}

// 从卡片上直接删除
function openDeleteDialogForAgent(agent: AdminAgentItem) {
    selectedAgentId.value = agent.id
    selectedAgent.value = agent as unknown as AdminAgentDetail
    void openDeleteDialog()
}

async function handleDeleteAgent() {
    if (!selectedAgentId.value || !selectedAgent.value || !deleteConfirmValid.value) return
    deletingAgent.value = true
    deleteError.value = ''
    try {
        await adminAgentApi.deleteAgent(selectedAgentId.value, selectedAgent.value.name)
        showDeleteDialog.value = false
        toast(`${selectedAgent.value.name} 已被删除`)
        selectedAgentId.value = null
        selectedAgent.value = null
        if (mode.value === 'detail') mode.value = 'list'
        void loadAgents()
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        deleteError.value = msg ?? '删除失败，请重试'
    } finally {
        deletingAgent.value = false
    }
}
</script>

<template>
    <div class="p-6 max-w-6xl mx-auto">

        <!-- 视图过渡 -->
        <Transition name="view" mode="out-in" appear>

            <!-- ════════════════ 列表视图 ════════════════ -->
            <div v-if="mode === 'list'" key="list" class="space-y-5">

                <!-- 顶栏 -->
                <div class="flex items-center justify-between gap-4">
                    <div class="flex items-center gap-3">
                        <h1 class="text-xl font-bold">Agent 管理</h1>
                        <Badge variant="secondary" class="h-6 px-2 text-xs tabular-nums">
                            {{ pageData.total }} 个
                        </Badge>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="relative">
                            <Search
                                class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input v-model="keyword" class="h-9 w-56 bg-muted/30 pl-10 text-sm"
                                placeholder="搜索名称或描述…" />
                        </div>
                        <Button variant="ghost" size="icon" class="h-9 w-9" :disabled="loading" @click="refreshList">
                            <RefreshCw class="h-4 w-4" :class="loading ? 'animate-spin' : ''" />
                        </Button>
                        <Button size="sm" class="h-9 gap-1.5" @click="openCreateDialog">
                            <Plus class="h-4 w-4" />
                            新建 Agent
                        </Button>
                    </div>
                </div>

                <!-- 角色筛选 -->
                <div class="flex gap-1.5">
                    <Button v-for="option in roleOptions" :key="option.value" size="sm"
                        :variant="roleFilter === option.value ? 'default' : 'ghost'"
                        class="h-7 rounded-full px-3 text-xs" @click="roleFilter = option.value">
                        {{ option.label }}
                    </Button>
                </div>

                <!-- 加载中 -->
                <div v-if="loading" class="flex items-center justify-center py-20">
                    <Loader2 class="h-7 w-7 animate-spin text-muted-foreground" />
                </div>

                <!-- 错误 -->
                <div v-else-if="listError" class="flex flex-col items-center py-20 text-muted-foreground">
                    <AlertCircle class="h-6 w-6 mb-2" />
                    <p class="text-sm">{{ listError }}</p>
                    <Button class="mt-3" size="sm" @click="refreshList">重新加载</Button>
                </div>

                <!-- 空状态 -->
                <div v-else-if="!pageData.items.length"
                    class="flex flex-col items-center py-20 text-muted-foreground/50">
                    <Users class="h-8 w-8 mb-3" />
                    <p class="text-sm font-medium">没有找到匹配的 Agent</p>
                </div>

                <!-- 卡片网格 -->
                <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    <div v-for="(agent, idx) in pageData.items" :key="agent.id"
                        class="group relative rounded-xl border border-border/50 bg-card overflow-hidden transition-all duration-200 hover:border-border hover:shadow-[var(--shadow-md)] hover:scale-[1.02] cursor-pointer animate-slide-up"
                        :style="{ animationDelay: `${idx * 40}ms` }" @click="openDetail(agent.id)">

                        <!-- 角色色彩条 -->
                        <div class="h-[3px] w-full" :class="getRoleBarClass(agent.role)" />

                        <div class="p-4">

                        <!-- 顶部：状态点 + 名称 + 角色 -->
                        <div class="flex items-start justify-between gap-2 mb-2">
                            <div class="flex items-center gap-2 min-w-0">
                                <span class="inline-block w-2 h-2 rounded-full shrink-0 ring-2 ring-background"
                                    :class="getStatusDotClass(agent.status)" />
                                <TextOverflowTooltip :text="agent.name" as="h3"
                                    class="text-sm font-semibold leading-5 truncate" />
                            </div>
                            <Badge variant="outline" :class="getRoleBadgeClass(agent.role)"
                                class="shrink-0 text-[10px] px-1.5 py-0">
                                {{ formatRole(agent.role) }}
                            </Badge>
                        </div>

                        <!-- 描述 -->
                        <p class="text-xs text-muted-foreground leading-4 line-clamp-2 min-h-[2rem] mb-3 pl-4">
                            {{ agent.description || '暂无描述' }}
                        </p>

                        <!-- 统计行 -->
                        <div class="flex items-center gap-3 text-[11px] text-muted-foreground pl-4 mb-3">
                            <span class="font-medium tabular-nums"
                                :class="agent.total_score >= 0 ? 'text-emerald-600' : 'text-rose-500'">
                                {{ agent.total_score >= 0 ? '+' : '' }}{{ agent.total_score }} 分
                            </span>
                            <span v-if="agent.open_sub_task_count" class="tabular-nums">
                                {{ agent.open_sub_task_count }} 个待办
                            </span>
                            <span v-else class="opacity-50">无待办</span>
                            <span class="ml-auto tabular-nums opacity-60">
                                {{ formatRelativeTime(agent.last_request_at) }}
                            </span>
                        </div>

                        <Separator class="mb-3 opacity-50" />

                        <!-- 操作按钮行（hover 时显示）-->
                        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200" @click.stop>
                            <TooltipProvider>
                                <Button variant="ghost" size="sm" class="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground"
                                    @click="openEditDialogForAgent(agent)">
                                    <Pencil class="h-3 w-3" />
                                    编辑
                                </Button>
                                <Button variant="ghost" size="sm"
                                    class="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground"
                                    :disabled="togglingStatus" @click="confirmToggleStatus(agent)">
                                    <ToggleRight v-if="agent.status === 'active'" class="h-3.5 w-3.5 text-emerald-500" />
                                    <ToggleLeft v-else class="h-3.5 w-3.5 text-gray-400" />
                                    {{ agent.status === 'active' ? '禁用' : '启用' }}
                                </Button>
                                <Button variant="ghost" size="sm"
                                    class="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-rose-600 ml-auto"
                                    @click="openDeleteDialogForAgent(agent)">
                                    <Trash2 class="h-3 w-3" />
                                    删除
                                </Button>
                            </TooltipProvider>
                        </div>
                        </div>
                    </div>
                </div>

                <!-- 分页 -->
                <div v-if="pageData.total_pages > 1"
                    class="flex items-center justify-center gap-3 pt-2 text-sm text-muted-foreground">
                    <Button variant="outline" size="sm" class="h-8 gap-1" :disabled="pageData.page <= 1 || loading"
                        @click="goToPage(pageData.page - 1)">
                        <ArrowLeft class="h-3.5 w-3.5" />
                        上一页
                    </Button>
                    <span class="tabular-nums text-xs">{{ pageData.page }} / {{ pageData.total_pages }}</span>
                    <Button variant="outline" size="sm" class="h-8 gap-1"
                        :disabled="pageData.page >= pageData.total_pages || loading"
                        @click="goToPage(pageData.page + 1)">
                        下一页
                        <ArrowRight class="h-3.5 w-3.5" />
                    </Button>
                </div>
            </div>

            <!-- ════════════════ 详情视图 ════════════════ -->
            <div v-else-if="mode === 'detail'" key="detail" class="space-y-6 max-w-3xl mx-auto">

                <!-- 返回 -->
                <button
                    class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                    @click="goBackToList">
                    <ChevronLeft class="h-4 w-4" />
                    返回列表
                </button>

                <!-- 加载中 -->
                <div v-if="loadingDetail" class="flex items-center justify-center py-20">
                    <Loader2 class="h-7 w-7 animate-spin text-muted-foreground" />
                </div>

                <!-- 错误 -->
                <div v-else-if="detailError" class="flex flex-col items-center py-20 text-muted-foreground/50">
                    <AlertCircle class="h-6 w-6 mb-2" />
                    <p class="text-sm">{{ detailError }}</p>
                    <Button v-if="selectedAgentId" class="mt-3" size="sm"
                        @click="loadAgentDetail(selectedAgentId)">重试</Button>
                </div>

                <!-- Agent 详情 -->
                <div v-else-if="selectedAgent" :key="detailKey" class="space-y-6 animate-slide-up">
                    <!-- 头部卡片 -->
                    <div class="rounded-xl border bg-card p-6">
                        <div class="flex items-start justify-between gap-4">
                            <div class="min-w-0 space-y-1.5">
                                <h2 class="text-xl font-bold leading-7">{{ selectedAgent.name }}</h2>
                                <p class="text-sm text-muted-foreground leading-5">
                                    {{ selectedAgent.description || '暂无描述信息。' }}
                                </p>
                            </div>
                            <div class="flex gap-1.5 shrink-0">
                                <Badge variant="outline" :class="getRoleBadgeClass(selectedAgent.role)">
                                    {{ formatRole(selectedAgent.role) }}
                                </Badge>
                                <Badge variant="outline" class="gap-1">
                                    <span class="inline-block w-1.5 h-1.5 rounded-full"
                                        :class="getStatusDotClass(selectedAgent.status)" />
                                    {{ formatStatus(selectedAgent.status) }}
                                </Badge>
                            </div>
                        </div>
                    </div>

                    <!-- 数据面板行 -->
                    <div class="grid gap-4 sm:grid-cols-3">
                        <!-- 积分 -->
                        <div class="rounded-xl border bg-card p-4 text-center">
                            <div class="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">积分总分
                            </div>
                            <div class="text-2xl font-bold tabular-nums"
                                :class="selectedAgent.total_score >= 0 ? 'text-emerald-600' : 'text-rose-500'">
                                {{ selectedAgent.total_score >= 0 ? '+' : '' }}{{ selectedAgent.total_score }}
                            </div>
                            <div class="text-xs text-muted-foreground mt-1 tabular-nums">
                                排名 <span class="font-medium text-foreground">{{ selectedAgent.rank }}</span>
                                / {{ selectedAgent.total_agents }}
                            </div>
                        </div>
                        <!-- 奖惩 -->
                        <div class="rounded-xl border bg-card p-4 text-center">
                            <div class="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">奖惩记录
                            </div>
                            <div class="flex items-center justify-center gap-4 mt-1">
                                <div>
                                    <div class="text-xl font-bold tabular-nums text-emerald-600">
                                        {{ selectedAgent.reward_count }}
                                    </div>
                                    <div class="text-[10px] text-muted-foreground">奖励</div>
                                </div>
                                <Separator orientation="vertical" class="h-8" />
                                <div>
                                    <div class="text-xl font-bold tabular-nums text-rose-500">
                                        {{ selectedAgent.penalty_count }}
                                    </div>
                                    <div class="text-[10px] text-muted-foreground">惩罚</div>
                                </div>
                            </div>
                        </div>
                        <!-- 工作负载 -->
                        <div class="rounded-xl border bg-card p-4 text-center">
                            <div class="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">
                                工作负载 · {{ workloadTotal }}
                            </div>
                            <div class="flex items-center justify-center gap-3 mt-1">
                                <div>
                                    <div class="text-lg font-bold tabular-nums text-indigo-600">
                                        {{ selectedAgent.assigned_count }}
                                    </div>
                                    <div class="text-[10px] text-muted-foreground">待办</div>
                                </div>
                                <div>
                                    <div class="text-lg font-bold tabular-nums text-sky-600">
                                        {{ selectedAgent.in_progress_count }}
                                    </div>
                                    <div class="text-[10px] text-muted-foreground">执行中</div>
                                </div>
                                <div>
                                    <div class="text-lg font-bold tabular-nums text-emerald-600">
                                        {{ selectedAgent.done_count }}
                                    </div>
                                    <div class="text-[10px] text-muted-foreground">已完成</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 时间信息 -->
                    <div class="rounded-xl border bg-card p-5">
                        <div class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider mb-3">
                            时间信息
                        </div>
                        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <div>
                                <div class="text-[11px] text-muted-foreground/60">最近请求</div>
                                <div class="text-sm font-medium mt-0.5">
                                    {{ formatRelativeTime(selectedAgent.last_request_at) }}
                                </div>
                                <div class="text-[10px] text-muted-foreground">
                                    {{ formatDate(selectedAgent.last_request_at) }}
                                </div>
                            </div>
                            <div>
                                <div class="text-[11px] text-muted-foreground/60">最近活动</div>
                                <div class="text-sm font-medium mt-0.5">
                                    {{ formatRelativeTime(selectedAgent.last_activity_at) }}
                                </div>
                                <div class="text-[10px] text-muted-foreground">
                                    {{ formatDate(selectedAgent.last_activity_at) }}
                                </div>
                            </div>
                            <div>
                                <div class="text-[11px] text-muted-foreground/60">创建时间</div>
                                <div class="text-sm font-medium mt-0.5">
                                    {{ formatDate(selectedAgent.created_at) }}
                                </div>
                            </div>
                            <div>
                                <div class="text-[11px] text-muted-foreground/60">Agent ID</div>
                                <div class="text-xs font-mono text-muted-foreground mt-1 break-all select-all">
                                    {{ selectedAgent.id }}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 操作区 -->
                    <div class="rounded-xl border bg-card p-5">
                        <div class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider mb-3">
                            操作
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <Button variant="outline" size="sm" class="gap-1.5" @click="openEditDialog">
                                <Pencil class="h-3.5 w-3.5" />
                                编辑信息
                            </Button>
                            <Button variant="outline" size="sm" class="gap-1.5" :disabled="togglingStatus"
                                @click="confirmToggleStatus(selectedAgent)">
                                <ToggleRight v-if="selectedAgent.status === 'active'"
                                    class="h-4 w-4 text-emerald-500" />
                                <ToggleLeft v-else class="h-4 w-4 text-gray-400" />
                                {{ selectedAgent.status === 'active' ? '禁用' : '启用' }}
                            </Button>
                            <Button variant="outline" size="sm"
                                class="gap-1.5 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                                @click="showResetKeyConfirm = true">
                                <KeyRound class="h-3.5 w-3.5" />
                                重置 API Key
                            </Button>
                            <Button variant="outline" size="sm"
                                class="gap-1.5 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                                @click="openDeleteDialog">
                                <Trash2 class="h-3.5 w-3.5" />
                                删除 Agent
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </Transition>
    </div>

    <!-- ════════ 弹窗区域 ════════ -->

    <!-- 编辑 Agent 信息弹窗 -->
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="showEditDialog" class="fixed inset-0 z-50 flex items-center justify-center">
                <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditDialog = false" />
                <div
                    class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                    <h2 class="text-lg font-semibold mb-4">编辑 Agent 信息</h2>
                    <div class="space-y-3">
                        <div>
                            <label class="text-xs text-muted-foreground mb-1 block">名称</label>
                            <Input v-model="editName" placeholder="Agent 名称" maxlength="100" />
                        </div>
                        <div>
                            <label class="text-xs text-muted-foreground mb-1.5 block">角色</label>
                            <div class="flex gap-1.5">
                                <Button v-for="option in roleOptions.filter(o => o.value !== 'all')" :key="option.value"
                                    size="sm" :variant="editRole === option.value ? 'default' : 'outline'"
                                    class="flex-1 h-8 text-xs px-0" @click="editRole = option.value">
                                    {{ option.label }}
                                </Button>
                            </div>
                            <div v-if="roleChanged"
                                class="mt-2 flex items-start gap-1.5 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-700 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300">
                                <AlertTriangle class="h-3.5 w-3.5 shrink-0 mt-0.5" />
                                <span>改角色后请在「提示词管理」中修改对应提示词，并手动同步到该 Agent，否则角色变更不会实际生效。</span>
                            </div>
                        </div>
                        <div>
                            <label class="text-xs text-muted-foreground mb-1 block">描述</label>
                            <textarea v-model="editDescription" placeholder="职责简要（可选）"
                                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                                rows="3" />
                        </div>
                        <p v-if="editError" class="text-xs text-rose-500">{{ editError }}</p>
                    </div>
                    <div class="mt-5 flex gap-3">
                        <Button variant="outline" class="flex-1" :disabled="savingEdit"
                            @click="showEditDialog = false">取消</Button>
                        <Button class="flex-1" :disabled="savingEdit" @click="handleSaveEdit">
                            <Loader2 v-if="savingEdit" class="h-4 w-4 animate-spin mr-1" />
                            保存
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>

    <!-- 重置 API Key 确认弹窗 -->
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="showResetKeyConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
                <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showResetKeyConfirm = false" />
                <div
                    class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                    <div class="space-y-2 text-center">
                        <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-100">
                            <KeyRound class="h-5 w-5 text-rose-600" />
                        </div>
                        <h2 class="text-lg font-semibold">重置 API Key</h2>
                        <p class="text-sm text-muted-foreground">
                            确认重置 <span class="font-medium text-foreground">{{ selectedAgent?.name }}</span> 的 API
                            Key？旧 Key 将立即失效。
                        </p>
                    </div>
                    <div class="mt-6 flex gap-3">
                        <Button variant="outline" class="flex-1" :disabled="resettingKey"
                            @click="showResetKeyConfirm = false">取消</Button>
                        <Button variant="destructive" class="flex-1" :disabled="resettingKey" @click="handleResetKey">
                            <Loader2 v-if="resettingKey" class="h-4 w-4 animate-spin mr-1" />
                            确认重置
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>

    <!-- 新 API Key 展示弹窗 -->
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="showNewKeyDialog" class="fixed inset-0 z-50 flex items-center justify-center">
                <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" />
                <div
                    class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                    <div class="space-y-2 text-center">
                        <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100">
                            <KeyRound class="h-5 w-5 text-emerald-600" />
                        </div>
                        <h2 class="text-lg font-semibold">新 API Key</h2>
                        <p class="text-sm text-muted-foreground">
                            请立即复制并保存，关闭后将无法再次查看！
                        </p>
                    </div>
                    <div class="mt-4 flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2">
                        <code class="flex-1 text-sm font-mono break-all select-all">{{ newApiKey }}</code>
                        <Button variant="ghost" size="icon" class="h-8 w-8 shrink-0" @click="copyNewKey">
                            <Check v-if="keyCopied" class="h-4 w-4 text-emerald-500" />
                            <Copy v-else class="h-4 w-4" />
                        </Button>
                    </div>
                    <div class="mt-5 flex justify-center">
                        <Button class="px-8" @click="showNewKeyDialog = false; newApiKey = ''">
                            我已保存，关闭
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>

    <!-- 删除 Agent 确认弹窗 -->
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="showDeleteDialog" class="fixed inset-0 z-50 flex items-center justify-center">
                <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showDeleteDialog = false" />
                <div
                    class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                    <div class="space-y-2 text-center">
                        <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-100">
                            <Trash2 class="h-5 w-5 text-rose-600" />
                        </div>
                        <h2 class="text-lg font-semibold">删除 Agent</h2>
                        <p class="text-sm text-muted-foreground">
                            即将删除 <span class="font-medium text-foreground">{{ selectedAgent?.name }}</span>，此操作不可撤销。
                        </p>
                    </div>

                    <!-- 关联数据风险提示 -->
                    <div class="mt-4 rounded-lg border border-rose-200 bg-rose-50/50 p-3 space-y-1.5">
                        <div class="flex items-center gap-1.5 text-xs font-medium text-rose-700">
                            <AlertTriangle class="h-3.5 w-3.5" />
                            <span>以下关联数据将被清空：</span>
                        </div>
                        <div v-if="loadingCounts" class="flex justify-center py-2">
                            <Loader2 class="h-4 w-4 animate-spin text-muted-foreground" />
                        </div>
                        <div v-else-if="relatedCounts" class="grid grid-cols-2 gap-1 text-xs text-rose-600">
                            <span>• 子任务解绑：{{ relatedCounts.sub_task_count }} 个</span>
                            <span>• 审查记录：{{ relatedCounts.review_count }} 条</span>
                            <span>• 积分记录：{{ relatedCounts.reward_count }} 条</span>
                            <span>• 活动日志：{{ relatedCounts.activity_count }} 条</span>
                            <span>• 巡查记录：{{ relatedCounts.patrol_count }} 条</span>
                            <span>• 请求日志：{{ relatedCounts.request_count }} 条</span>
                        </div>
                    </div>

                    <!-- 确认输入 -->
                    <div class="mt-4">
                        <label class="text-xs text-muted-foreground mb-1.5 block">
                            请输入 <span class="font-semibold text-foreground">确认删除{{ selectedAgent?.name }}</span> 以确认
                        </label>
                        <Input v-model="deleteConfirmInput" placeholder="确认删除..."
                            class="border-rose-200 focus:ring-rose-500" />
                        <p v-if="deleteError" class="text-xs text-rose-500 mt-1">{{ deleteError }}</p>
                    </div>

                    <div class="mt-5 flex gap-3">
                        <Button variant="outline" class="flex-1" :disabled="deletingAgent"
                            @click="showDeleteDialog = false">取消</Button>
                        <Button variant="destructive" class="flex-1" :disabled="!deleteConfirmValid || deletingAgent"
                            @click="handleDeleteAgent">
                            <Loader2 v-if="deletingAgent" class="h-4 w-4 animate-spin mr-1" />
                            确认删除
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
    <!-- 启用/禁用确认弹窗 -->
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="showToggleConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
                <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showToggleConfirm = false" />
                <div
                    class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                    <div class="space-y-2 text-center">
                        <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full"
                            :class="toggleTarget?.status === 'active' ? 'bg-amber-100' : 'bg-emerald-100'">
                            <ToggleLeft v-if="toggleTarget?.status === 'active'" class="h-5 w-5 text-amber-600" />
                            <ToggleRight v-else class="h-5 w-5 text-emerald-600" />
                        </div>
                        <h2 class="text-lg font-semibold">
                            {{ toggleTarget?.status === 'active' ? '禁用' : '启用' }} Agent
                        </h2>
                        <p class="text-sm text-muted-foreground">
                            确认{{ toggleTarget?.status === 'active' ? '禁用' : '启用' }}
                            <span class="font-medium text-foreground">{{ toggleTarget?.name }}</span>
                            ？{{ toggleTarget?.status === 'active' ? '禁用后该 Agent 将无法访问任何 API。' : '启用后该 Agent 将恢复 API 访问权限。' }}
                        </p>
                    </div>
                    <div class="mt-6 flex gap-3">
                        <Button variant="outline" class="flex-1"
                            @click="showToggleConfirm = false">取消</Button>
                        <Button class="flex-1"
                            :variant="toggleTarget?.status === 'active' ? 'destructive' : 'default'"
                            :disabled="togglingStatus" @click="handleToggleStatus">
                            <Loader2 v-if="togglingStatus" class="h-4 w-4 animate-spin mr-1" />
                            确认{{ toggleTarget?.status === 'active' ? '禁用' : '启用' }}
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>

    <!-- 新建 Agent 弹窗 -->
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="showCreateDialog" class="fixed inset-0 z-50 flex items-center justify-center">
                <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="!creatingAgent && (showCreateDialog = false)" />
                <div
                    class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                    <h2 class="text-lg font-semibold mb-4">新建 Agent</h2>
                    <div class="space-y-4">
                        <!-- 名称 -->
                        <div>
                            <label class="text-xs font-medium text-muted-foreground mb-1 block">名称 <span class="text-rose-500">*</span></label>
                            <Input v-model="createName" placeholder="Agent 名称" maxlength="100" :disabled="creatingAgent" />
                        </div>
                        <!-- 角色 / 目标 -->
                        <div>
                            <label class="text-xs font-medium text-muted-foreground mb-1 block">角色 / 目标 <span class="text-rose-500">*</span></label>
                            <textarea
                                v-model="createRole"
                                placeholder="e.g. Monitor competitor pricing weekly and write a brief report"
                                :disabled="creatingAgent"
                                rows="3"
                                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
                            />
                        </div>
                        <!-- 唤醒间隔 -->
                        <div>
                            <label class="text-xs font-medium text-muted-foreground mb-1 block">唤醒间隔</label>
                            <select
                                v-model="createWakeInterval"
                                :disabled="creatingAgent"
                                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <option v-for="opt in wakeIntervalOptions" :key="opt.value" :value="opt.value">
                                    {{ opt.label }}
                                </option>
                            </select>
                        </div>
                        <!-- 错误信息 -->
                        <p v-if="createError" class="text-xs text-rose-500 flex items-center gap-1">
                            <AlertCircle class="h-3.5 w-3.5 shrink-0" />
                            {{ createError }}
                        </p>
                    </div>
                    <div class="mt-5 flex gap-3">
                        <Button variant="outline" class="flex-1" :disabled="creatingAgent"
                            @click="showCreateDialog = false">取消</Button>
                        <Button class="flex-1 gap-1.5" :disabled="creatingAgent" @click="handleCreateAgent">
                            <Loader2 v-if="creatingAgent" class="h-4 w-4 animate-spin" />
                            <Plus v-else class="h-4 w-4" />
                            创建 Agent
                        </Button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<style scoped>
@keyframes slide-up-fade-in {
    from {
        opacity: 0;
        transform: translateY(12px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-slide-up {
    animation: slide-up-fade-in 0.35s ease-out both;
}

/* toast 动画 */
.toast-enter-active,
.toast-leave-active {
    transition: opacity 0.3s ease, transform 0.3s ease;
}

.toast-enter-from {
    opacity: 0;
    transform: translate(-50%, -12px);
}

.toast-leave-to {
    opacity: 0;
    transform: translate(-50%, -8px);
}

/* 视图切换过渡 */
.view-enter-active,
.view-leave-active {
    transition: opacity 0.2s ease, transform 0.2s ease;
}

.view-enter-from {
    opacity: 0;
    transform: translateX(12px);
}

.view-leave-to {
    opacity: 0;
    transform: translateX(-12px);
}

/* 弹窗过渡 */
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
