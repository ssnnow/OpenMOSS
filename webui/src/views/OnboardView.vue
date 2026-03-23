<script setup lang="ts">
import { ref, computed } from 'vue'
import { adminApi } from '@/api/client'
import { toast } from 'vue-sonner'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Copy,
  Plus,
  Brain,
  Play,
  Search,
  Shield,
  Users
} from 'lucide-vue-next'

// ─── 状态 ───

const currentStep = ref(1)
const loading = ref(false)

// 步骤1：选择角色和名称
const agentName = ref('')
const selectedRole = ref('')

// 步骤2：生成的配置
const agentConfig = ref<any>(null)

// ─── 角色选项 ───

const roleOptions = [
  {
    value: 'planner',
    label: '规划者',
    description: '负责拆解需求、创建任务、分配工作',
    icon: Brain,
    color: 'border-violet-200 bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300'
  },
  {
    value: 'executor',
    label: '执行者',
    description: '负责认领任务、编写代码、提交成果',
    icon: Play,
    color: 'border-sky-200 bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300'
  },
  {
    value: 'reviewer',
    label: '审查者',
    description: '负责审查质量、评分、通过或驳回',
    icon: Search,
    color: 'border-amber-200 bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
  },
  {
    value: 'patrol',
    label: '巡查者',
    description: '负责巡查异常、标记阻塞、发送告警',
    icon: Shield,
    color: 'border-teal-200 bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300'
  }
]

// ─── 计算属性 ───

const canProceedToStep2 = computed(() => {
  return agentName.value.trim().length > 0 && selectedRole.value !== ''
})

const canProceedToStep3 = computed(() => {
  return agentConfig.value !== null
})

const selectedRoleInfo = computed(() => {
  return roleOptions.find(role => role.value === selectedRole.value)
})

// ─── 方法 ───

