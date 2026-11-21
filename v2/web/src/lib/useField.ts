import { usePlanner } from '../store'

type Path = (string | number)[]

function getAt(obj: unknown, path: Path): unknown {
  let cur = obj
  for (const p of path) cur = (cur as Record<string | number, unknown> | undefined)?.[p]
  return cur
}

/** Ikatan satu input kasus ke store: nilai, status diubah, dan setter. */
export function useField(path: Path, label: string) {
  const key = path.join('.')
  const value = usePlanner((s) => getAt(s.caseData, path)) as number
  const changed = usePlanner((s) => key in s.dirty)
  const setInput = usePlanner((s) => s.setInput)
  return { value, changed, label, onChange: (v: number) => setInput(path, v, label) }
}
