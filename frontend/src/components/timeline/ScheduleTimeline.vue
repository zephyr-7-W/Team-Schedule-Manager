<template>
  <div class="timeline" v-loading="loading">
    <template v-if="viewMode === 'month'">
      <div v-if="!loading && members.length === 0" class="empty-state">
        <div class="empty-illus">✓</div>
        <div class="empty-title">已隐藏全部成员</div>
        <div class="empty-text">请在左侧勾选要展示的成员</div>
      </div>
      <div v-else class="month-grid">
        <div
          v-for="cell in monthCells"
          :key="cell.key"
          class="month-cell"
          :class="{ 'is-pad': cell.pad, 'is-weekend': cell.weekend, today: cell.date === today }"
          @dblclick="onMonthBlankDbl(cell, $event)"
        >
          <div class="month-day">
            <span>{{ cell.day }}</span>
            <span v-if="cell.date === selectedDate" class="month-selected-dot"></span>
          </div>

          <template v-if="!cell.pad">
            <el-tooltip
              v-for="item in monthView(cell.date).head"
              :key="item.id"
              placement="top"
              effect="light"
              popper-class="timeline-popper"
            >
              <template #content>
                <CardTip :item="item" :members="members" :conflicts="conflictMap.get(item.id) ?? []" />
              </template>
              <button
                type="button"
                class="month-chip"
                :class="{ conflict: conflictIds.has(item.id) }"
                :style="chipStyle(item)"
                @dblclick.stop.prevent="emit('edit', item)"
                @contextmenu.prevent.stop="openCardMenu(item, $event)"
              >
                <span class="chip-dot" :style="{ background: memberColor(item) }"></span>
                <span class="chip-title">{{ item.title }}</span>
                <span v-if="canEdit" class="chip-actions" @pointerdown.stop @mousedown.stop @click.stop>
                  <el-icon @click.stop.prevent="emit('edit', item)"><Edit /></el-icon>
                  <el-icon @click.stop.prevent="emit('remove', item)"><Delete /></el-icon>
                </span>
              </button>
            </el-tooltip>

            <el-tooltip v-if="monthView(cell.date).more.length" placement="top" effect="light" popper-class="timeline-popper">
              <template #content>
                <div class="tip-list">
                  <div v-for="item in monthView(cell.date).more" :key="item.id" class="tip-list-row">
                    <i class="tip-dot" :style="{ background: memberColor(item) }"></i>
                    <span class="tip-list-title">{{ item.title }}</span>
                    <span class="tip-list-time">{{ shortTime(item.start_time) }} - {{ shortTime(item.end_time) }}</span>
                    <span class="tip-list-member">{{ item.user?.name }}</span>
                  </div>
                </div>
              </template>
              <span class="month-more">+{{ monthView(cell.date).more.length }} 更多</span>
            </el-tooltip>
          </template>
        </div>
      </div>
    </template>

    <template v-else-if="viewMode === 'day'">
      <div v-if="!loading && members.length === 0" class="empty-state">
        <div class="empty-illus">✓</div>
        <div class="empty-title">已隐藏全部成员</div>
        <div class="empty-text">请在左侧勾选要展示的成员</div>
      </div>
      <div v-else-if="!loading && dayRows.every((row) => row.cards.length === 0)" class="empty-state">
        <div class="empty-illus">+</div>
        <div class="empty-title">当日暂无团队日程</div>
        <div class="empty-text">双击空白时间格快速创建</div>
      </div>

      <div v-else class="day-calendar">
        <div class="day-header">
          <div class="member-head">成员</div>
          <div class="hours-head">
            <span v-for="hour in hourLabels" :key="hour">{{ hour }}</span>
          </div>
        </div>

        <div class="day-rows">
          <div v-for="row in dayRows" :key="row.member.id" class="day-row" :style="{ height: row.rowHeight + 'px' }">
            <div class="day-member">
              <span class="member-dot" :style="{ background: row.member.color }"></span>
              <span class="day-member-name">{{ row.member.name }}</span>
              <span class="day-member-role">{{ row.member.role || '成员' }}</span>
            </div>

            <div
              class="member-time-cell"
              @dblclick="(event) => addAtMember(row.member, event)"
              @contextmenu.prevent="(event) => openBlankMenu(selectedDate, event)"
            >
              <div class="hour-lines"></div>
              <div class="day-hover-add"><el-icon><Plus /></el-icon></div>

              <el-tooltip
                v-for="card in row.cards"
                :key="card.item.id"
                placement="top"
                effect="light"
                popper-class="timeline-popper"
              >
                <template #content>
                  <CardTip :item="card.item" :members="members" :conflicts="conflictMap.get(card.item.id) ?? []" />
                </template>
                <div
                  class="schedule-card day-schedule-card"
                  :class="{ conflict: conflictIds.has(card.item.id) }"
                  :style="card.style"
                  @click.stop.prevent
                  @dblclick.stop.prevent="emit('edit', card.item)"
                  @contextmenu.prevent.stop="openCardMenu(card.item, $event)"
                >
                  <span v-if="conflictIds.has(card.item.id)" class="conflict-badge">!</span>
                  <div class="card-drag-area" @pointerdown.stop="(event) => startDrag(card.item, selectedDate, 'move', event)">
                    <div class="card-title">{{ card.item.title }}</div>
                    <div class="card-meta">{{ shortTime(card.item.start_time) }} - {{ shortTime(card.item.end_time) }}</div>
                    <div v-if="card.item.location" class="card-meta card-location">
                      <el-icon><Location /></el-icon>{{ card.item.location }}
                    </div>
                  </div>
                  <span class="resize-handle top" @pointerdown.stop="(event) => startDrag(card.item, selectedDate, 'resize-start', event)"></span>
                  <span class="resize-handle bottom" @pointerdown.stop="(event) => startDrag(card.item, selectedDate, 'resize-end', event)"></span>
                  <div v-if="canEdit" class="card-actions" @pointerdown.stop @mousedown.stop @click.stop>
                    <el-button circle text size="small" @click.stop.prevent="emit('edit', card.item)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                    <el-button circle text size="small" @click.stop.prevent="emit('copy', card.item)">
                      <el-icon><CopyDocument /></el-icon>
                    </el-button>
                    <el-button circle text size="small" @click.stop.prevent="emit('remove', card.item)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>
              </el-tooltip>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div v-if="!loading && members.length === 0" class="empty-state">
        <div class="empty-illus">✓</div>
        <div class="empty-title">已隐藏全部成员</div>
        <div class="empty-text">请在左侧勾选要展示的成员</div>
      </div>
      <div v-else-if="!loading && weekCardsEmpty" class="empty-state">
        <div class="empty-illus">+</div>
        <div class="empty-title">该周期暂无团队日程</div>
        <div class="empty-text">双击空白时间格快速创建</div>
      </div>

      <div v-else class="week-calendar">
        <div class="week-header" :style="gridColumns">
          <div class="time-head">时间</div>
          <div
            v-for="day in visibleDates"
            :key="day.date"
            class="day-head"
            :class="{ today: day.date === today, 'is-weekend': day.isWeekend }"
          >
            <strong>{{ day.week }}</strong>
            <span>{{ day.date.slice(5) }}</span>
          </div>
        </div>

        <div class="week-body" :style="gridColumns">
          <div class="time-axis">
            <div v-for="slot in axisSlots" :key="slot.label" class="axis-slot" :style="{ top: slot.pctTop + '%', height: hourBandPct + '%' }">
              <span>{{ slot.label }}</span>
            </div>
          </div>

          <div
            v-for="day in visibleDates"
            :key="day.date"
            class="day-column"
            :class="{ 'is-weekend': day.isWeekend }"
            @dblclick="(event) => addAtDay(day.date, event)"
            @contextmenu.prevent="(event) => openBlankMenu(day.date, event)"
          >
            <div class="hour-lines"></div>
            <div class="day-hover-add"><el-icon><Plus /></el-icon></div>

            <el-tooltip
              v-for="card in (weekCardsByDate.get(day.date) ?? [])"
              :key="card.item.id"
              placement="top"
              effect="light"
              popper-class="timeline-popper"
            >
              <template #content>
                <CardTip :item="card.item" :members="members" :conflicts="conflictMap.get(card.item.id) ?? []" />
              </template>
              <div
                class="schedule-card week-schedule-card"
                :class="{ conflict: conflictIds.has(card.item.id) }"
                :style="card.style"
                @click.stop.prevent
                @dblclick.stop.prevent="emit('edit', card.item)"
                @contextmenu.prevent.stop="openCardMenu(card.item, $event)"
              >
                <span v-if="conflictIds.has(card.item.id)" class="conflict-badge">!</span>
                <div class="card-drag-area" @pointerdown.stop="(event) => startDrag(card.item, day.date, 'move', event)">
                  <template v-if="(card.members?.length ?? 1) > 1">
                    <div class="card-title">{{ card.item.title }}</div>
                    <div class="card-participants">
                      <span v-for="attendee in card.members ?? []" :key="attendee.id" class="p-chip">
                        <i class="member-dot" :style="{ background: memberColor(attendee) }"></i>
                        <span class="p-name">{{ memberName(attendee) }}</span>
                      </span>
                    </div>
                  </template>
                  <template v-else>
                    <div class="card-member" :style="{ color: memberColor(card.item) }">
                      <span class="member-dot" :style="{ background: memberColor(card.item) }"></span>
                      {{ memberName(card.item) }}
                    </div>
                    <div class="card-title">{{ card.item.title }}</div>
                  </template>
                  <div class="card-meta">{{ shortTime(card.item.start_time) }} - {{ shortTime(card.item.end_time) }}</div>
                </div>
                <span class="resize-handle top" @pointerdown.stop="(event) => startDrag(card.item, day.date, 'resize-start', event)"></span>
                <span class="resize-handle bottom" @pointerdown.stop="(event) => startDrag(card.item, day.date, 'resize-end', event)"></span>
                <div v-if="canEdit" class="card-actions" @pointerdown.stop @mousedown.stop @click.stop>
                  <el-button circle text size="small" @click.stop.prevent="emit('edit', card.item)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button circle text size="small" @click.stop.prevent="emit('copy', card.item)">
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                  <el-button circle text size="small" @click.stop.prevent="emit('remove', card.item)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
            </el-tooltip>
          </div>
        </div>
      </div>
    </template>

    <div v-if="contextMenu.visible" class="context-menu" :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }">
      <button v-for="item in contextOptions" :key="item.label" type="button" @click="item.action">
        <el-icon><component :is="item.icon" /></el-icon>{{ item.label }}
      </button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { Component } from 'vue'
