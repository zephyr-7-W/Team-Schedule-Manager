import type { AiParseResult } from '../types'
import { apiPost } from './http'

export function aiParseSchedule(text: string): Promise<AiParseResult> {
  return apiPost<AiParseResult>('/ai/parse', { text })
}