async function createAgent() {
  if (!canProceedToStep2.value) return

  loading.value = true
  try {
    const response = await adminApi.post('/admin/agents/create-openclaw', {
      name: agentName.value.trim(),
      role: selectedRole.value,
      cron_schedule: '0 9 * * *' // 默认每天9点运行
    })

    agentConfig.value = response.data
    currentStep.value = 2
    toast.success('Agent 创建成功！')
  } catch (error: any) {
    toast.error(`创建失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  toast.success('已复制到剪贴板')
}

function resetWizard() {
  currentStep.value = 1
  agentName.value = ''
  selectedRole.value = ''
  agentConfig.value = null
}

function goToStep(step: number) {
  if (step === 2 && !canProceedToStep2.value) return
  if (step === 3 && !canProceedToStep3.value) return
  currentStep.value = step
}
</script>

<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center gap-3">
      <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground text-base font-bold shadow-sm">
        <Plus class="h-5 w-5" />
      </div>
      <div>
        <h1 class="text-2xl font-bold tracking-tight">添加 Agent</h1>
        <p class="text-muted-foreground">通过简单的向导为你的团队添加新的 AI Agent</p>
      </div>
    </div>

    <!-- 步骤指示器 -->
    <div class="flex items-center justify-center gap-8 mb-8">
      <div v-for="step in 3" :key="step" class="flex items-center gap-4">
        <div
          class="flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors"
          :class="[
            step === currentStep
              ? 'border-primary bg-primary text-primary-foreground'
              : step < currentStep
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border bg-muted text-muted-foreground'
          ]"
        >
          {{ step }}
        </div>
        <div
          class="text-sm font-medium"
          :class="step === currentStep ? 'text-foreground' : 'text-muted-foreground'"
        >
          {{ step === 1 ? '选择角色' : step === 2 ? '获取配置' : '完成设置' }}
        </div>
        <div v-if="step < 3" class="h-px w-8 bg-border" />
      </div>
    </div>

    <!-- 步骤1：选择角色 -->
    <div v-if="currentStep === 1">
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <Users class="h-5 w-5" />
            选择 Agent 角色
          </CardTitle>
          <CardDescription>
            为你的 Agent 选择一个角色，不同的角色有不同的职责和技能
          </CardDescription>
        </CardHeader>
        <CardContent class="space-y-6">
          <!-- 角色选择 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="role in roleOptions"
              :key="role.value"
              class="relative cursor-pointer rounded-lg border-2 p-4 transition-all hover:shadow-md"
              :class="[
                selectedRole === role.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              ]"
              @click="selectedRole = role.value"
            >
              <div class="flex items-center gap-3">
                <component :is="role.icon" class="h-6 w-6" />
                <div>
                  <div class="font-medium">{{ role.label }}</div>
                  <div class="text-sm text-muted-foreground">{{ role.description }}</div>
                </div>
              </div>
              <div
                v-if="selectedRole === role.value"
                class="absolute top-2 right-2"
              >
                <Check class="h-4 w-4 text-primary" />
              </div>
            </div>
          </div>

          <!-- Agent 名称输入 -->
          <div class="space-y-2">
            <Label for="agent-name">Agent 名称</Label>
            <Input
              id="agent-name"
              v-model="agentName"
              placeholder="例如：我的规划助手、代码执行专家等"
              class="max-w-md"
            />
            <p class="text-sm text-muted-foreground">
              为你的 Agent 起一个容易识别的名字
            </p>
          </div>
        </CardContent>
        <CardFooter class="flex justify-between">
          <Button variant="outline" disabled>上一步</Button>
          <Button
            :disabled="!canProceedToStep2 || loading"
            @click="createAgent"
          >
            <span v-if="loading" class="flex items-center gap-2">
              <div class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              创建中...
            </span>
            <span v-else class="flex items-center gap-2">
              创建 Agent <ArrowRight class="h-4 w-4" />
            </span>
          </Button>
        </CardFooter>
      </Card>
    </div>

    <!-- 步骤2：配置信息 -->
    <div v-if="currentStep === 2">
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <Check class="h-5 w-5 text-green-600" />
            Agent 创建成功！
          </CardTitle>
          <CardDescription>
            以下是你的 Agent 配置信息，请按照下面的步骤完成设置
          </CardDescription>
        </CardHeader>
        <CardContent class="space-y-6">
          <!-- Agent 基本信息 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-1">
              <Label class="text-sm text-muted-foreground">Agent 名称</Label>
              <div class="font-medium">{{ agentConfig?.name }}</div>
            </div>
            <div class="space-y-1">
              <Label class="text-sm text-muted-foreground">角色</Label>
              <Badge :class="selectedRoleInfo?.color">
                {{ selectedRoleInfo?.label }}
              </Badge>
            </div>
            <div class="space-y-1">
              <Label class="text-sm text-muted-foreground">服务器地址</Label>
              <div class="flex items-center gap-2">
                <code class="text-sm bg-muted px-2 py-1 rounded">{{ agentConfig?.api_url_hint }}</code>
                <Button variant="ghost" size="sm" @click="copyToClipboard(agentConfig?.api_url_hint)">
                  <Copy class="h-3 w-3" />
                </Button>
              </div>
            </div>
            <div class="space-y-1">
              <Label class="text-sm text-muted-foreground">注册令牌</Label>
              <div class="flex items-center gap-2">
                <code class="text-sm bg-muted px-2 py-1 rounded">{{ agentConfig?.registration_token }}</code>
                <Button variant="ghost" size="sm" @click="copyToClipboard(agentConfig?.registration_token)">
                  <Copy class="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>

          <Separator />

          <!-- 接入步骤（来自后端） -->
          <div class="space-y-4">
            <h3 class="font-medium">接入步骤</h3>
            <div
              v-for="(step, index) in agentConfig?.openclaw_setup_steps"
              :key="index"
              class="space-y-2"
            >
              <div class="flex items-start gap-3">
                <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold mt-0.5">
                  {{ index + 1 }}
                </div>
                <div class="flex-1 space-y-1">
                  <div class="flex items-start gap-2">
                    <pre class="flex-1 text-sm bg-muted px-3 py-2 rounded whitespace-pre-wrap break-all font-mono">{{ step }}</pre>
                    <Button variant="ghost" size="sm" class="shrink-0" @click="copyToClipboard(step)">
                      <Copy class="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
        <CardFooter class="flex justify-between">
          <Button variant="outline" @click="currentStep = 1">
            <ArrowLeft class="h-4 w-4 mr-2" />
            上一步
          </Button>
          <Button @click="currentStep = 3">
            完成设置 <ArrowRight class="h-4 w-4 ml-2" />
          </Button>
        </CardFooter>
      </Card>
    </div>

    <!-- 步骤3：完成 -->
    <div v-if="currentStep === 3">
      <Card>
        <CardHeader class="text-center">
          <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/20">
            <Check class="h-8 w-8 text-green-600" />
          </div>
          <CardTitle>设置完成！</CardTitle>
          <CardDescription>
            你的 Agent 已经成功创建，现在可以开始工作了
          </CardDescription>
        </CardHeader>
        <CardContent class="text-center space-y-4">
          <p class="text-muted-foreground">
            Agent <strong>{{ agentConfig?.name }}</strong> 已添加到你的团队中。
          </p>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div class="space-y-1">
              <div class="font-medium">✅ Agent 已注册</div>
              <div class="text-muted-foreground">系统已记录 Agent 信息</div>
            </div>
            <div class="space-y-1">
              <div class="font-medium">✅ API Key 已生成</div>
              <div class="text-muted-foreground">Agent 可以访问系统 API</div>
            </div>
            <div class="space-y-1">
              <div class="font-medium">✅ 技能包已准备</div>
              <div class="text-muted-foreground">包含角色专属技能</div>
            </div>
          </div>

          <div class="bg-muted/50 rounded-lg p-4 text-left">
            <h4 class="font-medium mb-2">下一步操作建议：</h4>
            <ul class="text-sm text-muted-foreground space-y-1">
              <li>• 在 Agent 机器上运行配置命令完成设置</li>
              <li>• 前往「Agent 管理」页面查看新创建的 Agent</li>
              <li>• 为 Agent 分配任务开始工作</li>
            </ul>
          </div>
        </CardContent>
        <CardFooter class="flex justify-between">
          <Button variant="outline" @click="currentStep = 2">
            <ArrowLeft class="h-4 w-4 mr-2" />
            上一步
          </Button>
          <div class="flex gap-2">
            <Button variant="outline" @click="resetWizard">
              <Plus class="h-4 w-4 mr-2" />
              再添加一个
            </Button>
            <Button>
              前往 Agent 管理
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>