import type { Member, Schedule } from '../../types'
import {
  HOUR_END,
  HOUR_START,
  addDays,
  dateToKey,
  daysInMonth,
  parseHM,
  shortTime,
  startOfWeek,
  toHM,
  todayStr,
} from '../../utils/date'
import CardTip from './CardTip.vue'

const HOUR_HEIGHT = 40
const HALF_HOUR_HEIGHT = 20
const PERIOD_MINUTES = (HOUR_END - HOUR_START) * 60
const DAY_ROW_MIN = 72
const DAY_BAND = 40
const MAX_MONTH_CHIPS = 3
const DEFAULT_COLOR = '#5470c6'

const props = defineProps<{
  members: Member[]
  schedules: Schedule[]
  loading: boolean
  viewMode: 'day' | 'week' | 'workweek' | 'month'
  selectedDate: string
  canEdit: boolean
}>()

const emit = defineEmits<{
  (e: 'add', member: Member | null, startTime?: string, date?: string): void
  (e: 'edit', schedule: Schedule): void
  (e: 'copy', schedule: Schedule): void
  (e: 'remove', schedule: Schedule): void
  (e: 'move', schedule: Schedule, patch: Partial<Schedule>): void
}>()

const today = todayStr()
const weekNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const hourBandPct = 100 / (HOUR_END - HOUR_START)
const contextMenu = reactive({ visible: false, x: 0, y: 0, schedule: null as Schedule | null, date: '', time: '' })

