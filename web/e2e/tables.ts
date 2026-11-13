import type { Page } from '@playwright/test'

// The table rules of M175 (DESIGN.md §11), checked in the page by both suites.

/**
 * One line per fault of the tables on screen:
 * - every table is a `.data-table` in a `.table-wrap`;
 * - a column whose cells are all numbers is at the end of its cells and of its heading (the
 *   first column, the row's name, and a column of drawn bars are left as they are), and a
 *   heading is on the side its cells are;
 * - a heading that is a statistic of the glossary (p, q, G², ρ …) opens its entry.
 * English interface: the headings are read by their text.
 */
export function tableFaults(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const numeric = (t: string) => /\d/.test(t) && /^[\s(<>≤≥~×+\-−–✓✗✔✘]*[\d.]/.test(t) && t.replace(/[^\p{L}]/gu, '').length <= 3
    const rtl = document.documentElement.dir === 'rtl'
    const atEnd = (el: Element) => {
      const a = getComputedStyle(el).textAlign
      return a === 'end' || a === (rtl ? 'left' : 'right')
    }
    const faults: string[] = []
    for (const table of document.querySelectorAll<HTMLTableElement>('main table')) {
      const name = table.className.replace('data-table', '').trim() || 'table'
      if (!table.classList.contains('data-table')) faults.push(`${name}: not a data-table`)
      if (!table.parentElement?.classList.contains('table-wrap')) faults.push(`${name}: not in a table-wrap`)
      const head = table.tHead?.rows[table.tHead.rows.length - 1]
      if (!head) continue
      const ncol = [...head.cells].reduce((n, c) => n + c.colSpan, 0)
      const rows = [...table.tBodies].flatMap((b) => [...b.rows]).filter((r) => r.cells.length === ncol && [...r.cells].every((c) => c.colSpan === 1))
      ;[...head.cells].forEach((th, c) => {
        const text = th.innerText.trim().replace(/\s+/g, ' ')
        if (/^(p|q|G²|ρ|AUC|Kappa|MRR)( |$)/.test(text) && !th.querySelector('.term-button')) faults.push(`${name}: the heading "${text}" does not open its glossary entry`)
        if (head.cells.length !== ncol || c === 0) return
        const cells = rows.map((r) => r.cells[c])
        const texts = cells.map((x) => x.innerText.trim()).filter((t) => t && !/^[–—-]$/.test(t))
        if (texts.length === 0) return
        const numbers = texts.every(numeric) && !cells.some((x) => x.querySelector('[class*="bar"]'))
        const cellsEnd = cells.every(atEnd)
        if (numbers && !cellsEnd) faults.push(`${name}: the numbers of "${text}" (${texts[0]}) are not at the end`)
        else if (cellsEnd !== atEnd(th)) faults.push(`${name}: the heading "${text}" is not on the side of its cells`)
      })
    }
    return faults
  })
}

/**
 * Each table that fits its wrapper and can be scrolled past its headings: how far (px) the
 * headings then sit from the bottom of the top bar. 0 where they stick.
 */
export function stickyOffsets(page: Page): Promise<number[]> {
  return page.evaluate(() => {
    const out: number[] = []
    for (const table of document.querySelectorAll<HTMLTableElement>('main table.data-table')) {
      const head = table.tHead?.rows[0]
      if (!head || !table.parentElement?.classList.contains('fits')) continue
      const bar = document.querySelector('.topbar')!.getBoundingClientRect().bottom
      const r = table.getBoundingClientRect()
      const h = head.getBoundingClientRect().height
      if (r.height < 2 * h + 40) continue
      // the table's top a heading and a bit above the bar's bottom
      const to = window.scrollY + r.top - bar + h + 20
      if (to > document.documentElement.scrollHeight - window.innerHeight) continue
      window.scrollTo({ top: to, behavior: 'instant' })
      out.push(Math.round(head.cells[0].getBoundingClientRect().top - document.querySelector('.topbar')!.getBoundingClientRect().bottom))
    }
    return out
  })
}
