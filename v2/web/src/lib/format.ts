// Format angka gaya Indonesia: titik ribuan, koma desimal.
const cache = new Map<number, Intl.NumberFormat>()

export function num(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–'
  let f = cache.get(digits)
  if (!f) {
    f = new Intl.NumberFormat('id-ID', { minimumFractionDigits: digits, maximumFractionDigits: digits })
    cache.set(digits, f)
  }
  return f.format(value)
}

export function pct(ratio: number, digits = 0): string {
  return `${num(ratio * 100, digits)} %`
}

/** Mengubah teks input "1.234,5" menjadi angka. */
export function parseNum(text: string): number | null {
  const clean = text.replace(/\s/g, '').replace(/\./g, '').replace(',', '.')
  if (clean === '' || clean === '-') return null
  const v = Number(clean)
  return Number.isFinite(v) ? v : null
}
