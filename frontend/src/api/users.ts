import type { Member, Schedule, ShareResult } from '../types'
import { apiDelete, apiGet, apiPost } from './http'

export function listMembers(): Promise<Member[]> {
  return apiGet<Member[]>('/users')
}

export function createMember(payload: Pick<Member, 'name' | 'role' | 'color'>): Promise<Member> {
  return apiPost<Member>('/users', payload)
}

export function deleteMember(userId: number): Promise<{ ok: boolean }> {
  return apiDelete<{ ok: boolean }>('/users/' + userId)
}

export function listUserSchedules(
  userId: number,
  date?: string,
): Promise<Schedule[]> {
  return apiGet<Schedule[]>(
    '/users/' + userId + '/schedules',
    date ? { date } : undefined,
  )
}

export function shareMemberDay(
  userId: number,
  date: string,
  channel: string,
): Promise<ShareResult> {
  return apiPost<ShareResult>(
    '/users/' + userId + '/schedules/share',
    { date, channel },
  )
}