const visibleIds = computed(() => new Set(props.members.map((member) => member.id)))
const gridColumns = computed(() => ({ gridTemplateColumns: '54px repeat(' + visibleDates.value.length + ', minmax(0, 1fr))' }))

const visibleDates = computed(() => {
  if (props.viewMode === 'day') return [dateMeta(props.selectedDate)]
  const start = startOfWeek(props.selectedDate)
  const length = props.viewMode === 'workweek' ? 5 : 7
  return Array.from({ length }, (_, index) => dateMeta(addDays(start, index)))
})

const axisSlots = computed(() =>
  Array.from({ length: HOUR_END - HOUR_START }, (_, index) => {
    const hour = HOUR_START + index
    return { pctTop: (index / (HOUR_END - HOUR_START)) * 100, label: String(hour).padStart(2, '0') + ':00' }
  }),
)
const hourLabels = computed(() =>
  Array.from({ length: HOUR_END - HOUR_START }, (_, index) => String(HOUR_START + index).padStart(2, '0') + ':00'),
)

interface MonthCell {
  key: string
  date: string
  day: number
  pad: boolean
  weekend: boolean
}

const monthCells = computed<MonthCell[]>(() => {
  const [year, month] = props.selectedDate.split('-').map(Number)
  const total = daysInMonth(year, month)
  const first = new Date(year, month - 1, 1)
  const lead = (first.getDay() + 6) % 7
  const list: MonthCell[] = []
  for (let index = 0; index < lead; index++) {
    list.push({ key: 'pad-l' + index, date: '', day: 0, pad: true, weekend: false })
  }
  for (let day = 1; day <= total; day++) {
    const weekday = new Date(year, month - 1, day).getDay()
    list.push({ key: dateToKey(year, month, day), date: dateToKey(year, month, day), day, pad: false, weekend: weekday === 0 || weekday === 6 })
  }
  while (list.length % 7 !== 0) {
    list.push({ key: 'pad-r' + list.length, date: '', day: 0, pad: true, weekend: false })
  }
  return list
})

