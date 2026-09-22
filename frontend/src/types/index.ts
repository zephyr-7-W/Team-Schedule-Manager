export interface Member {
  id: number
  name: string
  role: string
  color: string
  group?: string
}

export interface Schedule {
  id: number
  user_id: number
  title: string
  date: string
  start_time: string
  end_time: string
  location: string
  note: string
  source: string
  category?: ScheduleCategory
  recurrence?: RecurrenceRule
  participants?: number[]
  reminder?: number
  user: Member
}

export type ScheduleCategory = '会议' | '开发' | '评审' | '复盘' | '其他'
export type RecurrenceRule = 'none' | 'daily' | 'weekdays' | 'weekly'

export interface SchedulePayload {
  user_id: number
  title: string
  date: string
  start_time: string
  end_time: string
  location?: string
  note?: string
  category?: ScheduleCategory
  recurrence?: RecurrenceRule
  participants?: number[]
  reminder?: number
}

export interface AiCandidate {
  user_id: number | null
  user_name: string
  title: string
  date: string | null
  start_time: string | null
  end_time: string | null
  location: string
  note: string
  source: string
}

export interface AiParseResult {
  schedule: AiCandidate
  conflicts: string[]
  message: string
  source: string
}

export interface SharePayloadInfo {
  ok: boolean
  channel: string
  code: string
  delivered?: boolean
  note?: string
  content?: unknown
}

export interface ShareResult {
  ok: boolean
  channel: string
  message: string
  content: string
  payload: SharePayloadInfo
}
