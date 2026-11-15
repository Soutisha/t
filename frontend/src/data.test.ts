import { describe, expect, it } from 'vitest'
import { activities, mechanics, requests } from './data'

describe('demo fixtures', () => {
  it('contains demo mechanics with unique names', () => {
    expect(mechanics.length).toBeGreaterThan(0)
    expect(new Set(mechanics.map(m => m.name)).size).toBe(mechanics.length)
  })
  it('keeps tool requests separately identifiable', () => {
    expect(requests.every(r => r.id.startsWith('TB-'))).toBe(true)
  })
  it('provides activity labels and timestamps', () => {
    expect(activities.every(a => a.title.length > 0 && a.time.length > 0)).toBe(true)
  })
})
