// /street/3d: the street in 3D for the stage. Kenney suburban houses (the kit's own solar-roof models,
// each turned so its panels face the roof's real direction), the real sun for the sim time (the hub
// sends its position), roofs glowing with live solar, clouds over clouded roofs, power arcing between
// roofs for live deals, guard flags in red, an outage dims the street. A Simulate panel drives the
// demo from here. The 2D dashboard (/) stays the default and the fallback. Every number comes from the hub.
import { Component, memo, type ReactNode, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html, Line, OrbitControls, Sky, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { HaggleChat } from "../components/HaggleChat";
import { Button, Clock, type IconName, Logo, Segmented, toast } from "../components/ui";
import { useHub } from "../hooks/useHub";
import { api, blockKey, rupees } from "../lib/api";
import { HOUSES, type Contract, type House, type HouseInfo } from "../lib/types";
import { type Happening, TONE_CLASS, useHappening } from "../lib/happening";
import { useHubStore } from "../store/hub";

const KIT = "/models/kenney_city-kit-suburban_20/Models/GLB format/";
const model = (name: string) => encodeURI(`${KIT}${name}.glb`);

// Two sides of a street that runs east-west (north = -z). South-side houses front the road to their
// north, so south-facing panels sit on the back slope, away from the road, as on a real street.
const HOUSE_POS: Record<House, [number, number]> = { h12: [-6.5, 5.4], h14: [-2.5, -5.4], h16: [4.5, -5.4], h18: [2, 5.4] };
const ROAD_END = 13;                 // the road ends in a turning circle here (x)

// The kit's houses that come with panels, and which way their panels face in the model (azimuth,
// 0 = the model's -z). Bigger roofs get the model with more panels.
const SOLAR_MODELS: { min_kwp: number; name: string; panel_az: number }[] = [
  { min_kwp: 4, name: "building-type-h", panel_az: 0 },    // three panels
  { min_kwp: 2.5, name: "building-type-b", panel_az: 90 }, // panels on the side wing
  { min_kwp: 0, name: "building-type-j", panel_az: 0 },    // two panels
];
const PLAIN_MODEL: Record<House, string> = { h12: "building-type-a", h14: "building-type-c", h16: "building-type-e", h18: "building-type-k" };
const ALL_MODELS = [...SOLAR_MODELS.map((m) => m.name), ...Object.values(PLAIN_MODEL)];
const FOOTPRINT = 3.4;
const FLAG_MINUTES = 45;           // a guard flag stays red on the street this long (sim minutes)
const QUALITY_KEY = "hizashi.3d.quality";

type Quality = "high" | "low";

function loadQuality(): Quality {
  try { return localStorage.getItem(QUALITY_KEY) === "low" ? "low" : "high"; } catch { return "high"; }
}

// Checked once: every check makes a WebGL context, and browsers drop the oldest (the street) past ~16.
let webgl: boolean | undefined;
function webglOk(): boolean {
  if (webgl === undefined) {
    try {
      const gl = document.createElement("canvas").getContext("webgl2");
      webgl = !!gl;
      gl?.getExtension("WEBGL_lose_context")?.loseContext();
    } catch { webgl = false; }
  }
  return webgl;
}

/** pvlib azimuth (from north, clockwise) + elevation -> unit vector; north = -z, east = +x. */
function sunVector(az: number, el: number): THREE.Vector3 {
  const a = THREE.MathUtils.degToRad(az), e = THREE.MathUtils.degToRad(el);
  return new THREE.Vector3(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e));
}

/** Which model a house gets and how it's turned: panels toward the roof's azimuth, else door to the road. */
function placement(house: House, info?: HouseInfo): { name: string; rotation: number } {
  const roof = info?.roof;
  if (!roof) return { name: PLAIN_MODEL[house], rotation: HOUSE_POS[house][1] > 0 ? Math.PI : 0 };
  const m = SOLAR_MODELS.find((s) => roof.kwp >= s.min_kwp)!;
  return { name: m.name, rotation: -THREE.MathUtils.degToRad(roof.azimuth - m.panel_az) };
}

// --- page ------------------------------------------------------------------------------------------

