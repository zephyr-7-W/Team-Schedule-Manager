<template>
  <div class="home-body">
    <aside class="side-panel">
      <CalendarPanel :selected-date="selectedDate" @select="onSelectDate" />
      <MemberList
        :members="members"
        :selected-id="selectedUserId"
        :active-date="selectedDate"
        :checked-ids="checkedIds"
        :schedules="schedules"
        @select="onSelectMember"
        @toggle-check="toggleMember"
        @check-all="checkAll"
        @clear-check="clearCheck"
        @add-member="memberDialogVisible = true"
        :is-admin="adminMode"
        @delete-member="removeMember"
      />
    </aside>

    <main class="main-panel">
      <div class="main-head">
        <div class="head-left">
          <div>
            <div class="head-kicker">团队排班工作台</div>
            <div class="head-date">{{ selectedDate }} <span>{{ weekdayText }}</span></div>
          </div>
          <el-tag v-if="selectedMember" :color="selectedMember.color" effect="dark">
            {{ selectedMember.name }}
          </el-tag>
          <el-tag v-else type="info" effect="plain">全员</el-tag>
          <span class="head-count">共 {{ filteredSchedules.length }} 条日程</span>
        </div>

        <div class="head-actions">
          <el-tooltip content="AI 根据项目快速批量创建团队日程" placement="bottom">
            <el-button type="primary" plain :loading="aiOpening" @click="openAi">
              <el-icon><MagicStick /></el-icon>
              AI 生成
            </el-button>
          </el-tooltip>
          <el-button type="primary" :loading="formOpening" @click="openAdd(null)">
            <el-icon><Plus /></el-icon>
            新建日程
          </el-button>
        </div>
      </div>

      <div class="toolbar">
        <el-radio-group v-model="viewMode" size="small" @change="loadSchedules">
          <el-radio-button label="day">日视图</el-radio-button>
          <el-radio-button label="week">周视图</el-radio-button>
          <el-radio-button label="workweek">工作周</el-radio-button>
          <el-radio-button label="month">月视图</el-radio-button>
        </el-radio-group>

        <div class="toolbar-right">
          <el-select v-model="categoryFilter" size="small" placeholder="日程类型" clearable>
            <el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-input v-model="tagFilter" size="small" clearable placeholder="筛选标题 / 标签" class="filter-input">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-dropdown trigger="click">
            <el-button size="small">
              <el-icon><Download /></el-icon>
              导出
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="exportIcs">导出 ICS 日历</el-dropdown-item>
                <el-dropdown-item @click="exportCsv">导出表格 CSV</el-dropdown-item>
                <el-dropdown-item divided @click="triggerImport">导入外部日历</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <input ref="importInput" class="hidden-input" type="file" accept=".ics,.csv,text/calendar,text/csv" @change="importCalendar" />
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-label">忙碌总时长</span>
          <strong>{{ totalBusyHours }}h</strong>
        </div>
        <div v-for="stat in categoryStats" :key="stat.label" class="stat-item">
          <span class="stat-swatch" :style="{ background: stat.color }"></span>
          <span class="stat-label">{{ stat.label }}</span>
          <strong>{{ stat.value }}</strong>
        </div>
        <div class="admin-toggle">
          <span>管理员模式</span>
          <el-switch v-model="adminMode" size="small" />
        </div>
      </div>

      <ScheduleTimeline
        :members="visibleMembers"
        :schedules="filteredSchedules"
        :loading="loading"
        :view-mode="viewMode"
        :selected-date="selectedDate"
        :can-edit="adminMode || selectedUserId !== null"
        @add="openAdd"
        @edit="openEdit"
        @copy="copySchedule"
        @remove="removeSchedule"
        @move="moveSchedule"
      />
    </main>
  </div>

  <ScheduleFormDialog
    v-model="formVisible"
    :schedule="editing"
    :members="members"
    :default-date="selectedDate"
    :default-user="formDefaultUser"
    :default-start="formDefaultStart"
    :role-mode="adminMode ? 'admin' : 'member'"
    :current-user-id="selectedUserId"
    @saved="reload"
  />

  <AiScheduleDialog v-model="aiVisible" :members="members" :default-date="selectedDate" @saved="reload" />

  <el-dialog v-model="memberDialogVisible" title="新增团队成员" width="420px">
    <el-form label-width="72px">
      <el-form-item label="姓名" required>
        <el-input v-model="newMember.name" placeholder="请输入成员姓名" />
      </el-form-item>
      <el-form-item label="岗位">
        <el-input v-model="newMember.role" placeholder="例如：前端开发" />
      </el-form-item>
      <el-form-item label="成员色">
        <el-color-picker v-model="newMember.color" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="memberDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="memberSaving" @click="saveMember">添加成员</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CalendarPanel from '../components/CalendarPanel.vue'
