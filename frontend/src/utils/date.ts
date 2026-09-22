export const HOUR_START = 8
export const HOUR_END = 21
export const HOUR_WIDTH = 144
export const LABEL_WIDTH = 132
export const ROW_HEIGHT = 64
export const SCALE_WIDTH = (HOUR_END - HOUR_START) * HOUR_WIDTH

export function pad2(value: number): string {
  return value.toString().padStart(2, '0')
}

export function dateToKey(year: number, month: number, day: number): string {
  return year + '-' + pad2(month) + '-' + pad2(day)
}

export function formatDate(value: Date): string {
  return dateToKey(value.getFullYear(), value.getMonth() + 1, value.getDate())
}

export function todayStr(): string {
  return formatDate(new Date())
}

export function addDays(dateStr: string, offset: number): string {
  const parts = dateStr.split('-').map(Number)
  const base = new Date(parts[0], parts[1] - 1, parts[2])
  base.setDate(base.getDate() + offset)
  return formatDate(base)
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

export function parseHM(value: string): number {
  const parts = value.split(':').map(Number)
  return parts[0] * 60 + parts[1]
}

export function toHM(minutes: number): string {
  const clamped = Math.max(0, Math.min(23 * 60 + 59, minutes))
  return pad2(Math.floor(clamped / 60)) + ':' + pad2(clamped % 60)
}

export function shortTime(value: string): string {
  return value ? value.slice(0, 5) : ''
}

/** 时间轴内：HH:MM -> 像素偏移 */
export function timeToPx(value: string): number {
  return ((parseHM(value) - HOUR_START * 60) / 60) * HOUR_WIDTH
}

export function startOfWeek(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number)
  const value = new Date(year, month - 1, day)
  value.setDate(value.getDate() - ((value.getDay() + 6) % 7))
  return formatDate(value)
}
