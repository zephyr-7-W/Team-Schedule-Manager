<template>
  <div class="member-panel">
    <div class="member-head">
      <span>团队成员</span>
      <span class="member-head-right">
        <span class="member-count">{{ checkedIds.length }} / {{ members.length }} 人</span>
        <el-tooltip content="新增团队成员" placement="top">
          <el-button circle size="small" type="primary" plain @click="emit('add-member')">
            <el-icon><Plus /></el-icon>
          </el-button>
        </el-tooltip>
      </span>
    </div>

    <div class="member-tools">
      <el-button link type="primary" size="small" @click="emit('check-all')">全选</el-button>
      <el-button link type="info" size="small" @click="emit('clear-check')">清空</el-button>
      <el-button link type="info" size="small" @click="emit('select', null)">全员视图</el-button>
    </div>

    <div class="member-scroll">
      <section v-for="group in groupedMembers" :key="group.name" class="member-group">
        <div class="group-title">
          <span>{{ group.name }}</span>
          <span>{{ group.items.length }}</span>
        </div>
        <div
          v-for="member in group.items"
          :key="member.id"
          class="member-row"
          :class="{ active: member.id === selectedId, unchecked: !checkedIds.includes(member.id) }"
          @click="toggleSelect(member)"
        >
          <el-checkbox
            :model-value="checkedIds.includes(member.id)"
            @click.stop
            @change="emit('toggle-check', member.id)"
          />
          <el-avatar :size="30" :style="{ backgroundColor: member.color }">
            {{ member.name.charAt(0) }}
          </el-avatar>
          <div class="member-info">
            <div class="member-name">
              <span>{{ member.name }}</span>
              <el-tooltip :content="statusText(member)" placement="top">
                <span class="status-dot" :class="busyIds.has(member.id) ? 'busy' : 'free'"></span>
              </el-tooltip>
            </div>
            <div class="member-role">{{ member.role || '成员' }}</div>
          </div>
          <el-tooltip content="分享该成员当前日期的日程" placement="left">
            <el-button
              class="share-btn"
              circle
              size="small"
              type="primary"
              plain
              @click.stop="openShare(member)"
            >
              <el-icon><Share /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip v-if="isAdmin" content="删除成员及其日程" placement="left">
            <el-button class="delete-btn" circle size="small" type="danger" plain @click.stop="emit('delete-member', member)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </section>
    </div>

    <el-dialog
      v-model="shareVisible"
      :title="sharing ? '分享日程：' + sharing.name : '分享日程'"
      width="480px"
    >
      <el-form label-width="80px">
        <el-form-item label="日程日期">
          <span>{{ activeDate }}</span>
        </el-form-item>
        <el-form-item label="分享渠道">
          <el-radio-group v-model="channel">
            <el-radio value="internal">内部文本</el-radio>
            <el-radio value="feishu">飞书（占位）</el-radio>
            <el-radio value="dingtalk">钉钉（占位）</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template v-if="result">
        <el-divider content-position="left">分享内容</el-divider>
        <pre class="share-content">{{ result.content }}</pre>
        <el-alert
          :title="result.message"
          :type="result.payload?.delivered ? 'success' : 'warning'"
          :closable="false"
        />
      </template>

      <template #footer>
        <el-button @click="shareVisible = false">关闭</el-button>
        <el-button v-if="result" @click="copyResult">复制内容</el-button>
        <el-button type="primary" :loading="busy" @click="doShare">
          {{ result ? '重新生成' : '生成并分享' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { shareMemberDay } from '../api/users'
import type { Member, Schedule, ShareResult } from '../types'

const props = defineProps<{
  members: Member[]
  selectedId: number | null
  activeDate: string
  checkedIds: number[]
  schedules: Schedule[]
  isAdmin: boolean
}>()

const emit = defineEmits<{
  (e: 'select', memberId: number | null): void
  (e: 'toggle-check', memberId: number): void
  (e: 'check-all'): void
  (e: 'clear-check'): void
  (e: 'add-member'): void
  (e: 'delete-member', member: Member): void
}>()

const sharing = ref<Member | null>(null)
const shareVisible = ref(false)
const channel = ref('internal')
const busy = ref(false)
const result = ref<ShareResult | null>(null)

const busyIds = computed(() => new Set(props.schedules.map((item) => item.user_id)))

const groupedMembers = computed(() => {
  const order = ['产品组', '前端', '后端', '测试', '算法', '其他']
  const groups = new Map<string, Member[]>()
  for (const member of props.members) {
    const name = groupOf(member)
    groups.set(name, [...(groups.get(name) ?? []), member])
  }
  return order
    .filter((name) => groups.has(name))
    .map((name) => ({ name, items: groups.get(name) ?? [] }))
})

function groupOf(member: Member) {
  const text = member.group || member.role || ''
  if (text.includes('产品') || text.includes('设计')) return '产品组'
  if (text.includes('前端')) return '前端'
  if (text.includes('后端')) return '后端'
  if (text.includes('测试')) return '测试'
  if (text.includes('算法')) return '算法'
  return '其他'
}

function statusText(member: Member) {
  return busyIds.value.has(member.id) ? '忙碌：今日已有日程' : '空闲：今日暂无日程'
}

function toggleSelect(member: Member) {
  emit('select', props.selectedId === member.id ? null : member.id)
}

function openShare(member: Member) {
  sharing.value = member
  result.value = null
  channel.value = 'internal'
  shareVisible.value = true
}

async function doShare() {
  if (!sharing.value) return
  busy.value = true
  try {
    result.value = await shareMemberDay(sharing.value.id, props.activeDate, channel.value)
    ElMessage.success(result.value.message)
  } finally {
    busy.value = false
  }
}

async function copyResult() {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(result.value.content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择文本复制')
  }
}
</script>

<style scoped>
.member-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: #fff;
  border-radius: 8px;
  padding: 10px;
}

.member-head,
.member-head-right,
.member-tools,
.group-title,
.member-row,
.member-name {
  display: flex;
  align-items: center;
}

.member-head {
  justify-content: space-between;
  font-weight: 600;
  font-size: 14px;
  padding: 0 2px 4px;
}

.member-head-right {
  gap: 6px;
}

.member-tools {
  gap: 10px;
  padding: 0 2px 6px;
}

.member-count,
.group-title {
  color: #909399;
  font-size: 12px;
  font-weight: 400;
}

.member-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.member-group + .member-group {
  margin-top: 8px;
}

.group-title {
  justify-content: space-between;
  padding: 5px 4px;
}

.member-row {
  gap: 8px;
  padding: 7px 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
}

.member-row:hover {
  background: #f5f7fa;
}

.member-row.active {
  background: #ecf5ff;
}

.member-row.unchecked {
  opacity: 0.55;
}

.member-info {
  flex: 1;
  min-width: 0;
}

.member-name {
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.free {
  background: #67c23a;
}

.status-dot.busy {
  background: #e6a23c;
}

.member-role {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.share-btn {
  flex: none;
}

.delete-btn {
  flex: none;
}

.share-content {
  margin: 0 0 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