import MemberList from '../components/MemberList.vue'
import AiScheduleDialog from '../components/dialogs/AiScheduleDialog.vue'
import ScheduleFormDialog from '../components/dialogs/ScheduleFormDialog.vue'
import ScheduleTimeline from '../components/timeline/ScheduleTimeline.vue'
import { createSchedule, deleteSchedule, updateSchedule, listDailySchedules } from '../api/schedules'
import { createMember, deleteMember, listMembers } from '../api/users'
import type { Member, Schedule, ScheduleCategory } from '../types'
import { addDays, daysInMonth, parseHM, startOfWeek, todayStr } from '../utils/date'

const selectedDate = ref(todayStr())
const selectedUserId = ref<number | null>(null)
const members = ref<Member[]>([])
const schedules = ref<Schedule[]>([])
const checkedIds = ref<number[]>([])
const loading = ref(false)
const viewMode = ref<'day' | 'week' | 'workweek' | 'month'>('workweek')
const categoryFilter = ref<ScheduleCategory | ''>('')
const tagFilter = ref('')
const importInput = ref<HTMLInputElement | null>(null)
const formOpening = ref(false)
const aiOpening = ref(false)
const memberDialogVisible = ref(false)
const memberSaving = ref(false)
const adminMode = ref(true)
const newMember = ref({ name: '', role: '', color: '#5470c6' })

const formVisible = ref(false)
const aiVisible = ref(false)
const editing = ref<Schedule | null>(null)
const formDefaultUser = ref<Member | null>(null)
const formDefaultStart = ref('')

const categoryOptions: ScheduleCategory[] = ['会议', '开发', '评审', '复盘', '其他']
const weekdayMap = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const weekdayText = computed(() => {
  const [y, m, d] = selectedDate.value.split('-').map(Number)
  return weekdayMap[new Date(y, m - 1, d).getDay()]
})

const selectedMember = computed(() => members.value.find((item) => item.id === selectedUserId.value) ?? null)
const visibleMembers = computed(() => {
  const checked = members.value.filter((item) => checkedIds.value.includes(item.id))
  return selectedUserId.value ? checked.filter((item) => item.id === selectedUserId.value) : checked
})
const filteredSchedules = computed(() => schedules.value.filter((item) => {
  const categoryMatch = !categoryFilter.value || (item.category ?? guessCategory(item.title)) === categoryFilter.value
  const textMatch = !tagFilter.value || [item.title, item.note, item.location, item.category].join(' ').toLowerCase().includes(tagFilter.value.toLowerCase())
  return categoryMatch && textMatch
}))
const totalBusyHours = computed(() => (filteredSchedules.value.reduce((sum, item) => sum + parseHM(item.end_time) - parseHM(item.start_time), 0) / 60).toFixed(1))
const categoryStats = computed(() => categoryOptions.map((label) => ({
  label,
  value: filteredSchedules.value.filter((item) => (item.category ?? guessCategory(item.title)) === label).length,
  color: { 会议: '#409eff', 开发: '#67c23a', 评审: '#e6a23c', 复盘: '#8b6fd8', 其他: '#909399' }[label],
})).filter((item) => item.value))

