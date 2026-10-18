import { describe, expect, it } from 'vitest'

import { ApiError, isConflict } from './client'

describe('isConflict', () => {
  it('reconhece só conflito de versão, não id duplicado', () => {
    expect(isConflict(new ApiError(409, 'version_conflict', 'x'))).toBe(true)
    expect(isConflict(new ApiError(409, 'duplicate_id_conflict', 'x'))).toBe(false)
  })
})
