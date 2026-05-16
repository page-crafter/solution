import { describe, expect, it } from 'vitest'
import { router } from './index'

describe('router easter eggs', () => {
  it('exposes the secret archive through /secret and /coffee', () => {
    const secret = router.resolve('/secret')
    const coffee = router.resolve('/coffee')

    expect(secret.matched.at(-1)?.path).toBe('/secret')
    expect(secret.matched.at(-1)?.meta.requiresAdmin).toBe(true)
    expect(coffee.matched.at(-1)?.meta.requiresAdmin).toBe(true)
  })
})
