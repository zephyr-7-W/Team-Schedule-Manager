<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑日程' : '新建日程'"
    width="640px"
    :close-on-click-modal="false"
  >
    <el-alert
      v-if="readonly"
      title="普通成员只能修改自己的日程，当前日程仅可查看"
      type="info"
      :closable="false"
      show-icon
      class="readonly-tip"
    />

    <el-form label-width="96px" :disabled="readonly">
      <el-form-item label="日程标题" required>
        <el-input v-model="form.title" maxlength="80" placeholder="例如：需求评审 / 接口联调" />
      </el-form-item>

      <el-form-item label="负责人" required>
        <el-select v-model="form.user_id" placeholder="选择负责人" style="width: 100%">
          <el-option
            v-for="member in members"
            :key="member.id"
            :value="member.id"
            :label="member.name + '（' + (member.role || '成员') + '）'"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="参与人">
        <el-select v-model="form.participants" multiple collapse-tags collapse-tags-tooltip style="width: 100%">
          <el-option
            v-for="member in members"
            :key="member.id"
            :value="member.id"
            :label="member.name"
          />
        </el-select>
      </el-form-item>

      <div class="form-grid">
        <el-form-item label="日期" required>
          <el-date-picker
            v-model="form.date"
            type="date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="时间段" required>
          <div class="time-range">
            <el-select v-model="form.startTime" placeholder="开始" :teleported="true">
              <el-option v-for="time in timeOptions" :key="'start-' + time" :label="time" :value="time" />
            </el-select>
            <span class="time-separator">至</span>
            <el-select v-model="form.endTime" placeholder="结束" :teleported="true">
              <el-option v-for="time in timeOptions" :key="'end-' + time" :label="time" :value="time" />
            </el-select>
          </div>
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item label="标签类型">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="重复规则">
          <el-select v-model="form.recurrence" style="width: 100%">
            <el-option label="不重复" value="none" />
            <el-option label="每日重复" value="daily" />
            <el-option label="每周工作日重复" value="weekdays" />
            <el-option label="每周重复" value="weekly" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item label="地点/链接">
        <el-input v-model="form.location" placeholder="会议室 / 线上会议链接" />
      </el-form-item>

      <el-form-item label="提醒">
        <el-select v-model="form.reminder" style="width: 100%">
          <el-option :value="0" label="不提醒" />
          <el-option :value="5" label="提前 5 分钟" />
          <el-option :value="10" label="提前 10 分钟" />
          <el-option :value="30" label="提前 30 分钟" />
        </el-select>
      </el-form-item>

      <el-form-item label="备注提醒">
        <el-input v-model="form.note" type="textarea" :rows="3" placeholder="补充背景、会前准备或提醒内容" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button v-if="isEdit && !readonly" type="danger" plain @click="remove">删除</el-button>
      <el-button @click="dialogVisible = false">{{ readonly ? '关闭' : '取消' }}</el-button>
      <el-button v-if="!readonly" type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createSchedule, deleteSchedule, updateSchedule } from '../../api/schedules'
import type { Member, RecurrenceRule, Schedule, ScheduleCategory } from '../../types'

const props = defineProps<{
  modelValue: boolean
  schedule: Schedule | null
  members: Member[]
  defaultDate: string
  defaultUser: Member | null
  defaultStart?: string
  roleMode?: 'admin' | 'member'
  currentUserId?: number | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}>()

const categoryOptions: ScheduleCategory[] = ['会议', '开发', '评审', '复盘', '其他']
const timeOptions = Array.from({ length: 27 }, (_, index) => {
  const minutes = 8 * 60 + index * 30
  return Math.floor(minutes / 60).toString().padStart(2, '0') + ':' + (minutes % 60).toString().padStart(2, '0')
})

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const isEdit = computed(() => Boolean(props.schedule?.id))
const readonly = computed(() => props.roleMode === 'member' && Boolean(props.schedule) && props.schedule?.user_id !== props.currentUserId)
const saving = ref(false)

const form = reactive({
  user_id: null as number | null,
  title: '',
  date: props.defaultDate,
  startTime: '09:00',
  endTime: '10:00',
  location: '',
  note: '',
  category: '会议' as ScheduleCategory,
  recurrence: 'none' as RecurrenceRule,
  participants: [] as number[],
  reminder: 10,
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    const source = props.schedule
    const start = props.defaultStart ?? '09:00'
    form.user_id = source ? source.user_id : (props.defaultUser?.id ?? props.currentUserId ?? null)
    form.title = source ? source.title : ''
    form.date = source ? source.date : props.defaultDate
    form.startTime = source ? source.start_time : start
    form.endTime = source ? source.end_time : defaultEnd(start)
    form.location = source ? source.location : ''
    form.note = source ? source.note : ''
    form.category = source?.category ?? guessCategory(source?.title ?? '')
    form.recurrence = source?.recurrence ?? 'none'
    form.participants = source?.participants?.length ? [...source.participants] : (form.user_id ? [form.user_id] : [])
    form.reminder = source?.reminder ?? 10
  },
)

function defaultEnd(start: string) {
  const [hour, minute] = start.split(':').map(Number)
  const total = Math.min(23 * 60 + 59, hour * 60 + minute + 60)
  return Math.floor(total / 60).toString().padStart(2, '0') + ':' + (total % 60).toString().padStart(2, '0')
}

function guessCategory(title: string): ScheduleCategory {
  if (title.includes('开发') || title.includes('联调')) return '开发'
  if (title.includes('评审') || title.includes('走查')) return '评审'
  if (title.includes('复盘')) return '复盘'
  if (title.includes('会')) return '会议'
  return '其他'
}

function check(): string {
  if (!form.user_id) return '请选择负责人'
  if (!form.title.trim()) return '请填写日程标题'
  if (!form.date) return '请选择日期'
  if (!form.startTime || !form.endTime) return '请选择起止时间'
  if (form.startTime >= form.endTime) return '结束时间必须晚于开始时间'
  return ''
}

async function save() {
  const message = check()
  if (message) {
    ElMessage.warning(message)
    return
  }
  saving.value = true
  const payload = {
    user_id: form.user_id as number,
    title: form.title.trim(),
    date: form.date,
    start_time: form.startTime,
    end_time: form.endTime,
    location: form.location.trim(),
    note: form.note.trim(),
    category: form.category,
    recurrence: form.recurrence,
    participants: Array.from(new Set([form.user_id as number, ...form.participants])),
    reminder: form.reminder,
  }
  try {
    if (props.schedule) {
      await updateSchedule(props.schedule.id, payload)
      ElMessage.success('日程已更新')
    } else {
      await createSchedule(payload)
      ElMessage.success('日程已创建')
    }
    dialogVisible.value = false
    emit('saved')
  } catch {
    // 错误提示由 http 拦截器统一处理
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!props.schedule) return
  try {
    await ElMessageBox.confirm('确定删除该日程吗？', '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteSchedule(props.schedule.id)
    ElMessage.success('日程已删除')
    dialogVisible.value = false
    emit('saved')
  } catch {
    // 错误提示由 http 拦截器统一处理
  }
}
</script>

<style scoped>
.readonly-tip {
  margin-bottom: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.time-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-range .el-select {
  flex: 1;
  min-width: 0;
}

.time-separator {
  color: #909399;
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>