async function loadMembers() {
  members.value = await listMembers()
  checkedIds.value = members.value.map((item) => item.id)
}

async function saveMember() {
  if (!newMember.value.name.trim()) {
    ElMessage.warning('请输入成员姓名')
    return
  }
  memberSaving.value = true
  try {
    const member = await createMember({
      name: newMember.value.name.trim(),
      role: newMember.value.role.trim(),
      color: newMember.value.color,
    })
    members.value = [...members.value, member]
    checkedIds.value = [...checkedIds.value, member.id]
    newMember.value = { name: '', role: '', color: '#5470c6' }
    memberDialogVisible.value = false
    ElMessage.success('成员已添加')
  } finally {
    memberSaving.value = false
  }
}

async function removeMember(member: Member) {
  try {
    await ElMessageBox.confirm(`确定删除成员“${member.name}”及其关联日程吗？`, '删除成员', { type: 'warning' })
  } catch {
    return
  }
  await deleteMember(member.id)
  members.value = members.value.filter((item) => item.id !== member.id)
  checkedIds.value = checkedIds.value.filter((id) => id !== member.id)
  if (selectedUserId.value === member.id) selectedUserId.value = null
  await loadSchedules()
  ElMessage.success('成员已删除')
}

async function loadSchedules() {
  loading.value = true
  try {
    let dates = [selectedDate.value]
    if (viewMode.value === 'week' || viewMode.value === 'workweek') {
      const start = startOfWeek(selectedDate.value)
      dates = Array.from({ length: viewMode.value === 'workweek' ? 5 : 7 }, (_, index) => addDays(start, index))
    } else if (viewMode.value === 'month') {
      const [year, month] = selectedDate.value.split('-').map(Number)
      dates = Array.from({ length: daysInMonth(year, month) }, (_, index) => {
        const day = String(index + 1).padStart(2, '0')
        return year + '-' + String(month).padStart(2, '0') + '-' + day
      })
    }
    const batches = await Promise.all(dates.map((date) => listDailySchedules(date)))
    schedules.value = batches.flat()
  } finally {
    loading.value = false
  }
}

function reload() {
  void loadSchedules()
}

function onSelectDate(date: string) {
  selectedDate.value = date
}

function onSelectMember(memberId: number | null) {
  selectedUserId.value = memberId
}

function toggleMember(memberId: number) {
  checkedIds.value = checkedIds.value.includes(memberId)
    ? checkedIds.value.filter((id) => id !== memberId)
    : [...checkedIds.value, memberId]
}

function checkAll() {
  checkedIds.value = members.value.map((item) => item.id)
}

function clearCheck() {
  checkedIds.value = []
}

function openAdd(member: Member | null, startTime = '', date = selectedDate.value) {
  if (!adminMode.value && !selectedUserId.value && !member) {
    ElMessage.info('普通成员模式下，请先选择自己的成员行')
    return
  }
  formOpening.value = true
  editing.value = null
  formDefaultUser.value = member
  formDefaultStart.value = startTime
  selectedDate.value = date
  formVisible.value = true
  window.setTimeout(() => { formOpening.value = false }, 220)
}

function openEdit(schedule: Schedule) {
  editing.value = schedule
  formDefaultUser.value = null
  formDefaultStart.value = ''
  formVisible.value = true
}

async function copySchedule(schedule: Schedule) {
  await createSchedule({
    user_id: schedule.user_id,
    title: schedule.title + '（副本）',
    date: schedule.date,
    start_time: schedule.start_time,
    end_time: schedule.end_time,
    location: schedule.location,
    note: schedule.note,
    category: schedule.category ?? guessCategory(schedule.title),
    recurrence: schedule.recurrence ?? 'none',
    participants: schedule.participants ?? [schedule.user_id],
    reminder: schedule.reminder ?? 10,
  })
  ElMessage.success('已复制日程')
  reload()
}