/** Keeps the snapshot + WebSocket open; renders nothing, so its per-event re-render costs nothing. */
function HubConnection() {
  useHub("street");
  return null;
}

export default function Street3D() {
  const [quality, setQuality] = useState<Quality>(loadQuality);
  const outage = useHubStore((s) => !!s.outage);
  const flags = useHubStore((s) => s.flags);
  const { outageUntil, dayOver } = useHappening();

  const seenFlags = useRef(-1);
  useEffect(() => {
    const fresh = seenFlags.current < 0 ? [] : flags.slice(seenFlags.current);
    seenFlags.current = flags.length;
    for (const f of fresh) toast(`Guard · ${f.title ?? "flag"}`, String(f.text ?? ""), "bad");
  }, [flags]);

  const toggleQuality = () => {
    const q = quality === "high" ? "low" : "high";
    setQuality(q);
    try { localStorage.setItem(QUALITY_KEY, q); } catch { /* private mode */ }
  };

  return (
    <div className="fixed inset-0 bg-[#cfe3f5]">
      <HubConnection />
      <div className={`absolute inset-0 isolate transition-[filter] duration-700 ${outage ? "grayscale-[0.75] brightness-[0.55]" : ""}`}>
        {webglOk() ? (
          <Fallback>
            <Canvas shadows={quality === "high"} dpr={quality === "high" ? [1, 1.5] : 1}
              camera={{ position: [16, 12, 20], fov: 40 }} gl={{ antialias: quality === "high", powerPreference: "high-performance" }}>
              <Suspense fallback={<Html center><p className="whitespace-nowrap text-sm text-ink-2">Building the street…</p></Html>}>
                <Scene quality={quality} />
              </Suspense>
            </Canvas>
          </Fallback>
        ) : <NoWebGL />}
      </div>

      <header className="pointer-events-none absolute inset-x-0 top-0 flex items-center gap-4 p-5">
        <div className="pointer-events-auto flex items-center gap-3 rounded-2xl bg-white/80 px-4 py-2.5 backdrop-blur-xl">
          <Logo />
          <div>
            <p className="text-[17px] font-semibold leading-tight">Hizashi · the street</p>
            <p className="text-xs text-ink-2">Four homes on transformer T1, trading their own sunshine</p>
          </div>
        </div>
        <div className="flex-1" />
        <div className="pointer-events-auto flex items-center gap-2">
          <Clock />
          <Button small icon="sun" onClick={toggleQuality}>{quality === "high" ? "High quality" : "Low quality"}</Button>
          <Link to="/"><Button small kind="tinted" icon="arrow">2D street</Button></Link>
        </div>
      </header>

      {outage && (
        <div className="absolute left-1/2 top-24 -translate-x-1/2 rounded-full bg-alert px-4 py-2 text-sm font-semibold text-white shadow-lg">
          Grid outage{outageUntil ? ` until ${outageUntil}` : ""} · no neighbour trades, no penalties
        </div>
      )}

      {dayOver && <DayOver />}
      <SimPanel />
      <Stats />

      <div className="absolute bottom-5 right-5 w-[360px] rounded-2xl bg-white/85 p-4 backdrop-blur-xl">
        <p className="mb-2 text-[13px] font-semibold">A2A haggle</p>
        <HaggleChat />
      </div>
    </div>
  );
}

function Stats() {
  const contracts = useHubStore((s) => s.contracts);
  const savings = useHubStore((s) => s.savings);
  const shared = contracts.reduce((a, c) => a + c.kwh, 0);
  const saved = HOUSES.reduce((a, h) => a + (savings[h]?.saved_today ?? 0), 0);
  return (
    <div className="pointer-events-none absolute bottom-5 left-5 flex gap-3">
      <Stat value={String(contracts.length)} label="deals today" />
      <Stat value={`${shared.toFixed(1)} kWh`} label="shared between roofs" />
      <Stat value={rupees(saved)} label="saved vs BESCOM" tone="text-leaf-ink" />
    </div>
  );
}

