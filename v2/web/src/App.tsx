import type { ComponentType } from 'react'
import { Sidebar, TopBar, TraceDrawer } from './components/shell'
import { usePlanner } from './store'
import S00Beranda from './screens/S00Beranda'
import S01Soal from './screens/S01Soal'
import S02Tenant from './screens/S02Tenant'
import S03Pelabuhan from './screens/S03Pelabuhan'
import S04Kapal from './screens/S04Kapal'
import S05Alat from './screens/S05Alat'
import S06Armada from './screens/S06Armada'
import S07Biaya from './screens/S07Biaya'
import S08Terminal from './screens/S08Terminal'
import S09Investasi from './screens/S09Investasi'
import S10Optimasi from './screens/S10Optimasi'
import S11Skenario from './screens/S11Skenario'

const SCREENS: ComponentType[] = [
  S00Beranda, S01Soal, S02Tenant, S03Pelabuhan, S04Kapal, S05Alat,
  S06Armada, S07Biaya, S08Terminal, S09Investasi, S10Optimasi, S11Skenario,
]

export default function App() {
  const screen = usePlanner((s) => s.screen)
  const Screen = SCREENS[screen]
  return (
    <div className="min-h-screen bg-white">
      <TopBar />
      <div className="flex">
        <Sidebar />
        <main className="min-w-0 grow">
          <div className="mx-auto flex max-w-[960px] flex-col gap-8 px-8 pt-8 pb-12">
            <Screen />
          </div>
        </main>
        <TraceDrawer />
      </div>
    </div>
  )
}
