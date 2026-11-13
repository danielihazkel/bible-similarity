/// <reference types="node" />
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { describe, expect, it } from 'vitest'

// The scales of M176 (DESIGN.md §11): a rule takes a step of a scale, never a length of its own.
// Read from the stylesheets themselves, so a new rule that writes `font-size: 0.82rem` fails here.

const SRC = join(process.cwd(), 'src')

/** The files under `dir` whose name fits, as [path under `dir`, text]. */
function sources(dir: string, fits: RegExp, base = dir): (readonly [string, string])[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const path = join(dir, e.name)
    if (e.isDirectory()) return sources(path, fits, base)
    return fits.test(e.name) ? [[relative(base, path).split(sep).join('/'), readFileSync(path, 'utf8')] as const] : []
  })
}

const SHEETS = sources(join(SRC, 'styles'), /\.css$/)
const MODULES = [...sources(join(SRC, 'pages'), /(?<!\.test)\.tsx$/, SRC), ...sources(join(SRC, 'components'), /(?<!\.test)\.tsx$/, SRC)]

/** Every declaration of every stylesheet as [file, property, value], comments and the tokens' own block left out. */
function declarations(): [string, string, string][] {
  const out: [string, string, string][] = []
  for (const [name, sheet] of SHEETS) {
    let css = sheet.replace(/\/\*[\s\S]*?\*\//g, '')
    // the tokens are defined in global.css's first rule
    if (name === 'global.css') css = css.slice(css.indexOf('}', css.indexOf(':root {')) + 1)
    for (const m of css.matchAll(/(?<![\w-])([a-z-]+)\s*:\s*([^;{}]+?)\s*(?=[;}])/g)) out.push([name, m[1], m[2].replace(/\s*!important$/, '')])
  }
  return out
}

const all = declarations()
const faults = (keep: (prop: string, value: string) => boolean) => all.filter(([, p, v]) => keep(p, v)).map(([f, p, v]) => `${f}: ${p}: ${v}`)
const SPACING = /^(padding|margin)(-(top|bottom|left|right|block|inline)(-(start|end))?)?$|^(row-|column-)?gap$/
const NEGATED = /calc\(-1 \* var\(--space-\d+\)\)/g

describe('the scales of the stylesheets (M176)', () => {
  it('finds the stylesheets and the modules', () => {
    expect(SHEETS.length).toBeGreaterThan(100)
    expect(all.length).toBeGreaterThan(3000)
    expect(MODULES.length).toBeGreaterThan(100)
  })

  it('every font size is a step of the type scale', () => {
    expect(faults((p, v) => p === 'font-size' && !/^(var\(--fs-[a-z0-9-]+\)|inherit)$/.test(v))).toEqual([])
  })

  it('every corner is a step of the radii', () => {
    const part = /^(0|inherit|var\(--radius(-sm|-lg|-pill|-round)?\))$/
    expect(faults((p, v) => /radius$/.test(p) && !v.split(/\s+/).every((x) => part.test(x)))).toEqual([])
  })

  it('a shadow that lifts a box is a token: a rule writes no colour into a shadow', () => {
    // a ring or an inset line in a colour token is a mark, not a shadow
    expect(faults((p, v) => p === 'box-shadow' && /#[0-9a-f]{3,8}\b|(?<![a-z])rgba?\(|hsla?\(/i.test(v))).toEqual([])
  })

  it('padding, margin and gap are steps of the spacing scale (a hairline of 1px to 3px is written as it is)', () => {
    const fine = (v: string) =>
      v
        .replace(NEGATED, '0')
        .replace(/var\(--space-\d+\)/g, '0')
        .split(/\s+/)
        .every((x) => /^(0|auto|inherit|-?[123]px|-?[\d.]+(em|%|vh|vw))$/.test(x))
    // min(), max() and calc() around a width are layout, not a step
    expect(faults((p, v) => SPACING.test(p) && !/\b(min|max|clamp|calc)\(/.test(v.replace(NEGATED, '')) && !fine(v))).toEqual([])
  })

  it('two breakpoints: 720px (a phone) and 900px (the top bar folds), and the bar’s own widths above them', () => {
    const widths = new Set<string>()
    for (const [, css] of SHEETS) {
      for (const m of css.matchAll(/@media[^{]*/g)) for (const w of m[0].matchAll(/(max|min)-width:\s*(\d+)px/g)) widths.add(`${w[1]} ${w[2]}`)
    }
    // 1139 / 1219 / 1339: where the bar's one row no longer fits, per language (M168, M169)
    expect([...widths].sort()).toEqual(['max 1139', 'max 1219', 'max 1339', 'max 720', 'max 900', 'min 901'])
  })

  it('a page’s module writes no colour of its own: chart colours are tokens (lib/palette.ts)', () => {
    const found = MODULES.flatMap(([name, code]) => [...code.matchAll(/#[0-9a-f]{6}\b|hsla?\(/gi)].map((m) => `${name}: ${m[0]}`))
    expect(found).toEqual([])
  })

  it('each palette token has a dark value', () => {
    const css = SHEETS.find(([name]) => name === 'global.css')![1]
    const light = css.slice(css.indexOf(':root {'), css.indexOf("[data-theme='dark']"))
    const dark = css.slice(css.indexOf("[data-theme='dark']"), css.indexOf('color-scheme: dark'))
    const names = [...light.matchAll(/(--(?:sec|cl|dist|seq)-[a-z0-9]+):/g)].map((m) => m[1])
    expect(names.length).toBe(3 + 12 + 12 + 2)
    expect(names.filter((n) => !dark.includes(`${n}:`))).toEqual([])
  })
})