async function removeSchedule(schedule: Schedule) {
  await deleteSchedule(schedule.id)
  ElMessage.success('日程已删除')
  reload()
}

async function moveSchedule(schedule: Schedule, patch: Partial<Schedule>) {
  await updateSchedule(schedule.id, patch)
  ElMessage.success('日程时间已调整')
  reload()
}

function openAi() {
  aiOpening.value = true
  aiVisible.value = true
  window.setTimeout(() => { aiOpening.value = false }, 220)
}

function guessCategory(title: string): ScheduleCategory {
  if (title.includes('开发') || title.includes('联调')) return '开发'
  if (title.includes('评审') || title.includes('走查')) return '评审'
  if (title.includes('复盘')) return '复盘'
  if (title.includes('会')) return '会议'
  return '其他'
}

function download(name: string, content: string, type: string) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = name
  anchor.click()
  URL.revokeObjectURL(url)
}

function exportIcs() {
  const body = filteredSchedules.value.map((item) => {
    const stamp = item.date.replace(/-/g, '') + 'T' + item.start_time.replace(':', '') + '00'
    const end = item.date.replace(/-/g, '') + 'T' + item.end_time.replace(':', '') + '00'
    return ['BEGIN:VEVENT', 'UID:schedule-' + item.id, 'DTSTART:' + stamp, 'DTEND:' + end, 'SUMMARY:' + item.title, 'DESCRIPTION:' + item.note, 'LOCATION:' + item.location, 'END:VEVENT'].join('\r\n')
  }).join('\r\n')
  download('team-schedule.ics', 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\n' + body + '\r\nEND:VCALENDAR', 'text/calendar;charset=utf-8')
}

function exportCsv() {
  const rows = [['日期', '负责人', '标题', '类型', '开始', '结束', '地点', '备注']]
  filteredSchedules.value.forEach((item) => rows.push([item.date, item.user.name, item.title, item.category ?? guessCategory(item.title), item.start_time, item.end_time, item.location, item.note]))
  download('team-schedule.csv', rows.map((row) => row.map((value) => '"' + String(value).replace(/"/g, '""') + '"').join(',')).join('\n'), 'text/csv;charset=utf-8')
}

function triggerImport() {
  importInput.value?.click()
}

function importCalendar(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) ElMessage.success('已读取 ' + file.name + '，导入解析入口已就绪')
  ;(event.target as HTMLInputElement).value = ''
}

watch([selectedDate, selectedUserId], loadSchedules)

onMounted(() => {
  void loadMembers()
  void loadSchedules()
})
</script>

<style scoped>
.home-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 12px;
  padding: 12px;
}

.side-panel {
  width: 300px;
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.main-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.main-head,
.toolbar,
.stats-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  background: #fff;
  border-radius: 8px;
}

.head-left,
.head-actions,
.toolbar-right,
.stats-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.head-kicker {
  font-size: 11px;
  color: #909399;
  margin-bottom: 2px;
}

.head-date {
  font-size: 18px;
  font-weight: 700;
}

.head-date span {
  font-size: 13px;
  color: #909399;
  margin-left: 4px;
  font-weight: 400;
}

.head-count,
.stat-label {
  font-size: 12px;
  color: #909399;
}

.filter-input {
  width: 170px;
}

.hidden-input {
  display: none;
}

.stats-row {
  justify-content: flex-start;
  flex-wrap: wrap;
  padding: 8px 14px;
}

.stat-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-right: 14px;
  border-right: 1px solid #ebeef5;
}

.stat-item strong {
  color: #303133;
}

.stat-swatch {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.admin-toggle {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #667085;
  font-size: 12px;
}

@media (max-width: 980px) {
  .home-body {
    flex-direction: column;
    overflow: auto;
  }

  .side-panel {
    width: 100%;
    min-height: 300px;
  }

  .main-head,
  .toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-right {
    flex-wrap: wrap;
  }
}
</style>
