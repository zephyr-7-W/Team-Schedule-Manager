<template>
  <el-dialog
    v-model="dialogVisible"
    title="AI 生成日程"
    width="620px"
    :close-on-click-modal="false"
  >
    <div class="ai-input-row">
      <el-input
        v-model="text"
        type="textarea"
        :rows="2"
        placeholder="用一句话描述，例如：明天下午3点到4点 张三 和后端评审接口方案"
      />
      <el-button
        type="primary"
        :loading="parsing"
        :disabled="!text.trim()"
        @click="parse"
      >
        AI 解析
      </el-button>
    </div>

    <template v-if="result">
      <el-alert
        class="ai-alert"
        :title="result.message"
        :type="result.source === 'llm' ? 'success' : 'info'"
        :closable="false"
        show-icon
      />
      <template v-if="result.conflicts.length">
        <div class="conflict-title">冲突提示（可继续保存，但建议调整时间）：</div>
        <el-alert
          v-for="(conflict, index) in result.conflicts"
          :key="index"
          :title="conflict"
          type="error"
          :closable="false"
        />
      </template>
    </template>

    <el-form v-if="result" label-width="76px" class="ai-form">
      <el-form-item label="成员" required>
        <el-select v-model="form.user_id" placeholder="选择成员" style="width: 100%">
          <el-option
            v-for="member in members"
            :key="member.id"
            :value="member.id"
            :label="member.name + '（' + (member.role || '成员') + '）'"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="标题" required>
        <el-input v-model="form.title" maxlength="50" />
      </el-form-item>
      <el-form-item label="日期" required>
        <el-date-picker
          v-model="form.date"
          type="date"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="时间段" required>
        <el-time-picker
          v-model="form.range"
          is-range
          format="HH:mm"
          value-format="HH:mm"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="地点">
        <el-input v-model="form.location" placeholder="可选" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialogVisible = false">关闭</el-button>
      <el-button
        type="primary"
        :disabled="!result"
        :loading="saving"
        @click="save"
      >
        保存日程
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { aiParseSchedule } from '../../api/ai'
import { createSchedule } from '../../api/schedules'
import type { AiParseResult, Member } from '../../types'

const props = defineProps<{
  modelValue: boolean
  members: Member[]
  defaultDate: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const text = ref('')
const parsing = ref(false)
const saving = ref(false)
const result = ref<AiParseResult | null>(null)

const form = reactive({
  user_id: null as number | null,
  title: '',
  date: props.defaultDate,
  range: ['09:00', '10:00'] as string[],
  location: '',
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    text.value = ''
    result.value = null
    form.user_id = null
    form.title = ''
    form.date = props.defaultDate
    form.range = ['09:00', '10:00']
    form.location = ''
  },
)

async function parse() {
  if (!text.value.trim()) return
  parsing.value = true
  try {
    const response = await aiParseSchedule(text.value.trim())
    result.value = response
    const candidate = response.schedule
    form.user_id = candidate.user_id
    form.title = candidate.title
    form.date = candidate.date || props.defaultDate
    if (candidate.start_time) {
      form.range = [
        candidate.start_time,
        candidate.end_time || addHour(candidate.start_time),
      ]
    }
    form.location = candidate.location || ''
  } catch {
    // 错误提示由 http 拦截器统一处理
  } finally {
    parsing.value = false
  }
}

function addHour(value: string): string {
  const [hour, minute] = value.split(':').map(Number)
  const total = hour * 60 + minute + 60
  return (
    Math.floor(total / 60)
      .toString()
      .padStart(2, '0') +
    ':' +
    (total % 60).toString().padStart(2, '0')
  )
}

async function save() {
  if (!form.user_id) {
    ElMessage.warning('请选择成员')
    return
  }
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (form.range[0] >= form.range[1]) {
    ElMessage.warning('结束时间必须晚于开始时间')
    return
  }
  saving.value = true
  try {
    await createSchedule({
      user_id: form.user_id,
      title: form.title.trim(),
      date: form.date,
      start_time: form.range[0],
      end_time: form.range[1],
      location: form.location.trim(),
    })
    ElMessage.success('日程已保存')
    dialogVisible.value = false
    emit('saved')
  } catch {
    // 错误提示由 http 拦截器统一处理
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ai-input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.ai-input-row .el-textarea {
  flex: 1;
}

.ai-alert {
  margin: 12px 0 4px;
}

.conflict-title {
  margin: 10px 0 4px;
  font-size: 12px;
  color: #f56c6c;
}

.ai-form {
  margin-top: 12px;
}
</style>
