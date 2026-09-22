<template>
  <div class="calendar-panel">
    <div class="cal-head">
      <span class="cal-title">{{ viewYear }} 年 {{ viewMonth }} 月</span>
      <span class="cal-nav">
        <el-segmented v-model="panelMode" size="small" :options="['月', '周']" />
        <el-button link @click="shiftMonth(-1)">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <el-button link @click="shiftMonth(1)">
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </span>
    </div>

    <div class="cal-week">
      <span v-for="w in weekLabels" :key="w" class="cal-week-cell">{{ w }}</span>
    </div>

    <div class="cal-grid">
      <div
        v-for="cell in visibleCells"
        :key="cell.key"
        class="cal-cell"
        :class="{
          'is-out': !cell.inMonth,
          'is-selected': cell.date === selectedDate,
          'is-week': isSameWeek(cell.date),
        }"
        @click="pick(cell.date)"
      >
        <span class="cal-day" :class="{ 'is-today': cell.date === today }">
          {{ cell.day }}
        </span>
      </div>
    </div>

    <div class="cal-foot">
      <el-tooltip content="快捷键 T" placement="top">
        <el-button class="today-btn" type="primary" link size="small" @click="goToday">
          回到今天
        </el-button>
      </el-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { dateToKey, daysInMonth, startOfWeek, todayStr } from '../utils/date'

const props = defineProps<{
  selectedDate: string
}>()

const emit = defineEmits<{
  (e: 'select', date: string): void
}>()

const today = todayStr()
const weekLabels = ['一', '二', '三', '四', '五', '六', '日']
const panelMode = ref<'月' | '周'>('月')

const parts = props.selectedDate.split('-').map(Number)
const viewYear = ref(parts[0])
const viewMonth = ref(parts[1])

interface DayCell {
  key: string
  date: string
  day: number
  inMonth: boolean
}

const cells = computed<DayCell[]>(() => {
  const year = viewYear.value
  const month = viewMonth.value
  const first = new Date(year, month - 1, 1)
  const mondayIndex = (first.getDay() + 6) % 7
  const total = daysInMonth(year, month)
  const list: DayCell[] = []
  for (let i = 0; i < mondayIndex; i++) {
    const day = daysInMonth(year, month - 1) - mondayIndex + i + 1
    const [py, pm] = month === 1 ? [year - 1, 12] : [year, month - 1]
    list.push({ key: 'pre-' + i, date: dateToKey(py, pm, day), day, inMonth: false })
  }
  for (let day = 1; day <= total; day++) {
    list.push({ key: 'cur-' + day, date: dateToKey(year, month, day), day, inMonth: true })
  }
  const remainder = (7 - (list.length % 7)) % 7
  const [ny, nm] = month === 12 ? [year + 1, 1] : [year, month + 1]
  for (let day = 1; day <= remainder; day++) {
    list.push({ key: 'next-' + day, date: dateToKey(ny, nm, day), day, inMonth: false })
  }
  return list
})

const visibleCells = computed(() => {
  if (panelMode.value === '月') return cells.value
  const start = startOfWeek(props.selectedDate)
  const index = cells.value.findIndex((cell) => cell.date === start)
  return index >= 0 ? cells.value.slice(index, index + 7) : cells.value.slice(0, 7)
})

watch(
  () => props.selectedDate,
  (value) => {
    const [y, m] = value.split('-').map(Number)
    viewYear.value = y
    viewMonth.value = m
  },
)

function isSameWeek(date: string) {
  return startOfWeek(date) === startOfWeek(props.selectedDate)
}

function shiftMonth(offset: number) {
  let month = viewMonth.value + offset
  let year = viewYear.value
  if (month > 12) {
    month = 1
    year += 1
  } else if (month < 1) {
    month = 12
    year -= 1
  }
  viewYear.value = year
  viewMonth.value = month
}

function pick(date: string) {
  emit('select', date)
}

function goToday() {
  const t = todayStr()
  const [y, m] = t.split('-').map(Number)
  viewYear.value = y
  viewMonth.value = m
  pick(t)
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (event.key.toLowerCase() === 't' && !['INPUT', 'TEXTAREA'].includes(target.tagName)) {
    goToday()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.calendar-panel {
  background: #fff;
  border-radius: 8px;
  padding: 12px 10px 8px;
}

.cal-head,
.cal-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 0 4px 8px;
}

.cal-title {
  font-weight: 600;
  font-size: 14px;
}

.cal-week,
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.cal-week-cell {
  text-align: center;
  font-size: 12px;
  color: #909399;
  line-height: 24px;
}

.cal-grid {
  row-gap: 2px;
}

.cal-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 30px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s ease, color 0.15s ease;
}

.cal-cell:hover {
  background: #f1f3f6;
}

.cal-cell.is-out {
  opacity: 0.35;
}

.cal-cell.is-week {
  background: #f5f9ff;
}

.cal-cell.is-selected {
  background: #d8ebff;
}

.cal-day {
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  font-size: 13px;
  border-radius: 50%;
}

.cal-cell.is-selected .cal-day {
  color: #1677d2;
  font-weight: 700;
}

.cal-day.is-today {
  font-weight: 700;
  color: #409eff;
}

.cal-foot {
  display: flex;
  justify-content: center;
  padding-top: 4px;
}

.today-btn:hover {
  background: #ecf5ff;
}
</style>
