// Tahap 2–3: kasus dibaca langsung dari file JSON (belum ada API). Lihat SPEC §9.1.
import type { Case } from '../api/case'
import k15Json from '../../../cases/k15-batam.json'

export const K15: Case = k15Json as unknown as Case

export interface CaseListItem {
  id: string
  name: string
  location: string
  status: 'siap' | 'belum diekstrak'
  data?: Case
}

export const CASES: CaseListItem[] = [
  { id: 'k15-batam', name: 'K15 · KI Batam', location: 'Batam, Kep. Riau', status: 'siap', data: K15 },
  { id: 'k21-gresik', name: 'K21 · Gresik', location: 'Gresik, Jawa Timur', status: 'belum diekstrak' },
  { id: 'k24-palu', name: 'K24 · Palu', location: 'Palu, Sulawesi Tengah', status: 'belum diekstrak' },
]