function dateMeta(date: string) {
  const [year, month, day] = date.split('-').map(Number)
  const weekday = new Date(year, month - 1, day).getDay()
  return { date, week: weekNames[weekday], weekday, isWeekend: weekday === 0 || weekday === 6 }
}

function byTime(a: Schedule, b: Schedule) {
  return a.start_time.localeCompare(b.start_time) || a.id - b.id
}

function scheduleOn(date: string): Schedule[] {
  return props.schedules
    .filter((item) => item.date === date && visibleIds.value.has(item.user_id))
    .sort(byTime)
}

function memberColor(item: Schedule): string {
  return props.members.find((member) => member.id === item.user_id)?.color || item.user?.color || DEFAULT_COLOR
}

function memberName(item: Schedule): string {
  return props.members.find((member) => member.id === item.user_id)?.name || item.user?.name || '成员'
}

function hexA(hex: string, alpha: number): string {
  if (/^#[0-9a-fA-F]{6}$/.test(hex)) {
    const value = parseInt(hex.slice(1), 16)
    return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`
  }
  return hex + '1f'
}

function chipStyle(item: Schedule): Record<string, string> {
  const color = memberColor(item)
  return { background: hexA(color, 0.1), borderLeftColor: color, color: '#344054' }
}

/** 把同一时间轴上互相重叠的日程拆到不同的“分片/lane”，互不压盖。 */
function laneResult(items: Schedule[]): Map<number, { lane: number; lanes: number }> {
  const sorted = [...items].sort(byTime)
  const map = new Map<number, { lane: number; lanes: number }>()
  let group: Schedule[] = []
  let groupEnd = Number.NEGATIVE_INFINITY

  const flush = () => {
    if (group.length === 0) return
    const laneEnds: number[] = []
    for (const item of group) {
      const start = parseHM(item.start_time)
      const end = parseHM(item.end_time)
      let lane = laneEnds.findIndex((value) => value <= start)
      if (lane < 0) {
        lane = laneEnds.length
        laneEnds.push(0)
      }
      laneEnds[lane] = end
      map.set(item.id, { lane, lanes: 0 })
    }
    const lanes = laneEnds.length
    for (const item of group) {
      const info = map.get(item.id)
      if (info) info.lanes = lanes
    }
    group = []
  }

  for (const item of sorted) {
    const start = parseHM(item.start_time)
    const end = parseHM(item.end_time)
    if (group.length === 0 || start < groupEnd) {
      group.push(item)
      groupEnd = Math.max(groupEnd, end)
    } else {
      flush()
      group.push(item)
      groupEnd = end
    }
  }
  flush()
  return map
}

/** 按相同会议签名的多人日程聚合成单张卡片。 */
function spanLanes(
  entries: { key: string; startMin: number; endMin: number }[],
): Map<string, { lane: number; lanes: number }> {
  const sorted = [...entries].sort((a, b) => a.startMin - b.startMin || a.key.localeCompare(b.key))
  const map = new Map<string, { lane: number; lanes: number }>()
  let group: { key: string; startMin: number; endMin: number }[] = []
  let groupEnd = Number.NEGATIVE_INFINITY
  const flush = () => {
    if (group.length === 0) return
    const laneEnds: number[] = []
    for (const entry of group) {
      let lane = laneEnds.findIndex((value) => value <= entry.startMin)
      if (lane < 0) {
        lane = laneEnds.length
        laneEnds.push(0)
      }
      laneEnds[lane] = entry.endMin
      map.set(entry.key, { lane, lanes: 0 })
    }
    const lanes = laneEnds.length
    for (const entry of group) {
      const info = map.get(entry.key)
      if (info) info.lanes = lanes
    }
    group = []
  }
  for (const entry of sorted) {
    if (group.length === 0 || entry.startMin < groupEnd) {
      group.push(entry)
      groupEnd = Math.max(groupEnd, entry.endMin)
    } else {
      flush()
      group.push(entry)
      groupEnd = entry.endMin
    }
  }
  flush()
  return map
}

interface CardModel {
  item: Schedule
  style: Record<string, string>
  members?: Schedule[]
}
interface DayRowModel {
  member: Member
  rowHeight: number
  cards: CardModel[]
}
interface WeekColumnModel {
  date: string
  cards: CardModel[]
}

const dayRows = computed<DayRowModel[]>(() =>
  props.members.map((member) => {
    const items = props.schedules
      .filter((item) => item.date === props.selectedDate && item.user_id === member.id)
      .sort(byTime)
    const cards: CardModel[] = []
    let rowHeight = DAY_ROW_MIN
    if (items.length > 0) {
      const lanes = laneResult(items)
      let maxLanes = 1
      lanes.forEach((info) => {
        maxLanes = Math.max(maxLanes, info.lanes)
      })
      rowHeight = maxLanes > 1 ? maxLanes * DAY_BAND : DAY_ROW_MIN
      items.forEach((item) => {
        const info = lanes.get(item.id)
        if (!info) return
        const startMin = Math.max(HOUR_START * 60, parseHM(item.start_time))
        const endMin = Math.min(HOUR_END * 60, parseHM(item.end_time))
        const band = rowHeight / info.lanes
        const left = (((startMin - HOUR_START * 60) / PERIOD_MINUTES) * 100).toFixed(3)
        const width = (Math.max((endMin - startMin) / PERIOD_MINUTES, 0.01) * 100).toFixed(3)
        cards.push({
          item,
          style: {
            top: (info.lane * band + 2).toFixed(1) + 'px',
            height: Math.max(band - 4, 26).toFixed(1) + 'px',
            left: left + '%',
            width: 'calc(' + width + '% - 6px)',
            borderColor: memberColor(item),
            background: hexA(memberColor(item), 0.12),
          },
        })
      })
    }
    return { member, rowHeight, cards }
  }),
)

const weekCardsByDate = computed(() => {
  const result = new Map<string, CardModel[]>()
  visibleDates.value.forEach((day) => {
    const items = scheduleOn(day.date)
    const cards: CardModel[] = []
    if (items.length > 0) {
      // 同一份安排（同标题/同起止/同地点）合并为一张卡片，避免多人各占一格
      const buckets = new Map<string, Schedule[]>()
      items.forEach((item) => {
        const signature = [item.title, item.start_time, item.end_time, item.location || ''].join('\u0001')
        const list = buckets.get(signature) ?? []
        list.push(item)
        buckets.set(signature, list)
      })
      const units: { key: string; item: Schedule; members: Schedule[]; startMin: number; endMin: number }[] = []
      buckets.forEach((list) => {
        list.sort(byTime)
        const uniqueUsers = new Set(list.map((entry) => entry.user_id))
        if (list.length > 1 && uniqueUsers.size === list.length) {
          units.push({
            key: 'group-' + list[0].id,
            item: list[0],
            members: list,
            startMin: Math.max(HOUR_START * 60, parseHM(list[0].start_time)),
            endMin: Math.min(HOUR_END * 60, parseHM(list[0].end_time)),
          })
        } else {
          list.forEach((entry) => {
            units.push({
              key: 'unit-' + entry.id,
              item: entry,
              members: [entry],
              startMin: Math.max(HOUR_START * 60, parseHM(entry.start_time)),
              endMin: Math.min(HOUR_END * 60, parseHM(entry.end_time)),
            })
          })
        }
      })
      const lanes = spanLanes(units.map((unit) => ({ key: unit.key, startMin: unit.startMin, endMin: unit.endMin })))
      units
        .slice()
        .sort((a, b) => a.startMin - b.startMin || a.item.id - b.item.id)
        .forEach((unit) => {
          const info = lanes.get(unit.key)
          if (!info) return
          const hours = HOUR_END - HOUR_START
          const top = (((unit.startMin - HOUR_START * 60) / 60) / hours) * 100
          const rawHeight = Math.max((((unit.endMin - unit.startMin) / 60) / hours) * 100, 2.6)
          const laneWidth = 100 / info.lanes
          cards.push({
            item: unit.item,
            members: unit.members,
            style: {
              top: top.toFixed(3) + '%',
              height: rawHeight.toFixed(3) + '%',
              left: 'calc(' + (info.lane * laneWidth).toFixed(3) + '% + 2px)',
              width: 'calc(' + laneWidth.toFixed(3) + '% - 4px)',
              borderColor: memberColor(unit.item),
              background: hexA(memberColor(unit.item), 0.12),
            },
          })
        })
    }
    result.set(day.date, cards)
  })
  return result
})

const weekCardsEmpty = computed(() => Array.from(weekCardsByDate.value.values()).every((cards) => cards.length === 0))

function monthView(date: string) {
  const items = scheduleOn(date)
  return { head: items.slice(0, MAX_MONTH_CHIPS), more: items.slice(MAX_MONTH_CHIPS) }
}

const conflictMap = computed(() => {
  const byKey = new Map<string, Schedule[]>()
  props.schedules.forEach((item) => {
    if (!visibleIds.value.has(item.user_id)) return
    const key = item.date + ':' + item.user_id
    const list = byKey.get(key) ?? []
    list.push(item)
    byKey.set(key, list)
  })
  const result = new Map<number, Schedule[]>()
  byKey.forEach((list) => {
    list.sort(byTime)
    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        const a = list[i]
        const b = list[j]
        if (parseHM(a.start_time) < parseHM(b.end_time) && parseHM(b.start_time) < parseHM(a.end_time)) {
          result.set(a.id, [...(result.get(a.id) ?? []), b])
          result.set(b.id, [...(result.get(b.id) ?? []), a])
        }
      }
    }
  })
  return result
})
const conflictIds = computed(() => new Set(conflictMap.value.keys()))

const contextOptions = computed(() => {
  if (contextMenu.schedule) {
    const schedule = contextMenu.schedule
    return [
      { label: '查看详情', icon: 'View' as unknown as Component, action: () => chooseMenu(() => emit('edit', schedule)) },
      { label: '编辑', icon: 'Edit' as unknown as Component, action: () => chooseMenu(() => emit('edit', schedule)) },
      { label: '复制', icon: 'CopyDocument' as unknown as Component, action: () => chooseMenu(() => emit('copy', schedule)) },
      { label: '删除', icon: 'Delete' as unknown as Component, action: () => chooseMenu(() => emit('remove', schedule)) },
    ]
  }
  return [{ label: '快速新建日程', icon: 'Plus' as unknown as Component, action: () => chooseMenu(() => emit('add', null, contextMenu.time, contextMenu.date)) }]
})

function timeFromPoint(event: MouseEvent, axis: 'x' | 'y'): number {
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const ratio = axis === 'x' ? (event.clientX - rect.left) / Math.max(rect.width, 1) : (event.clientY - rect.top) / Math.max(rect.height, 1)
  const base = HOUR_START * 60 + Math.round((ratio * PERIOD_MINUTES) / 30) * 30
  return Math.max(HOUR_START * 60, Math.min((HOUR_END - 1) * 60, base))
}

function addAtMember(member: Member, event: MouseEvent) {
  if ((event.target as HTMLElement).closest('.schedule-card')) return
  emit('add', member, toHM(timeFromPoint(event, 'x')), props.selectedDate)
}

function addAtDay(date: string, event: MouseEvent) {
  if ((event.target as HTMLElement).closest('.schedule-card')) return
  emit('add', null, toHM(timeFromPoint(event, 'y')), date)
}

function onMonthBlankDbl(cell: MonthCell, event: MouseEvent) {
  if (cell.pad) return
  if ((event.target as HTMLElement).closest('.month-chip')) return
  emit('add', null, '', cell.date)
}

function openBlankMenu(date: string, event: MouseEvent) {
  contextMenu.visible = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.schedule = null
  contextMenu.date = date
  const target = event.currentTarget as HTMLElement
  contextMenu.time = toHM(timeFromPoint(event, target.classList.contains('member-time-cell') ? 'x' : 'y'))
}

function openCardMenu(schedule: Schedule, event: MouseEvent) {
  contextMenu.visible = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.schedule = schedule
}

function chooseMenu(action: () => void) {
  contextMenu.visible = false
  action()
}

function closeMenu() {
  contextMenu.visible = false
}

function startDrag(schedule: Schedule, date: string, mode: 'move' | 'resize-start' | 'resize-end', event: PointerEvent) {
  if (!props.canEdit) {
    ElMessage.info('当前账号没有修改该日程的权限')
    return
  }
  const isDay = props.viewMode === 'day'
  const cell = (event.currentTarget as HTMLElement).closest(isDay ? '.member-time-cell' : '.day-column') as HTMLElement | null
  const baseRect = cell?.getBoundingClientRect()
  const startX = event.clientX
  const startY = event.clientY
  const startTime = parseHM(schedule.start_time)
  const endTime = parseHM(schedule.end_time)
  const duration = endTime - startTime

  function onMove(moveEvent: PointerEvent) {
    moveEvent.preventDefault()
  }
  function onUp(upEvent: PointerEvent) {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    if (!baseRect) return
    const offset = isDay ? upEvent.clientX - startX : upEvent.clientY - startY
    const minutesPerPixel = isDay ? PERIOD_MINUTES / Math.max(baseRect.width, 1) : PERIOD_MINUTES / Math.max(baseRect.height, 1)
    const delta = Math.round((offset * minutesPerPixel) / 30) * 30
    let nextStart = startTime
    let nextEnd = endTime
    if (mode === 'move') {
      nextStart = Math.max(HOUR_START * 60, Math.min(HOUR_END * 60 - duration, startTime + delta))
      nextEnd = nextStart + duration
    } else if (mode === 'resize-start') {
      nextStart = Math.max(HOUR_START * 60, Math.min(endTime - 30, startTime + delta))
    } else {
      nextEnd = Math.min(HOUR_END * 60, Math.max(startTime + 30, endTime + delta))
    }
    emit('move', schedule, { date, start_time: toHM(nextStart), end_time: toHM(nextEnd) })
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}

onMounted(() => window.addEventListener('click', closeMenu))
onUnmounted(() => window.removeEventListener('click', closeMenu))
</script>
<style scoped>
.timeline {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

/* ---------- 空状态 ---------- */
.empty-state {
  flex: 1;
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #98a2b3;
}
.empty-illus {
  width: 56px;
  height: 56px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed #a9d3ff;
  border-radius: 8px;
  background: #f3f9ff;
  color: #409eff;
  font-size: 30px;
}
.empty-title { color: #475467; font-size: 14px; font-weight: 700; }
.empty-text { margin-top: 4px; font-size: 12px; }

/* ---------- 日视图 ---------- */
.day-calendar { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.day-header {
  flex: none;
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  min-height: 38px;
  border-bottom: 1px solid #e8edf3;
  background: #fbfcfe;
}
.member-head {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #98a2b3;
  font-size: 11px;
  border-right: 1px solid #e8edf3;
}
.hours-head { display: grid; grid-template-columns: repeat(13, minmax(0, 1fr)); min-width: 0; }
.hours-head span {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding-left: 6px;
  color: #98a2b3;
  font-size: 10px;
  border-right: 1px solid #eef1f5;
  overflow: hidden;
  white-space: nowrap;
}
.day-rows { flex: 1; min-height: 0; overflow-y: auto; }
.day-row {
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  border-bottom: 1px solid #eef1f5;
}
.day-member {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  padding: 6px 10px;
  border-right: 1px solid #e8edf3;
  background: #fbfcfe;
}
.day-member .member-dot { width: 8px; height: 8px; margin-bottom: 1px; }
.day-member-name { overflow: hidden; color: #344054; font-size: 12px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.day-member-role { overflow: hidden; color: #98a2b3; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.member-time-cell { position: relative; min-width: 0; border-left: 1px solid #f3f5f8; cursor: crosshair; }
.member-time-cell:hover .day-hover-add { opacity: 1; }
.member-time-cell .hour-lines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to right, transparent calc(100% - 1px), #e8edf3 calc(100% - 1px)),
    linear-gradient(to right, transparent calc(100% - 1px), #f3f5f8 calc(100% - 1px));
  background-size: calc(100% / 13) 100%, calc(100% / 26) 100%;
}
.day-hover-add {
  position: absolute;
  inset: 4px 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  background: rgba(64, 158, 255, 0.07);
  border: 1px dashed rgba(64, 158, 255, 0.4);
  border-radius: 6px;
  opacity: 0;
  pointer-events: none;
}

/* ---------- 周视图 / 工作周 ---------- */
.week-calendar { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.week-header {
  flex: none;
  display: grid;
  min-height: 42px;
  border-bottom: 1px solid #e8edf3;
  background: #fbfcfe;
}
.time-head {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #98a2b3;
  font-size: 11px;
  border-right: 1px solid #e8edf3;
}
.day-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: #475467;
  font-size: 12px;
  border-right: 1px solid #eef1f5;
}
.day-head span { color: #98a2b3; font-size: 11px; }
.day-head.is-weekend { background: #fafbfd; }
.day-head.today { color: #1677d2; background: #f0f7ff; }
.week-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-auto-rows: 1fr;
  overflow: hidden;
}
.time-axis {
  position: relative;
  min-height: 0;
  border-right: 1px solid #e8edf3;
  background: #fbfcfe;
}
.axis-slot {
  position: absolute;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 7px;
  color: #98a2b3;
  font-size: 10px;
}
.day-column {
  position: relative;
  min-width: 0;
  min-height: 0;
  border-right: 1px solid #eef1f5;
  cursor: crosshair;
}
.day-column.is-weekend { background: #fbfcfd; }
.day-column .hour-lines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to bottom, transparent calc(100% - 1px), #e8edf3 calc(100% - 1px)),
    linear-gradient(to bottom, transparent calc(100% - 1px), #f2f4f7 calc(100% - 1px));
  background-size: 100% calc(100% / 13), 100% calc(100% / 26);
}

/* ---------- 日程卡片 ---------- */
.schedule-card {
  position: absolute;
  z-index: 2;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 3px 4px;
  border: 1px solid;
  border-radius: 5px;
  box-shadow: 0 1px 4px rgba(16, 24, 40, 0.08);
  overflow: hidden;
  cursor: grab;
}
.schedule-card:hover {
  z-index: 6;
  box-shadow: 0 6px 14px rgba(16, 24, 40, 0.14);
}
.schedule-card.conflict { outline: 1px dashed #f56c6c; }
.card-drag-area { flex: 1; min-width: 0; min-height: 0; overflow: hidden; }
.card-member,
.card-title,
.card-meta { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-member { display: flex; align-items: center; gap: 3px; font-size: 10px; font-weight: 700; }
.member-dot { width: 6px; height: 6px; flex: none; border-radius: 50%; }
.card-participants {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  flex: none;
  overflow: hidden;
}
.p-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
  color: #344054;
  font-size: 9px;
  font-weight: 600;
}
.p-chip .member-dot { width: 5px; height: 5px; }
.p-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-title { margin-top: 1px; color: #1d2939; font-size: 11px; font-weight: 700; }
.card-meta { margin-top: 1px; color: #667085; font-size: 9px; }
.card-location { display: flex; align-items: center; gap: 2px; }
.day-schedule-card { padding: 4px 6px; }
.day-schedule-card .card-title { font-size: 12px; }
.day-schedule-card .card-meta { font-size: 10px; }
.day-schedule-card .card-location { display: none; }
.resize-handle { position: absolute; left: 0; right: 0; height: 6px; cursor: ns-resize; }
.resize-handle.top { top: 0; }
.resize-handle.bottom { bottom: 0; }
.conflict-badge {
  position: absolute;
  z-index: 3;
  top: 0;
  right: 0;
  width: 15px;
  height: 15px;
  color: #fff;
  background: #f56c6c;
  border-bottom-left-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  text-align: center;
  line-height: 15px;
}
.card-actions {
  position: absolute;
  right: 1px;
  bottom: 1px;
  display: none;
  align-items: center;
  padding: 0 1px;
  background: rgba(255, 255, 255, 0.86);
  border-radius: 4px;
}
.card-actions .el-button { width: 16px; height: 16px; padding: 0; }
.card-actions .el-icon { font-size: 11px; }
.schedule-card:hover .card-actions { display: flex; }

/* ---------- 月视图 ---------- */
.month-grid {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  grid-auto-rows: minmax(94px, auto);
  border-top: 1px solid #e8edf3;
  border-left: 1px solid #e8edf3;
}
.month-cell {
  position: relative;
  min-width: 0;
  padding: 4px 5px 6px;
  border-right: 1px solid #eef1f5;
  border-bottom: 1px solid #eef1f5;
  overflow: hidden;
}
.month-cell.is-pad { background: #fafbfc; }
.month-cell.is-weekend:not(.is-pad) { background: #fbfcfd; }
.month-cell.today { background: #f5faff; }
.month-day {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 18px;
  margin-bottom: 2px;
  color: #475467;
  font-size: 12px;
}
.month-cell.is-weekend .month-day { color: #c45656; }
.month-selected-dot { width: 6px; height: 6px; border-radius: 50%; background: #409eff; }
.month-chip {
  position: relative;
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  margin: 2px 0;
  padding: 2px 3px;
  border: 0;
  border-left: 3px solid transparent;
  border-radius: 4px;
  font-size: 11px;
  text-align: left;
  overflow: hidden;
  cursor: pointer;
}
.month-chip.conflict { box-shadow: inset 0 0 0 1px rgba(245, 108, 108, 0.7); }
.month-chip .chip-dot { width: 6px; height: 6px; flex: none; border-radius: 50%; }
.month-chip .chip-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-actions {
  display: none;
  align-items: center;
  gap: 2px;
  flex: none;
  color: #667085;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 3px;
}
.month-chip:hover .chip-actions { display: flex; }
.chip-actions .el-icon { cursor: pointer; }
.chip-actions .el-icon:hover { color: #409eff; }
.month-more {
  display: inline-flex;
  margin: 2px 2px 0;
  color: #909399;
  font-size: 11px;
  cursor: pointer;
}
.month-more:hover { color: #409eff; }

/* ---------- 右键菜单 ---------- */
.context-menu {
  position: fixed;
  z-index: 3000;
  width: 148px;
  padding: 5px;
  background: #fff;
  border: 1px solid #d0d5dd;
  border-radius: 7px;
  box-shadow: 0 10px 24px rgba(16, 24, 40, 0.16);
}
.context-menu button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #344054;
  cursor: pointer;
  font-size: 12px;
  text-align: left;
}
.context-menu button:hover { background: #f2f4f7; }
</style>

<style>
.timeline-popper { max-width: 320px; }
</style>
