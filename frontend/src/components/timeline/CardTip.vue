<template>
  <div class="card-tip">
    <div class="ctp-head">
      <i class="ctp-dot" :style="{ background: color }"></i>
      <span class="ctp-member">{{ memberName }}</span>
      <span v-if="role" class="ctp-role">{{ role }}</span>
    </div>
    <div class="ctp-title">{{ item.title }}</div>
    <div class="ctp-row">{{ item.date }} {{ shortTime(item.start_time) }} - {{ shortTime(item.end_time) }}</div>
    <div v-if="item.location" class="ctp-row">地点：{{ item.location }}</div>
    <div v-if="item.note" class="ctp-row ctp-note">备注：{{ item.note }}</div>
    <div v-for="conflict in conflicts" :key="conflict.id" class="ctp-row ctp-conflict">
      ⚠ 与 {{ conflict.user?.name || '成员' }}《{{ conflict.title }}》({{ shortTime(conflict.start_time) }}) 冲突
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Member, Schedule } from '../../types'
import { shortTime } from '../../utils/date'

const props = defineProps<{
  item: Schedule
  members: Member[]
  conflicts?: Schedule[]
}>()

const member = computed(() => props.members.find((item) => item.id === props.item.user_id))
const color = computed(() => member.value?.color || props.item.user?.color || '#5470c6')
const memberName = computed(() => member.value?.name || props.item.user?.name || '成员')
const role = computed(() => member.value?.role || props.item.user?.role || '')
</script>

<style scoped>
.card-tip {
  min-width: 170px;
  max-width: 280px;
  font-size: 12px;
  line-height: 1.55;
}
.ctp-head {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 3px;
}
.ctp-dot {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 50%;
}
.ctp-member {
  font-weight: 700;
  color: #303133;
}
.ctp-role {
  color: #909399;
  font-size: 11px;
}
.ctp-title {
  margin: 2px 0;
  color: #1d2939;
  font-weight: 700;
}
.ctp-row {
  color: #667085;
  word-break: break-all;
}
.ctp-note {
  color: #4b5563;
}
.ctp-conflict {
  color: #d4380d;
  font-weight: 600;
}
</style>
