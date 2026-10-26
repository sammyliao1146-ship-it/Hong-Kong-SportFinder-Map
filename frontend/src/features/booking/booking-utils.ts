import type { BookingSlot } from '../../api/client';
// Sum court-sessions, not unique courts. Preserve unknown values in every aggregate.
export function sumSlots(slots: BookingSlot[]): number | null {
  return !slots.length || slots.some(s => s.remaining === null) ? null : slots.reduce((n, s) => n + s.remaining!, 0);
}
export function periodCounts(slots: BookingSlot[], date: string) {
  return [0, 1, 2].map(period => sumSlots(slots.filter(s => s.date === date && (Number(s.start.slice(0, 2)) < 12 ? 0 : Number(s.start.slice(0, 2)) < 18 ? 1 : 2) === period)));
}
export function countClass(n: number | null) { return n === null ? 'unknown' : n === 0 ? 'empty' : n < 3 ? 'limited' : 'plenty'; }
export const displayCount = (n: number | null) => n === null ? '?' : String(n);