function Stat({ value, label, tone = "" }: { value: string; label: string; tone?: string }) {
  return (
    <div className="rounded-2xl bg-white/85 px-4 py-3 backdrop-blur-xl">
      <p className={`num text-[24px] font-semibold leading-tight tracking-tight ${tone}`}>{value}</p>
      <p className="text-xs text-ink-2">{label}</p>
    </div>
  );
}

// --- simulate panel ------------------------------------------------------------------------------------

const PER_HOUSE: { type: string; label: string; icon: IconName; minutes?: number; solarOnly?: boolean }[] = [
  { type: "cloud", label: "Cloud", icon: "cloud", minutes: 45, solarOnly: true },
  { type: "ac", label: "AC on", icon: "bolt", minutes: 120 },
  { type: "guests", label: "Guests", icon: "people", minutes: 180 },
  { type: "away", label: "Away", icon: "home", minutes: 240 },
];

/** The console's demo controls, on the 3D screen so the stage never leaves it. Every tap goes to the hub. */
function SimPanel() {
  const [open, setOpen] = useState(true);
  const [house, setHouse] = useState<House>("h12");
  const speed = useHubStore((s) => s.speed);
  const houses = useHubStore((s) => s.houses);
  const run = async (what: string, fn: () => Promise<unknown>) => {
    try { await fn(); toast(what, undefined, "ok"); } catch (e) { toast(what, (e as Error).message, "bad"); }
  };
  const name = (h: House) => houses[h]?.label ?? `House ${h.slice(1)}`;

  if (!open) {
    return (
      <div className="absolute left-5 top-24">
        <Button small icon="sliders" onClick={() => setOpen(true)}>Simulate</Button>
      </div>
    );
  }
  return (
    <div className="absolute left-5 top-24 max-h-[calc(100vh-15rem)] w-[300px] overflow-y-auto rounded-2xl bg-white/90 p-4 backdrop-blur-xl">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-[13px] font-semibold">Simulate</p>
        <button onClick={() => setOpen(false)} className="text-[12px] text-ink-2 hover:text-ink">Hide</button>
      </div>

      <Segmented value={speed} onChange={(s) => run(`Speed ${s}×`, () => api.setSpeed(s as 1 | 60 | 300))}
        options={[1, 60, 300].map((s) => ({ value: s, label: `${s}×` }))} />

      <NowList />

      <p className="mb-1.5 mt-4 text-[11px] font-semibold uppercase tracking-wide text-ink-3">One house</p>
      <Segmented value={house} onChange={setHouse} options={HOUSES.map((h) => ({ value: h, label: h.slice(1) }))} />
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        {PER_HOUSE.map((a) => (
          <Button key={a.type} small icon={a.icon} disabled={a.solarOnly && !houses[house]?.roof}
            onClick={() => run(`${a.label} · ${name(house)}`, () => api.consoleEvent(a.type, house, a.minutes))}>
            {a.label}
          </Button>
        ))}
      </div>
      <Button small icon="check" kind="tinted" className="mt-1.5 w-full"
        onClick={() => run(`Asking ${name(house)}'s owner (check the phone)`, () => api.consoleEvent("ask_owner", house))}>
        Ask the owner for a big buy
      </Button>

      <p className="mb-1.5 mt-4 text-[11px] font-semibold uppercase tracking-wide text-ink-3">Whole street</p>
      <div className="grid grid-cols-2 gap-1.5">
        <Button small icon="cloud" onClick={() => run("Cloud over the street", () => api.consoleEvent("cloud", undefined, 45))}>Cloud</Button>
        <Button small icon="plug" onClick={() => run("Grid outage · 30 min", () => api.consoleEvent("outage", undefined, 30))}>Outage</Button>
      </div>

      <p className="mb-1.5 mt-4 text-[11px] font-semibold uppercase tracking-wide text-ink-3">Attack</p>
      <Button small icon="ban" kind="danger" className="w-full"
        onClick={() => run("Impostor “House 16” tries to sell at ₹40", () => api.consoleEvent("impostor"))}>
        Impostor “House 16” sells at ₹40
      </Button>

      <p className="mb-1.5 mt-4 text-[11px] font-semibold uppercase tracking-wide text-ink-3">Day</p>
      <div className="grid grid-cols-2 gap-1.5">
        <Button small icon="reset" onClick={() => run("Day reset", api.reset)}>Reset day</Button>
        <Button small icon="arrow" onClick={() => run("Next day", api.nextDay)}>Next day</Button>
      </div>
    </div>
  );
}

