<script setup lang="ts">
import { ref, onMounted, computed, reactive, nextTick } from 'vue'
import {
    adminDashboardApi,
    type DashboardOverview,
    type DashboardHighlights,
    type DashboardTrends,
} from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
    ListTodo,
    Activity,
    ClipboardCheck,
    AlertTriangle,
    Users,
    CheckCircle2,
    RefreshCw,
    Loader2,
    AlertCircle,
    TrendingUp,
    TrendingDown,
    Ban,
    Clock,
    Zap,
    Moon,
    Star,
} from 'lucide-vue-next'

const loading = ref(true)
const error = ref('')
const data = ref<DashboardOverview | null>(null)
const highlights = ref<DashboardHighlights | null>(null)
const trends = ref<DashboardTrends | null>(null)

onMounted(() => {
    void loadData()
})

async function loadData() {
    loading.value = true
    error.value = ''
    try {
        const [overviewRes, highlightsRes, trendsRes] = await Promise.all([
            adminDashboardApi.overview(),
            adminDashboardApi.highlights({ limit: 5 }),
            adminDashboardApi.trends({ days: 7 }),
        ])
        data.value = overviewRes.data
        highlights.value = highlightsRes.data
        trends.value = trendsRes.data
        await nextTick()
        triggerAnimations()
    } catch (e) {
        console.error('Failed to load dashboard', e)
        error.value = '仪表盘数据加载失败'
    } finally {
        loading.value = false
    }
}

