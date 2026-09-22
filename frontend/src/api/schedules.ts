import type { Schedule, SchedulePayload, ShareResult } from '../types'
import { apiDelete, apiGet, apiPost, apiPut } from './http'

export function listDailySchedules(date: string, userId?: number | null) {
  const params: Record<string, string> = { date }
  if (userId) {
    params.user_id = String(userId)
  }
  return apiGet<Schedule[]>('/schedules', params)
}

export function createSchedule(payload: SchedulePayload): Promise<Schedule> {
  return apiPost<Schedule>('/schedules', payload)
}

export function updateSchedule(
  id: number,
  payload: Partial<SchedulePayload>,
): Promise<Schedule> {
  return apiPut<Schedule>('/schedules/' + id, payload)
}

export function deleteSchedule(id: number): Promise<{ ok: boolean }> {
  return apiDelete<{ ok: boolean }>('/schedules/' + id)
}

export function shareSingleSchedule(
  id: number,
  channel: string,
): Promise<ShareResult> {
  return apiPost<ShareResult>('/schedules/' + id + '/share', { channel })
}