/** What is on right now: every console button shows up here the moment the hub has it. */
function NowList() {
  const { all } = useHappening();
  return (
    <div className="mt-3 rounded-xl bg-fill/60 p-2.5">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-3">Now</p>
      {all.length === 0 ? <p className="mt-1 text-[12px] text-ink-2">Nothing unusual. Normal sun and use.</p> : (
        <ul className="mt-1.5 flex flex-wrap gap-1">
          {all.map((x) => (
            <li key={x.key} className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${TONE_CLASS[x.tone]}`}>
              {x.house ? `${x.house.slice(1)} · ` : "Street · "}{x.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The simulated day ended at 19:00: nothing moves until the next day or a reset. */
function DayOver() {
  const run = async (what: string, fn: () => Promise<unknown>) => {
    try { await fn(); toast(what, undefined, "ok"); } catch (e) { toast(what, (e as Error).message, "bad"); }
  };
  return (
    <div className="absolute left-1/2 top-1/2 z-30 -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white/95 p-5 text-center shadow-xl backdrop-blur-xl">
      <p className="text-[17px] font-semibold">The day is over (19:00)</p>
      <p className="mt-1 text-[13px] text-ink-2">Nothing trades at night. Start a day to try the buttons.</p>
      <div className="mt-4 flex justify-center gap-2">
        <Button small icon="arrow" kind="tinted" onClick={() => run("Next day", api.nextDay)}>Next day</Button>
        <Button small icon="reset" onClick={() => run("Day reset", api.reset)}>Same day again</Button>
      </div>
    </div>
  );
}

function NoWebGL() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <p className="text-lg font-semibold">3D isn't available in this browser</p>
      <Link to="/"><Button kind="tinted" icon="arrow">Open the 2D street</Button></Link>
    </div>
  );
}

/** Any failure inside the 3D scene (WebGL lost, a model missing) shows the way back to 2D. */
class Fallback extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <NoWebGL /> : this.props.children; }
}

// --- scene -------------------------------------------------------------------------------------------

const Scene = memo(function Scene({ quality }: { quality: Quality }) {
  const simTime = useHubStore((s) => s.sim_time);
  const blocks = useHubStore((s) => s.blocks);
  const contracts = useHubStore((s) => s.contracts);
  const flags = useHubStore((s) => s.flags);
  const outage = useHubStore((s) => !!s.outage);
  const { byHouse, impostor } = useHappening();
  const now = simTime ? Date.parse(simTime) : 0;

  const live = useMemo(() => {
    const delivering = Object.entries(blocks).find(([, s]) => s === "DELIVERING")?.[0];
    return delivering ? contracts.filter((c) => blockKey(c.block) === delivering) : [];
  }, [blocks, contracts]);
  const flagged = new Map<string, string>();
  for (const f of flags) {
    if (now - Date.parse(f.ts ?? "") <= FLAG_MINUTES * 60_000) for (const h of f.houses ?? []) flagged.set(h, String(f.title ?? "Guard flag"));
  }
  const [tops, setTops] = useState<Record<string, number>>({});
  const onTop = useCallback((h: House, y: number) => setTops((t) => (t[h] === y ? t : { ...t, [h]: y })), []);
  const scale = useHouseScale();

  return (
    <>
      <SunAndSky quality={quality} />
      <Ground />
      <Decor />
      <Transformer />
      {HOUSES.map((h) => (
        <HouseOnStreet key={h} house={h} scale={scale} cloud={byHouse[h].some((x) => x.tone === "cloud")}
          flag={flagged.get(h)} chips={byHouse[h]} onTop={onTop} />
      ))}
      {impostor && <Impostor claimed={impostor.claimed} price={impostor.price} />}
      {!outage && live.map((c) => <PowerArc key={c.contract_id} contract={c} sellerTop={tops[c.seller] ?? 2.5} buyerTop={tops[c.buyer] ?? 2.5} />)}
      <OrbitControls target={[0, 1.2, 0]} autoRotate autoRotateSpeed={0.35} enablePan={false}
        minDistance={12} maxDistance={45} maxPolarAngle={1.38} />
    </>
  );
});

function SunAndSky({ quality }: { quality: Quality }) {
  const sun = useHubStore((s) => s.sun) ?? { azimuth: 180, elevation: 55 };
  const { az, el } = { az: Math.round(sun.azimuth * 10) / 10, el: Math.round(sun.elevation * 10) / 10 };
  const v = useMemo(() => {
    const dir = sunVector(az, el);
    return { sky: dir.clone().multiplyScalar(100).toArray(), light: dir.clone().multiplyScalar(30).toArray(), disc: dir.clone().multiplyScalar(80).toArray() };
  }, [az, el]);
  const up = Math.max(0, Math.sin(THREE.MathUtils.degToRad(el)));
  const low = 1 - Math.min(1, el / 25);      // warmer light near the horizon
  const color = useMemo(() => new THREE.Color().setRGB(1, 0.93 - 0.25 * Math.max(0, low), 0.85 - 0.45 * Math.max(0, low)), [low]);
  const horizon = el > 5 ? "#cfe3f5" : el > -4 ? "#f2c9a0" : "#2b3550";
  return (
    <>
      <color attach="background" args={[horizon]} />
      <fog attach="fog" args={[horizon, 40, 120]} />
      <Sky sunPosition={v.sky} turbidity={6} rayleigh={el > 0 ? 1.2 : 3} mieCoefficient={0.006} mieDirectionalG={0.85} />
      <hemisphereLight args={["#dbeafe", "#a3b18a", 0.25 + 0.55 * up]} />
      <directionalLight position={v.light} intensity={el > -2 ? 0.3 + 2.4 * up : 0}
        color={color} castShadow={quality === "high"} shadow-mapSize={[2048, 2048]} shadow-bias={-0.0004} shadow-normalBias={0.02}
        shadow-camera-left={-20} shadow-camera-right={20} shadow-camera-top={20} shadow-camera-bottom={-20} />
      <mesh position={v.disc} visible={el > -3}>
        <sphereGeometry args={[2.6, 24, 24]} />
        <meshBasicMaterial color="#ffd36b" toneMapped={false} />
      </mesh>
    </>
  );
}

const ROAD_W = 2.6;

const Ground = memo(function Ground() {
  const roadLen = 200;
  return (
    <>
      <mesh rotation-x={-Math.PI / 2} receiveShadow>
        <planeGeometry args={[400, 400]} />
        <meshStandardMaterial color="#9cc27a" />
      </mesh>
      {/* the road from the west, ending in a turning circle */}
      <mesh rotation-x={-Math.PI / 2} receiveShadow position={[ROAD_END - roadLen / 2, 0.01, 0]}>
        <planeGeometry args={[roadLen, ROAD_W]} />
        <meshStandardMaterial color="#5b5f66" />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} receiveShadow position={[ROAD_END, 0.01, 0]}>
        <circleGeometry args={[3, 48]} />
        <meshStandardMaterial color="#5b5f66" />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position={[ROAD_END, 0.012, 0]}>
        <circleGeometry args={[1.1, 36]} />
        <meshStandardMaterial color="#7fae5e" />
      </mesh>
      {Array.from({ length: 30 }, (_, i) => (
        <mesh key={i} rotation-x={-Math.PI / 2} position={[ROAD_END - 5 - i * 4, 0.02, 0]}>
          <planeGeometry args={[1.6, 0.12]} />
          <meshStandardMaterial color="#f5f5f5" />
        </mesh>
      ))}
      {[-1, 1].map((side) => (
        <mesh key={side} rotation-x={-Math.PI / 2} receiveShadow position={[ROAD_END - 3 - roadLen / 2, 0.015, side * (ROAD_W / 2 + 0.35)]}>
          <planeGeometry args={[roadLen, 0.7]} />
          <meshStandardMaterial color="#d6d3cc" />
        </mesh>
      ))}
    </>
  );
});

function Kit({ name, position, rotation = 0, scale = 1 }: { name: string; position: [number, number, number]; rotation?: number; scale?: number }) {
  const { scene } = useGLTF(model(name));
  const obj = useMemo(() => {
    const c = scene.clone(true);
    c.traverse((o) => { if ((o as THREE.Mesh).isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    const box = new THREE.Box3().setFromObject(c);
    c.position.y = -box.min.y;                   // stand on the ground
    return c;
  }, [scene]);
  return <group position={position} rotation-y={rotation} scale={scale}><primitive object={obj} /></group>;
}

const TREES: [number, number, number, string][] = [
  [-10, -8.5, 1.7, "tree-large"], [-5.5, -9, 1.4, "tree-small"], [1, -9.2, 1.6, "tree-large"], [8.5, -8.6, 1.5, "tree-small"],
  [-10.5, 8.8, 1.6, "tree-small"], [-2.5, 9, 1.8, "tree-large"], [6, 8.6, 1.5, "tree-large"], [10.5, 6, 1.4, "tree-small"],
  [16.8, -3.5, 1.8, "tree-large"], [16.5, 3.8, 1.6, "tree-small"], [-14, 4, 1.7, "tree-large"], [-15, -4.5, 1.5, "tree-small"],
  [ROAD_END, 0, 1.3, "tree-small"],
];

const Decor = memo(function Decor() {
  return (
    <>
      {TREES.map(([x, z, s, name]) => <Kit key={`${x},${z}`} name={name} position={[x, 0, z]} scale={s} />)}
      <Kit name="planter" position={[-0.4, 0, 3.1]} scale={1.3} />
      <Kit name="planter" position={[8, 0, -3.1]} scale={1.3} />
    </>
  );
});

const POLE: [number, number, number] = [-11, 0, -2.4];
const POLE_TOP = 4.2;

const Transformer = memo(function Transformer() {
  return (
    <group position={POLE}>
      <mesh castShadow position={[0, POLE_TOP / 2, 0]}>
        <cylinderGeometry args={[0.09, 0.12, POLE_TOP, 10]} />
        <meshStandardMaterial color="#6b5b4b" />
      </mesh>
      <mesh castShadow position={[0, POLE_TOP - 0.9, 0.25]}>
        <boxGeometry args={[0.7, 0.8, 0.45]} />
        <meshStandardMaterial color="#8a9099" metalness={0.5} roughness={0.4} />
      </mesh>
      <Html position={[0, POLE_TOP + 0.5, 0]} center zIndexRange={[5, 0]} distanceFactor={14}>
        <span className="rounded-md bg-[#3a3a3c] px-1.5 py-0.5 text-[11px] font-bold text-white">T1</span>
      </Html>
    </group>
  );
});

// --- one house ---------------------------------------------------------------------------------------

/** One scale for every house (Kenney models share proportions): the widest fits FOOTPRINT. */
function useHouseScale(): number {
  const gltfs = useGLTF(ALL_MODELS.map(model));
  return useMemo(() => {
    const widest = Math.max(...gltfs.map((g) => {
      const size = new THREE.Box3().setFromObject(g.scene).getSize(new THREE.Vector3());
      return Math.max(size.x, size.z);
    }));
    return FOOTPRINT / widest;
  }, [gltfs]);
}

const HouseOnStreet = memo(function HouseOnStreet({ house, scale: s, cloud, flag, chips, onTop }:
  { house: House; scale: number; cloud: boolean; flag?: string; chips: Happening[]; onTop: (house: House, y: number) => void }) {
  const info = useHubStore((st) => st.houses[house]);
  const live = useHubStore((st) => st.live[house]);
  const outage = useHubStore((st) => !!st.outage);
  const { name, rotation } = placement(house, info);
  const { scene } = useGLTF(model(name));
  const { obj, top, width, depth } = useMemo(() => {
    const c = scene.clone(true);
    c.traverse((o) => { if ((o as THREE.Mesh).isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    const box = new THREE.Box3().setFromObject(c);
    const size = box.getSize(new THREE.Vector3());
    const mid = box.getCenter(new THREE.Vector3());
    c.scale.setScalar(s);
    c.position.set(-mid.x * s, -box.min.y * s, -mid.z * s);   // centred, so it turns in place
    return { obj: c, top: size.y * s, width: size.x * s, depth: size.z * s };
  }, [scene, s]);
  useEffect(() => onTop(house, top), [house, top, onTop]);

  const [x, z] = HOUSE_POS[house];
  const solarKw = live?.solar_kw ?? 0;
  const net = live ? live.solar_kw - live.use_kw : 0;
  const glow = info?.roof && !outage ? Math.min(1, solarKw / info.roof.kwp) : 0;
  const role = !live ? "" : outage ? "outage" : net >= 0.05 ? `${net.toFixed(2)} kW spare` : net <= -0.05 ? `${(-net).toFixed(2)} kW short` : "balanced";
  const toRoad = z > 0 ? -1 : 1;     // the driveway runs from the house to the road
  const reach = Math.abs(Math.cos(rotation)) * depth + Math.abs(Math.sin(rotation)) * width;   // north-south size once turned

  return (
    <group position={[x, 0, z]}>
      <group rotation-y={rotation}><primitive object={obj} /></group>
      <Kit name="driveway-short" position={[0.9, 0, toRoad * (reach / 2 + 0.55)]} rotation={toRoad > 0 ? 0 : Math.PI} scale={s} />
      {/* Always mounted (a light appearing or vanishing recompiles every material): brightness follows live solar. */}
      <pointLight position={[0, top + 1.2, 0]} color="#ffb547" intensity={7 * glow} distance={5} decay={2} />
      {cloud && <Cloud top={top} />}
      {flag && <FlagRing />}
      <Html position={[0, top + (cloud ? 4.2 : 1.4), 0]} center zIndexRange={[5, 0]} distanceFactor={16}>
        <div className="pointer-events-none flex flex-col items-center gap-1 whitespace-nowrap">
          {chips.filter((x) => x.house !== null).map((x) => (
            <span key={x.key} className={`rounded-full px-2.5 py-0.5 text-[12px] font-semibold shadow ${TONE_CLASS[x.tone]}`}>{x.label}</span>
          ))}
          <span className="rounded-full bg-white/90 px-3 py-1 text-[13px] font-semibold shadow">{info?.label ?? house}</span>
          {role && (
            <span className={`rounded-full px-2.5 py-0.5 text-[12px] font-medium shadow ${net >= 0.05 ? "bg-leaf-soft text-leaf-ink" : net <= -0.05 ? "bg-sky-soft text-sky" : "bg-white/90 text-ink-2"}`}>
              {info?.roof ? `☀ ${solarKw.toFixed(2)} kW · ` : ""}{role}
            </span>
          )}
        </div>
      </Html>
    </group>
  );
});

function Cloud({ top }: { top: number }) {
  const ref = useRef<THREE.Group>(null);
  useFrame(({ clock }) => { if (ref.current) ref.current.position.x = Math.sin(clock.elapsedTime * 0.3) * 0.6; });
  const puffs: [number, number, number, number][] = [[0, 0, 0, 1.1], [1, -0.15, 0.2, 0.85], [-1, -0.2, -0.1, 0.8], [0.4, 0.35, -0.3, 0.75], [-0.5, 0.3, 0.3, 0.7]];
  return (
    <>
      <group ref={ref} position={[0, top + 2.6, 0]}>
        {puffs.map(([x, y, z, r], i) => (
          <mesh key={i} position={[x, y, z]} castShadow>
            <sphereGeometry args={[r, 18, 18]} />
            <meshStandardMaterial color="#f4f6f8" roughness={1} />
          </mesh>
        ))}
      </group>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.03, 0]}>
        <circleGeometry args={[2.6, 40]} />
        <meshBasicMaterial color="#000" transparent opacity={0.18} depthWrite={false} />
      </mesh>
    </>
  );
}

function FlagRing() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const k = 1 + 0.12 * Math.sin(clock.elapsedTime * 4);
    ref.current.scale.set(k, k, 1);
  });
  return (
    <mesh ref={ref} rotation-x={-Math.PI / 2} position={[0, 0.05, 0]}>
      <ringGeometry args={[2.4, 2.75, 48]} />
      <meshBasicMaterial color="#ff3b30" transparent opacity={0.85} toneMapped={false} depthWrite={false} />
    </mesh>
  );
}

/** The impostor that tried to enter the market: a red ghost at the street's entrance, turned away. */
function Impostor({ claimed, price }: { claimed: string; price: number }) {
  const ref = useRef<THREE.Group>(null);
  useFrame(({ clock }) => { if (ref.current) ref.current.position.y = 0.15 + Math.sin(clock.elapsedTime * 2) * 0.1; });
  return (
    <group position={[-15.5, 0, 0]}>
      <group ref={ref}>
        <mesh position={[0, 0.9, 0]}>
          <boxGeometry args={[1.6, 1.6, 1.6]} />
          <meshStandardMaterial color="#ff3b30" transparent opacity={0.45} depthWrite={false} />
        </mesh>
        <mesh position={[0, 2.05, 0]} rotation-y={Math.PI / 4}>
          <coneGeometry args={[1.35, 0.9, 4]} />
          <meshStandardMaterial color="#ff3b30" transparent opacity={0.45} depthWrite={false} />
        </mesh>
      </group>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.03, 0]}>
        <ringGeometry args={[1.6, 1.9, 40]} />
        <meshBasicMaterial color="#ff3b30" toneMapped={false} depthWrite={false} />
      </mesh>
      <Html position={[0, 3.3, 0]} center zIndexRange={[5, 0]} distanceFactor={16}>
        <div className="pointer-events-none flex flex-col items-center gap-1 whitespace-nowrap">
          <span className="rounded-full bg-alert px-3 py-1 text-[13px] font-semibold text-white shadow">✗ Blacklisted</span>
          <span className="rounded-full bg-white/90 px-2.5 py-0.5 text-[12px] font-medium text-ink shadow">
            Fake “House {claimed.slice(1)}” · ask ₹{price.toFixed(2)} · wrong signature
          </span>
        </div>
      </Html>
    </group>
  );
}

// --- power between roofs ----------------------------------------------------------------------------

const PowerArc = memo(function PowerArc({ contract, sellerTop, buyerTop }: { contract: Contract; sellerTop: number; buyerTop: number }) {
  const { curve, points, mid } = useMemo(() => {
    const [sx, sz] = HOUSE_POS[contract.seller], [bx, bz] = HOUSE_POS[contract.buyer];
    const a = new THREE.Vector3(sx, sellerTop + 0.3, sz);
    const b = new THREE.Vector3(bx, buyerTop + 0.3, bz);
    const m = a.clone().add(b).multiplyScalar(0.5).add(new THREE.Vector3(0, 1.8 + a.distanceTo(b) * 0.18, 0));
    const c = new THREE.QuadraticBezierCurve3(a, m, b);
    return { curve: c, points: c.getPoints(48), mid: m };
  }, [contract.seller, contract.buyer, sellerTop, buyerTop]);
  const dots = useRef<THREE.Mesh[]>([]);
  useFrame(({ clock }) => {
    dots.current.forEach((m, i) => {
      if (m) m.position.copy(curve.getPoint(((clock.elapsedTime * 0.45) + i / 4) % 1));
    });
  });
  return (
    <group>
      <Line points={points} color="#ff9500" lineWidth={3} transparent opacity={0.55} />
      {[0, 1, 2, 3].map((i) => (
        <mesh key={i} ref={(m) => { if (m) dots.current[i] = m; }}>
          <sphereGeometry args={[0.16, 14, 14]} />
          <meshBasicMaterial color="#ffc04d" toneMapped={false} />
        </mesh>
      ))}
      <Html position={mid.toArray()} center zIndexRange={[5, 0]} distanceFactor={16}>
        <span className="num whitespace-nowrap rounded-full bg-white/95 px-3 py-1 text-[13px] font-semibold text-sun-ink shadow">
          {contract.kwh.toFixed(2)} kWh · {rupees(contract.price)}
        </span>
      </Html>
    </group>
  );
});

for (const name of [...ALL_MODELS, "driveway-short", "tree-large", "tree-small", "planter"]) useGLTF.preload(model(name));