function formatRelativeTime(value: string | null) {
    if (!value) return '—'
    const now = Date.now()
    const time = new Date(value).getTime()
    if (Number.isNaN(time)) return '—'
    const diff = Math.floor((now - time) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
    return `${Math.floor(diff / 86400)} 天前`
}

const roleLabels: Record<string, string> = {
    planner: '规划者', executor: '执行者', reviewer: '审查者', patrol: '巡查者',
}

function hasHighlights(h: DashboardHighlights) {
    return h.blocked_sub_tasks.length > 0 || h.pending_review_sub_tasks.length > 0
        || h.busy_agents.length > 0 || h.low_activity_agents.length > 0 || h.recent_reviews.length > 0
}

// ─── 数字滚动动画 ───

const animatedValues = reactive<Record<string, number>>({})

function animateCountUp(key: string, target: number, duration = 800) {
    const start = animatedValues[key] || 0
    const diff = target - start
    if (diff === 0) { animatedValues[key] = target; return }
    const startTime = performance.now()
    function tick(now: number) {
        const elapsed = now - startTime
        const progress = Math.min(elapsed / duration, 1)
        // easeOutCubic
        const eased = 1 - Math.pow(1 - progress, 3)
        animatedValues[key] = Math.round(start + diff * eased)
        if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
}

function triggerAnimations() {
    if (!data.value) return
    const c = data.value.core_cards
    const entries: [string, number][] = [
        ['open_task_count', c.open_task_count],
        ['active_sub_task_count', c.active_sub_task_count],
        ['review_queue_count', c.review_queue_count],
        ['blocked_sub_task_count', c.blocked_sub_task_count],
        ['active_agent_count', c.active_agent_count],
        ['today_completed_sub_task_count', c.today_completed_sub_task_count],
    ]
    entries.forEach(([key, val], i) => {
        setTimeout(() => animateCountUp(key, val, 900), i * 80)
    })
    // trend totals
    if (trends.value) {
        const t = trends.value
        const trendTotals: [string, number][] = [
            ['trend_created', t.sub_task_created_trend.reduce((a, b) => a + b.count, 0)],
            ['trend_completed', t.sub_task_completed_trend.reduce((a, b) => a + b.count, 0)],
            ['trend_review', t.review_trend.reduce((a, b) => a + b.total, 0)],
            ['trend_score', t.score_delta_trend.reduce((a, b) => a + b.net_score_delta, 0)],
            ['trend_request', t.request_trend.reduce((a, b) => a + b.count, 0)],
            ['trend_activity', t.activity_trend.reduce((a, b) => a + b.count, 0)],
        ]
        trendTotals.forEach(([key, val], i) => {
            setTimeout(() => animateCountUp(key, val, 800), 800 + i * 60)
        })
    }
}

// ─── 核心卡片配置 ───
const coreCards = computed(() => {
    if (!data.value) return []
    const c = data.value.core_cards
    return [
        { title: '开放任务', value: c.open_task_count, animKey: 'open_task_count', icon: ListTodo, color: 'text-blue-500', bg: 'bg-blue-500/10' },
        { title: '活跃子任务', value: c.active_sub_task_count, animKey: 'active_sub_task_count', icon: Activity, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
        { title: '等待审查', value: c.review_queue_count, animKey: 'review_queue_count', icon: ClipboardCheck, color: 'text-amber-500', bg: 'bg-amber-500/10' },
        { title: '阻塞子任务', value: c.blocked_sub_task_count, animKey: 'blocked_sub_task_count', icon: AlertTriangle, color: 'text-rose-500', bg: 'bg-rose-500/10' },
        { title: '活跃 Agent', value: c.active_agent_count, animKey: 'active_agent_count', icon: Users, color: 'text-violet-500', bg: 'bg-violet-500/10' },
        { title: '今日完成', value: c.today_completed_sub_task_count, animKey: 'today_completed_sub_task_count', icon: CheckCircle2, color: 'text-teal-500', bg: 'bg-teal-500/10' },
    ]
})

// ─── 分布图表辅助 ───
const statusLabels: Record<string, string> = {
    // task
    planning: '规划中', active: '活跃', in_progress: '进行中', completed: '已完成', archived: '归档', cancelled: '已取消',
    // sub_task
    pending: '待分配', assigned: '已分配', review: '审查中', rework: '返工中', blocked: '阻塞', done: '已完成',
    // agent status (active 与 task.active 共用)
    disabled: '已禁用',
    // agent role
    planner: '规划者', executor: '执行者', reviewer: '审查者', patrol: '巡查者',
    // review result
    approved: '通过', rejected: '驳回',
}

const statusColors: Record<string, string> = {
    planning: 'bg-slate-400', active: 'bg-blue-500', in_progress: 'bg-amber-500',
    completed: 'bg-emerald-500', archived: 'bg-gray-400', cancelled: 'bg-red-400',
    pending: 'bg-slate-400', assigned: 'bg-sky-400', review: 'bg-amber-500',
    rework: 'bg-orange-500', blocked: 'bg-rose-500', done: 'bg-emerald-500',
    disabled: 'bg-gray-400',
    planner: 'bg-violet-500', executor: 'bg-sky-500', reviewer: 'bg-amber-500', patrol: 'bg-teal-500',
    approved: 'bg-emerald-500', rejected: 'bg-rose-500',
}

function distTotal(dist: Record<string, number>) {
    return Object.values(dist).reduce((a, b) => a + b, 0)
}

function distPercent(count: number, total: number) {
    if (total === 0) return 0
    return Math.round((count / total) * 100)
}

// ─── 趋势图 SVG 工具 ───

const SPARK_W = 200
const SPARK_H = 40

function buildSparklinePath(values: number[]): { line: string; area: string } {
    if (!values.length) return { line: '', area: '' }
    const max = Math.max(...values, 1)
    const step = SPARK_W / Math.max(values.length - 1, 1)
    const points = values.map((v, i) => ({
        x: i * step,
        y: SPARK_H - (v / max) * (SPARK_H - 4) - 2,
    }))
    const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
    const area = line + ` L${SPARK_W},${SPARK_H} L0,${SPARK_H} Z`
    return { line, area }
}

interface TrendCard {
    title: string
    total: number
    color: string
    gradientId: string
    animKey: string
    values: number[]
}

const trendCards = computed<TrendCard[]>(() => {
    if (!trends.value) return []
    const t = trends.value
    return [
        {
            title: '新建子任务',
            total: t.sub_task_created_trend.reduce((a, b) => a + b.count, 0),
            color: '#3b82f6',
            gradientId: 'g-created',
            animKey: 'trend_created',
            values: t.sub_task_created_trend.map(p => p.count),
        },
        {
            title: '完成子任务',
            total: t.sub_task_completed_trend.reduce((a, b) => a + b.count, 0),
            color: '#10b981',
            gradientId: 'g-completed',
            animKey: 'trend_completed',
            values: t.sub_task_completed_trend.map(p => p.count),
        },
        {
            title: '审查总量',
            total: t.review_trend.reduce((a, b) => a + b.total, 0),
            color: '#f59e0b',
            gradientId: 'g-review',
            animKey: 'trend_review',
            values: t.review_trend.map(p => p.total),
        },
        {
            title: '积分净变化',
            total: t.score_delta_trend.reduce((a, b) => a + b.net_score_delta, 0),
            color: '#8b5cf6',
            gradientId: 'g-score',
            animKey: 'trend_score',
            values: t.score_delta_trend.map(p => p.net_score_delta),
        },
        {
            title: 'API 请求量',
            total: t.request_trend.reduce((a, b) => a + b.count, 0),
            color: '#06b6d4',
            gradientId: 'g-request',
            animKey: 'trend_request',
            values: t.request_trend.map(p => p.count),
        },
        {
            title: '活动日志',
            total: t.activity_trend.reduce((a, b) => a + b.count, 0),
            color: '#ec4899',
            gradientId: 'g-activity',
            animKey: 'trend_activity',
            values: t.activity_trend.map(p => p.count),
        },
    ]
})</script>

<template>
    <div class="flex flex-col h-[calc(100vh-3.5rem)] overflow-y-auto">
        <!-- 错误 -->
        <div v-if="error" class="flex flex-col items-center justify-center py-16">
            <AlertCircle class="h-5 w-5 text-muted-foreground" />
            <p class="mt-2 text-sm">{{ error }}</p>
            <Button class="mt-3" size="sm" @click="loadData">重新加载</Button>
        </div>

        <!-- 加载中 -->
        <div v-else-if="loading" class="flex items-center justify-center py-16">
            <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
        </div>

        <!-- 主内容 -->
        <div v-else-if="data" class="p-5 space-y-6 max-w-5xl mx-auto w-full">
            <!-- 顶栏 -->
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-lg font-semibold">仪表盘</h1>
                    <p class="text-xs text-muted-foreground/60">
                        数据更新于 {{ new Date(data.generated_at).toLocaleString('zh-CN') }}
                    </p>
                </div>
                <Button variant="ghost" size="icon" class="h-8 w-8" @click="loadData">
                    <RefreshCw class="h-3.5 w-3.5" />
                </Button>
            </div>

            <!-- ─── 核心指标卡片 ─── -->
            <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Card v-for="(card, idx) in coreCards" :key="card.title"
                    class="animate-slide-up border-border/40 hover:border-border/70 transition-colors"
                    :style="{ animationDelay: `${idx * 50}ms` }">
                    <CardContent class="flex items-center gap-3 p-4">
                        <div class="rounded-lg p-2.5" :class="card.bg">
                            <component :is="card.icon" class="h-5 w-5" :class="card.color" />
                        </div>
                        <div>
                            <div class="text-2xl font-bold tabular-nums leading-tight">{{ animatedValues[card.animKey]
                                ?? card.value }}</div>
                            <div class="text-xs text-muted-foreground">{{ card.title }}</div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <!-- ─── 次级指标 ─── -->
            <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <div class="rounded-lg border border-border/40 bg-card p-3 text-center animate-slide-up"
                    style="animation-delay: 300ms">
                    <div class="text-lg font-bold tabular-nums">{{ data.secondary_cards.disabled_agent_count }}</div>
                    <div class="text-[11px] text-muted-foreground">已禁用 Agent</div>
                </div>
                <div class="rounded-lg border border-border/40 bg-card p-3 text-center animate-slide-up"
                    style="animation-delay: 350ms">
                    <div class="text-lg font-bold tabular-nums">{{ data.secondary_cards.today_review_count }}</div>
                    <div class="text-[11px] text-muted-foreground">今日审查</div>
                </div>
                <div class="rounded-lg border border-border/40 bg-card p-3 text-center animate-slide-up"
                    style="animation-delay: 400ms">
                    <div class="text-lg font-bold tabular-nums">{{ data.secondary_cards.today_rejected_review_count }}
                    </div>
                    <div class="text-[11px] text-muted-foreground">今日驳回</div>
                </div>
                <div class="rounded-lg border border-border/40 bg-card p-3 text-center animate-slide-up"
                    style="animation-delay: 450ms">
                    <div class="text-lg font-bold tabular-nums">{{ data.secondary_cards.today_reject_rate.toFixed(1) }}%
                    </div>
                    <div class="text-[11px] text-muted-foreground">驳回率</div>
                </div>
                <div class="rounded-lg border border-border/40 bg-card p-3 text-center animate-slide-up"
                    style="animation-delay: 500ms">
                    <div class="flex items-center justify-center gap-1">
                        <TrendingUp v-if="data.secondary_cards.today_net_score_delta >= 0"
                            class="h-4 w-4 text-emerald-500" />
                        <TrendingDown v-else class="h-4 w-4 text-rose-500" />
                        <span class="text-lg font-bold tabular-nums"
                            :class="data.secondary_cards.today_net_score_delta >= 0 ? 'text-emerald-600' : 'text-rose-600'">
                            {{ data.secondary_cards.today_net_score_delta >= 0 ? '+' : '' }}{{
                                data.secondary_cards.today_net_score_delta }}
                        </span>
                    </div>
                    <div class="text-[11px] text-muted-foreground">今日积分净值</div>
                </div>
            </div>

            <Separator class="opacity-40" />

            <!-- ─── 状态分布 ─── -->
            <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <!-- 任务状态分布 -->
                <Card class="border-border/40 animate-slide-up" style="animation-delay: 550ms">
                    <CardHeader class="pb-2 px-4 pt-4">
                        <CardTitle class="text-sm font-medium text-muted-foreground">任务状态分布</CardTitle>
                    </CardHeader>
                    <CardContent class="px-4 pb-4 space-y-2">
                        <template v-for="(count, key) in data.distributions.task_status_distribution" :key="key">
                            <div class="flex items-center gap-2 text-sm">
                                <div class="w-2 h-2 rounded-full shrink-0"
                                    :class="statusColors[key] || 'bg-gray-400'" />
                                <span class="flex-1 truncate">{{ statusLabels[key] || key }}</span>
                                <span class="font-medium tabular-nums">{{ count }}</span>
                                <span class="text-[10px] text-muted-foreground/50 w-8 text-right tabular-nums">
                                    {{ distPercent(count, distTotal(data.distributions.task_status_distribution)) }}%
                                </span>
                            </div>
                        </template>
                        <!-- 进度条 -->
                        <div class="h-2 rounded-full bg-muted overflow-hidden flex mt-2">
                            <div v-for="(count, key) in data.distributions.task_status_distribution" :key="key"
                                class="h-full transition-all" :class="statusColors[key] || 'bg-gray-400'"
                                :style="{ width: `${distPercent(count, distTotal(data.distributions.task_status_distribution))}%` }" />
                        </div>
                    </CardContent>
                </Card>

                <!-- 子任务状态分布 -->
                <Card class="border-border/40 animate-slide-up" style="animation-delay: 600ms">
                    <CardHeader class="pb-2 px-4 pt-4">
                        <CardTitle class="text-sm font-medium text-muted-foreground">子任务状态分布</CardTitle>
                    </CardHeader>
                    <CardContent class="px-4 pb-4 space-y-2">
                        <template v-for="(count, key) in data.distributions.sub_task_status_distribution" :key="key">
                            <div class="flex items-center gap-2 text-sm">
                                <div class="w-2 h-2 rounded-full shrink-0"
                                    :class="statusColors[key] || 'bg-gray-400'" />
                                <span class="flex-1 truncate">{{ statusLabels[key] || key }}</span>
                                <span class="font-medium tabular-nums">{{ count }}</span>
                                <span class="text-[10px] text-muted-foreground/50 w-8 text-right tabular-nums">
                                    {{ distPercent(count, distTotal(data.distributions.sub_task_status_distribution))
                                    }}%
                                </span>
                            </div>
                        </template>
                        <div class="h-2 rounded-full bg-muted overflow-hidden flex mt-2">
                            <div v-for="(count, key) in data.distributions.sub_task_status_distribution" :key="key"
                                class="h-full transition-all" :class="statusColors[key] || 'bg-gray-400'"
                                :style="{ width: `${distPercent(count, distTotal(data.distributions.sub_task_status_distribution))}%` }" />
                        </div>
                    </CardContent>
                </Card>

                <!-- Agent 状态分布 -->
                <Card class="border-border/40 animate-slide-up" style="animation-delay: 650ms">
                    <CardHeader class="pb-2 px-4 pt-4">
                        <CardTitle class="text-sm font-medium text-muted-foreground">Agent 状态分布</CardTitle>
                    </CardHeader>
                    <CardContent class="px-4 pb-4 space-y-2">
                        <template v-for="(count, key) in data.distributions.agent_status_distribution" :key="key">
                            <div class="flex items-center gap-2 text-sm">
                                <div class="w-2 h-2 rounded-full shrink-0"
                                    :class="statusColors[key] || 'bg-gray-400'" />
                                <span class="flex-1 truncate">{{ statusLabels[key] || key }}</span>
                                <span class="font-medium tabular-nums">{{ count }}</span>
                                <span class="text-[10px] text-muted-foreground/50 w-8 text-right tabular-nums">
                                    {{ distPercent(count, distTotal(data.distributions.agent_status_distribution)) }}%
                                </span>
                            </div>
                        </template>
                        <div class="h-2 rounded-full bg-muted overflow-hidden flex mt-2">
                            <div v-for="(count, key) in data.distributions.agent_status_distribution" :key="key"
                                class="h-full transition-all" :class="statusColors[key] || 'bg-gray-400'"
                                :style="{ width: `${distPercent(count, distTotal(data.distributions.agent_status_distribution))}%` }" />
                        </div>
                    </CardContent>
                </Card>

                <!-- Agent 角色分布 -->
                <Card class="border-border/40 animate-slide-up" style="animation-delay: 700ms">
                    <CardHeader class="pb-2 px-4 pt-4">
                        <CardTitle class="text-sm font-medium text-muted-foreground">Agent 角色分布</CardTitle>
                    </CardHeader>
                    <CardContent class="px-4 pb-4 space-y-2">
                        <template v-for="(count, key) in data.distributions.agent_role_distribution" :key="key">
                            <div class="flex items-center gap-2 text-sm">
                                <div class="w-2 h-2 rounded-full shrink-0"
                                    :class="statusColors[key] || 'bg-gray-400'" />
                                <span class="flex-1 truncate">{{ statusLabels[key] || key }}</span>
                                <span class="font-medium tabular-nums">{{ count }}</span>
                                <span class="text-[10px] text-muted-foreground/50 w-8 text-right tabular-nums">
                                    {{ distPercent(count, distTotal(data.distributions.agent_role_distribution)) }}%
                                </span>
                            </div>
                        </template>
                        <div class="h-2 rounded-full bg-muted overflow-hidden flex mt-2">
                            <div v-for="(count, key) in data.distributions.agent_role_distribution" :key="key"
                                class="h-full transition-all" :class="statusColors[key] || 'bg-gray-400'"
                                :style="{ width: `${distPercent(count, distTotal(data.distributions.agent_role_distribution))}%` }" />
                        </div>
                    </CardContent>
                </Card>

                <!-- 近 7 天审查结果分布 -->
                <Card class="border-border/40 animate-slide-up" style="animation-delay: 750ms">
                    <CardHeader class="pb-2 px-4 pt-4">
                        <CardTitle class="text-sm font-medium text-muted-foreground">近 7 天审查结果</CardTitle>
                    </CardHeader>
                    <CardContent class="px-4 pb-4 space-y-2">
                        <template v-for="(count, key) in data.distributions.review_result_distribution_7d" :key="key">
                            <div class="flex items-center gap-2 text-sm">
                                <div class="w-2 h-2 rounded-full shrink-0"
                                    :class="statusColors[key] || 'bg-gray-400'" />
                                <span class="flex-1 truncate">{{ statusLabels[key] || key }}</span>
                                <span class="font-medium tabular-nums">{{ count }}</span>
                                <span class="text-[10px] text-muted-foreground/50 w-8 text-right tabular-nums">
                                    {{ distPercent(count, distTotal(data.distributions.review_result_distribution_7d))
                                    }}%
                                </span>
                            </div>
                        </template>
                        <div class="h-2 rounded-full bg-muted overflow-hidden flex mt-2">
                            <div v-for="(count, key) in data.distributions.review_result_distribution_7d" :key="key"
                                class="h-full transition-all" :class="statusColors[key] || 'bg-gray-400'"
                                :style="{ width: `${distPercent(count, distTotal(data.distributions.review_result_distribution_7d))}%` }" />
                        </div>
                    </CardContent>
                </Card>
            </div>

            <!-- ─── 趋势图 ─── -->
            <template v-if="trends && trendCards.length">
                <Separator class="opacity-40" />

                <div>
                    <div class="flex items-center justify-between mb-3">
                        <h2 class="text-sm font-medium text-muted-foreground">近 {{ trends.days }} 天趋势</h2>
                        <span class="text-[10px] text-muted-foreground/50 tabular-nums">{{ trends.start_date }} – {{
                            trends.end_date }}</span>
                    </div>
                    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        <Card v-for="(card, idx) in trendCards" :key="card.title"
                            class="border-border/40 animate-slide-up overflow-hidden"
                            :style="{ animationDelay: `${800 + idx * 50}ms` }">
                            <CardContent class="p-4 pb-0">
                                <div class="flex items-center justify-between mb-1">
                                    <span class="text-xs text-muted-foreground">{{ card.title }}</span>
                                    <span class="text-lg font-bold tabular-nums" :style="{ color: card.color }">{{
                                        animatedValues[card.animKey] ?? card.total }}</span>
                                </div>
                                <svg :viewBox="`0 0 ${SPARK_W} ${SPARK_H}`" class="w-full h-10"
                                    preserveAspectRatio="none">
                                    <defs>
                                        <linearGradient :id="card.gradientId" x1="0" x2="0" y1="0" y2="1">
                                            <stop offset="0%" :stop-color="card.color" stop-opacity="0.3" />
                                            <stop offset="100%" :stop-color="card.color" stop-opacity="0.02" />
                                        </linearGradient>
                                    </defs>
                                    <path :d="buildSparklinePath(card.values).area" :fill="`url(#${card.gradientId})`"
                                        class="sparkline-area" />
                                    <path :d="buildSparklinePath(card.values).line" fill="none" :stroke="card.color"
                                        stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                                        class="sparkline-line" />
                                </svg>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </template>

            <!-- ─── 高亮面板 ─── -->
            <template v-if="highlights && hasHighlights(highlights)">
                <Separator class="opacity-40" />

                <div class="grid gap-4 sm:grid-cols-2">
                    <!-- 阻塞子任务 -->
                    <Card v-if="highlights.blocked_sub_tasks.length" class="border-rose-200/50 animate-slide-up"
                        style="animation-delay: 800ms">
                        <CardHeader class="pb-2 px-4 pt-4">
                            <CardTitle class="text-sm font-medium flex items-center gap-1.5 text-rose-600">
                                <Ban class="h-3.5 w-3.5" /> 阻塞子任务
                            </CardTitle>
                        </CardHeader>
                        <CardContent class="px-4 pb-4 space-y-2">
                            <div v-for="item in highlights.blocked_sub_tasks" :key="item.id"
                                class="rounded border border-rose-100 bg-rose-50/30 p-2.5">
                                <div class="flex items-center justify-between">
                                    <span class="text-sm font-medium truncate flex-1">{{ item.name }}</span>
                                    <span class="text-[10px] text-muted-foreground/60 shrink-0 ml-2">{{
                                        formatRelativeTime(item.updated_at) }}</span>
                                </div>
                                <div class="text-[11px] text-muted-foreground mt-0.5 flex gap-3">
                                    <span>{{ item.task_name }}</span>
                                    <span v-if="item.assigned_agent_name">→ {{ item.assigned_agent_name }}</span>
                                    <span v-if="item.rework_count">返工 {{ item.rework_count }} 次</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <!-- 待审查子任务 -->
                    <Card v-if="highlights.pending_review_sub_tasks.length" class="border-amber-200/50 animate-slide-up"
                        style="animation-delay: 850ms">
                        <CardHeader class="pb-2 px-4 pt-4">
                            <CardTitle class="text-sm font-medium flex items-center gap-1.5 text-amber-600">
                                <Clock class="h-3.5 w-3.5" /> 待审查子任务
                            </CardTitle>
                        </CardHeader>
                        <CardContent class="px-4 pb-4 space-y-2">
                            <div v-for="item in highlights.pending_review_sub_tasks" :key="item.id"
                                class="rounded border border-amber-100 bg-amber-50/30 p-2.5">
                                <div class="flex items-center justify-between">
                                    <span class="text-sm font-medium truncate flex-1">{{ item.name }}</span>
                                    <span class="text-[10px] text-muted-foreground/60 shrink-0 ml-2">{{
                                        formatRelativeTime(item.updated_at) }}</span>
                                </div>
                                <div class="text-[11px] text-muted-foreground mt-0.5">
                                    {{ item.task_name }}
                                    <span v-if="item.assigned_agent_name"> → {{ item.assigned_agent_name }}</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <!-- 高负载 Agent -->
                    <Card v-if="highlights.busy_agents.length" class="border-sky-200/50 animate-slide-up"
                        style="animation-delay: 900ms">
                        <CardHeader class="pb-2 px-4 pt-4">
                            <CardTitle class="text-sm font-medium flex items-center gap-1.5 text-sky-600">
                                <Zap class="h-3.5 w-3.5" /> 高负载 Agent
                            </CardTitle>
                        </CardHeader>
                        <CardContent class="px-4 pb-4 space-y-2">
                            <div v-for="agent in highlights.busy_agents" :key="agent.id"
                                class="rounded border border-sky-100 bg-sky-50/30 p-2.5 flex items-center justify-between">
                                <div>
                                    <span class="text-sm font-medium">{{ agent.name }}</span>
                                    <span class="text-[11px] text-muted-foreground ml-1">{{ roleLabels[agent.role] ||
                                        agent.role }}</span>
                                </div>
                                <div class="text-right">
                                    <div class="text-sm font-bold tabular-nums">{{ agent.open_sub_task_count }} 个任务
                                    </div>
                                    <div class="text-[10px] text-muted-foreground/60">积分 {{ agent.total_score }}</div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <!-- 低活跃 Agent -->
                    <Card v-if="highlights.low_activity_agents.length" class="border-border/40 animate-slide-up"
                        style="animation-delay: 950ms">
                        <CardHeader class="pb-2 px-4 pt-4">
                            <CardTitle class="text-sm font-medium flex items-center gap-1.5 text-muted-foreground">
                                <Moon class="h-3.5 w-3.5" /> 低活跃 Agent
                            </CardTitle>
                        </CardHeader>
                        <CardContent class="px-4 pb-4 space-y-2">
                            <div v-for="agent in highlights.low_activity_agents" :key="agent.id"
                                class="rounded border border-border/50 bg-muted/20 p-2.5 flex items-center justify-between">
                                <div>
                                    <span class="text-sm font-medium">{{ agent.name }}</span>
                                    <span class="text-[11px] text-muted-foreground ml-1">{{ roleLabels[agent.role] ||
                                        agent.role }}</span>
                                </div>
                                <div class="text-[11px] text-muted-foreground/60">
                                    最近活动 {{ formatRelativeTime(agent.last_activity_at) }}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <!-- 最近审查 -->
                <Card v-if="highlights.recent_reviews.length" class="border-border/40 animate-slide-up"
                    style="animation-delay: 1000ms">
                    <CardHeader class="pb-2 px-4 pt-4">
                        <CardTitle class="text-sm font-medium flex items-center gap-1.5 text-violet-600">
                            <Star class="h-3.5 w-3.5" /> 最近审查
                        </CardTitle>
                    </CardHeader>
                    <CardContent class="px-4 pb-4">
                        <div class="divide-y divide-border/20">
                            <div v-for="review in highlights.recent_reviews" :key="review.id"
                                class="flex items-center gap-3 py-2">
                                <div class="w-2 h-2 rounded-full shrink-0"
                                    :class="review.result === 'approved' ? 'bg-emerald-500' : 'bg-rose-500'" />
                                <div class="flex-1 min-w-0">
                                    <div class="text-sm truncate">{{ review.sub_task_name }}</div>
                                    <div class="text-[11px] text-muted-foreground/60">{{ review.reviewer_agent_name ||
                                        '—' }} · {{ review.task_name }}</div>
                                </div>
                                <span class="text-amber-500 text-xs shrink-0">{{ '★'.repeat(Math.min(5, review.score))
                                    }}{{ '☆'.repeat(Math.max(0, 5 - review.score)) }}</span>
                                <span class="text-[10px] text-muted-foreground/50 shrink-0 tabular-nums">{{
                                    formatRelativeTime(review.created_at) }}</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </template>
        </div>
    </div>
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

/* Sparkline draw-in animation */
@keyframes sparkline-draw {
    from {
        stroke-dashoffset: 500;
    }

    to {
        stroke-dashoffset: 0;
    }
}

@keyframes sparkline-area-in {
    from {
        opacity: 0;
    }

    to {
        opacity: 1;
    }
}

.sparkline-line {
    stroke-dasharray: 500;
    stroke-dashoffset: 500;
    animation: sparkline-draw 1.2s ease-out 0.8s forwards;
}

.sparkline-area {
    opacity: 0;
    animation: sparkline-area-in 0.6s ease-out 1.4s forwards;
}
</style>
