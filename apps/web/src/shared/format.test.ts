import { describe, expect, it } from 'vitest'

import { addDays, mondayOf } from './format'

describe('datas civis', () => {
  it('calcula a segunda-feira sem depender do fuso do navegador', () => {
    expect(mondayOf('2026-10-09')).toBe('2026-10-05')
    expect(mondayOf('2026-10-12')).toBe('2026-10-12')
    expect(mondayOf('2026-10-11')).toBe('2026-10-05')
  })
  it('soma dias atravessando o mês', () => {
    expect(addDays('2026-10-30', 3)).toBe('2026-11-02')
  })
})
