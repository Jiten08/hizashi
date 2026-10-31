// /street/3d: the street in 3D for the stage. Kenney suburban houses, the real sun for the sim
// time (the hub sends its position), panels glowing with live solar, clouds over clouded roofs,
// power arcing between roofs for live deals, guard flags in red, an outage dims the street.
// The 2D dashboard (/) stays the default and the fallback. Every number comes from the hub.
import { Component, type ReactNode, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html, Line, OrbitControls, Sky, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { HaggleChat } from "../components/HaggleChat";
import { Button, Clock, Logo, toast } from "../components/ui";
import { useHub } from "../hooks/useHub";
import { blockKey, rupees } from "../lib/api";
import { HOUSES, type Contract, type House } from "../lib/types";
import { useHubStore } from "../store/hub";

const KIT = "/models/kenney_city-kit-suburban_20/Models/GLB format/";
const model = (name: string) => encodeURI(`${KIT}${name}.glb`);
const HOUSE_X: Record<House, number> = { h12: -7.5, h14: -2.5, h16: 2.5, h18: 7.5 };
const HOUSE_MODEL: Record<House, string> = { h12: "building-type-a", h14: "building-type-c", h16: "building-type-e", h18: "building-type-b" };
const FOOTPRINT = 3.4;
const FLAG_MINUTES = 45;           // a guard flag stays red on the street this long (sim minutes)
const QUALITY_KEY = "hizashi.3d.quality";

type Quality = "high" | "low";

function loadQuality(): Quality {
  try { return localStorage.getItem(QUALITY_KEY) === "low" ? "low" : "high"; } catch { return "high"; }
}

function webglOk(): boolean {
  try { return !!document.createElement("canvas").getContext("webgl2"); } catch { return false; }
}

/** pvlib azimuth (from north, clockwise) + elevation -> unit vector; north = -z, east = +x. */
function sunVector(az: number, el: number): THREE.Vector3 {
  const a = THREE.MathUtils.degToRad(az), e = THREE.MathUtils.degToRad(el);
  return new THREE.Vector3(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e));
}

// --- page ------------------------------------------------------------------------------------------

export default function Street3D() {
  const hub = useHub("street");
  const [quality, setQuality] = useState<Quality>(loadQuality);
  const outage = !!hub.outage;
  const shared = hub.contracts.reduce((a, c) => a + c.kwh, 0);
  const saved = HOUSES.reduce((a, h) => a + (hub.savings[h]?.saved_today ?? 0), 0);

  const seenFlags = useRef(-1);
  useEffect(() => {
    const fresh = seenFlags.current < 0 ? [] : hub.flags.slice(seenFlags.current);
    seenFlags.current = hub.flags.length;
    for (const f of fresh) toast(`Guard · ${f.title ?? "flag"}`, String(f.text ?? ""), "bad");
  }, [hub.flags.length]);

  const toggleQuality = () => {
    const q = quality === "high" ? "low" : "high";
    setQuality(q);
    try { localStorage.setItem(QUALITY_KEY, q); } catch { /* private mode */ }
  };

  return (
    <div className="fixed inset-0 bg-[#cfe3f5]">
      <div className={`absolute inset-0 transition-[filter] duration-700 ${outage ? "grayscale-[0.75] brightness-[0.55]" : ""}`}>
        {webglOk() ? (
          <Fallback>
            <Canvas shadows={quality === "high"} dpr={quality === "high" ? [1, 2] : 1}
              camera={{ position: [15, 10, 19], fov: 40 }} gl={{ antialias: quality === "high" }}>
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
          <Link to="/console"><Button small icon="sliders">Controls</Button></Link>
          <Link to="/"><Button small kind="tinted" icon="arrow">2D street</Button></Link>
        </div>
      </header>

      {outage && (
        <div className="absolute left-1/2 top-24 -translate-x-1/2 rounded-full bg-alert px-4 py-2 text-sm font-semibold text-white shadow-lg">
          Grid outage · no penalties for these blocks
        </div>
      )}

      <div className="pointer-events-none absolute bottom-5 left-5 flex gap-3">
        <Stat value={String(hub.contracts.length)} label="deals today" />
        <Stat value={`${shared.toFixed(1)} kWh`} label="shared between roofs" />
        <Stat value={rupees(saved)} label="saved vs BESCOM" tone="text-leaf-ink" />
      </div>

      <div className="absolute bottom-5 right-5 w-[360px] rounded-2xl bg-white/85 p-4 backdrop-blur-xl">
        <p className="mb-2 text-[13px] font-semibold">Agents haggling</p>
        <HaggleChat />
      </div>
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

function Scene({ quality }: { quality: Quality }) {
  const hub = useHubStore();
  const now = hub.sim_time ? Date.parse(hub.sim_time) : 0;
  const delivering = Object.entries(hub.blocks).find(([, s]) => s === "DELIVERING")?.[0];
  const live = delivering ? hub.contracts.filter((c) => blockKey(c.block) === delivering) : [];
  const clouded = new Set(hub.sim_events
    .filter((e) => e.type === "cloud" && Date.parse(e.start) <= now && Date.parse(e.end) > now)
    .flatMap((e) => (e.house ? [e.house] : HOUSES)));
  const flagged = new Map<string, string>();
  for (const f of hub.flags) {
    if (now - Date.parse(f.ts ?? "") <= FLAG_MINUTES * 60_000) for (const h of f.houses ?? []) flagged.set(h, String(f.title ?? "Guard flag"));
  }
  const roofTop = useRef<Record<string, number>>({});
  const scale = useHouseScale();

  return (
    <>
      <SunAndSky quality={quality} />
      <Ground />
      <Decor />
      <Transformer />
      {HOUSES.map((h) => (
        <HouseOnStreet key={h} house={h} scale={scale} cloud={clouded.has(h)} flag={flagged.get(h)}
          onTop={(y) => { roofTop.current[h] = y; }} />
      ))}
      {live.map((c) => <PowerArc key={c.contract_id} contract={c} tops={roofTop.current} />)}
      <OrbitControls target={[0, 1.2, 1]} autoRotate autoRotateSpeed={0.35} enablePan={false}
        minDistance={12} maxDistance={42} maxPolarAngle={1.38} />
    </>
  );
}

function SunAndSky({ quality }: { quality: Quality }) {
  const sun = useHubStore((s) => s.sun) ?? { azimuth: 180, elevation: 55 };
  const dir = useMemo(() => sunVector(sun.azimuth, sun.elevation), [sun.azimuth, sun.elevation]);
  const up = Math.max(0, Math.sin(THREE.MathUtils.degToRad(sun.elevation)));
  const low = 1 - Math.min(1, sun.elevation / 25);      // warmer light near the horizon
  const color = new THREE.Color().setRGB(1, 0.93 - 0.25 * Math.max(0, low), 0.85 - 0.45 * Math.max(0, low));
  const horizon = sun.elevation > 5 ? "#cfe3f5" : sun.elevation > -4 ? "#f2c9a0" : "#2b3550";
  return (
    <>
      <color attach="background" args={[horizon]} />
      <fog attach="fog" args={[horizon, 35, 110]} />
      <Sky sunPosition={dir.clone().multiplyScalar(100).toArray()} turbidity={6} rayleigh={sun.elevation > 0 ? 1.2 : 3}
        mieCoefficient={0.006} mieDirectionalG={0.85} />
      <hemisphereLight args={["#dbeafe", "#a3b18a", 0.25 + 0.55 * up]} />
      <directionalLight position={dir.clone().multiplyScalar(30).toArray()} intensity={sun.elevation > -2 ? 0.3 + 2.4 * up : 0}
        color={color} castShadow={quality === "high"} shadow-mapSize={[2048, 2048]} shadow-bias={-0.0004}
        shadow-camera-left={-18} shadow-camera-right={18} shadow-camera-top={18} shadow-camera-bottom={-18} />
      {sun.elevation > -3 && (
        <mesh position={dir.clone().multiplyScalar(80).toArray()}>
          <sphereGeometry args={[2.6, 24, 24]} />
          <meshBasicMaterial color="#ffd36b" toneMapped={false} />
        </mesh>
      )}
    </>
  );
}

function Ground() {
  return (
    <>
      <mesh rotation-x={-Math.PI / 2} receiveShadow position={[0, 0, 0]}>
        <planeGeometry args={[400, 400]} />
        <meshStandardMaterial color="#9cc27a" />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} receiveShadow position={[0, 0.01, 4.2]}>
        <planeGeometry args={[400, 3.4]} />
        <meshStandardMaterial color="#5b5f66" />
      </mesh>
      {Array.from({ length: 40 }, (_, i) => (
        <mesh key={i} rotation-x={-Math.PI / 2} position={[-80 + i * 4, 0.02, 4.2]}>
          <planeGeometry args={[1.6, 0.12]} />
          <meshStandardMaterial color="#f5f5f5" />
        </mesh>
      ))}
      <mesh rotation-x={-Math.PI / 2} receiveShadow position={[0, 0.015, 2.25]}>
        <planeGeometry args={[400, 0.6]} />
        <meshStandardMaterial color="#d6d3cc" />
      </mesh>
    </>
  );
}

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

function Decor() {
  return (
    <>
      {[-10, -5, 0, 5, 10].map((x, i) => <Kit key={`t${x}`} name={i % 2 ? "tree-small" : "tree-large"} position={[x, 0, -2.6]} scale={1.5} />)}
      {[-12.5, 12.5].map((x) => <Kit key={`e${x}`} name="tree-large" position={[x, 0, 1]} scale={1.8} />)}
      {HOUSES.map((h) => <Kit key={`d${h}`} name="driveway-short" position={[HOUSE_X[h] + 1.1, 0, 1.6]} scale={1.2} />)}
    </>
  );
}

const POLE: [number, number, number] = [-11, 0, 2.6];
const POLE_TOP = 4.2;

function Transformer() {
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
      <Html position={[0, POLE_TOP + 0.5, 0]} center distanceFactor={14}>
        <span className="rounded-md bg-[#3a3a3c] px-1.5 py-0.5 text-[11px] font-bold text-white">T1</span>
      </Html>
    </group>
  );
}

// --- one house ---------------------------------------------------------------------------------------

/** One scale for every house (Kenney models share proportions): the widest fits FOOTPRINT. */
function useHouseScale(): number {
  const gltfs = useGLTF(HOUSES.map((h) => model(HOUSE_MODEL[h])));
  return useMemo(() => {
    const widest = Math.max(...gltfs.map((g) => {
      const size = new THREE.Box3().setFromObject(g.scene).getSize(new THREE.Vector3());
      return Math.max(size.x, size.z);
    }));
    return FOOTPRINT / widest;
  }, [gltfs]);
}

function HouseOnStreet({ house, scale: s, cloud, flag, onTop }: { house: House; scale: number; cloud: boolean; flag?: string; onTop: (y: number) => void }) {
  const info = useHubStore((s) => s.houses[house]);
  const live = useHubStore((s) => s.live[house]);
  const outage = useHubStore((s) => !!s.outage);
  const { scene } = useGLTF(model(HOUSE_MODEL[house]));
  const { obj, top, depth } = useMemo(() => {
    const c = scene.clone(true);
    c.traverse((o) => { if ((o as THREE.Mesh).isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    const box = new THREE.Box3().setFromObject(c);
    const size = box.getSize(new THREE.Vector3());
    c.scale.setScalar(s);
    c.position.y = -box.min.y * s;
    return { obj: c, top: size.y * s, depth: size.z * s };
  }, [scene, s]);
  useEffect(() => onTop(top), [top]);

  const x = HOUSE_X[house];
  const solarKw = live?.solar_kw ?? 0;
  const net = live ? live.solar_kw - live.use_kw : 0;
  const glow = info?.roof ? Math.min(1, solarKw / info.roof.kwp) : 0;
  const role = !live ? "" : outage ? "outage" : net >= 0.05 ? `${net.toFixed(2)} kW spare` : net <= -0.05 ? `${(-net).toFixed(2)} kW short` : "balanced";

  return (
    <group position={[x, 0, 0]}>
      <primitive object={obj} />
      {info?.roof && <Panels kwp={info.roof.kwp} glow={outage ? 0 : glow} top={top} depth={depth} />}
      {cloud && <Cloud top={top} />}
      {flag && <FlagRing />}
      <Html position={[0, top + (cloud ? 4.2 : 1.4), 0]} center distanceFactor={16}>
        <div className="pointer-events-none flex flex-col items-center gap-1 whitespace-nowrap">
          {flag && <span className="rounded-full bg-alert px-2.5 py-1 text-[12px] font-semibold text-white shadow">{flag}</span>}
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
}

/** A south-facing array; glows with live output (0..1 of the roof's kWp). */
function Panels({ kwp, glow, top, depth }: { kwp: number; glow: number; top: number; depth: number }) {
  const cols = Math.min(6, Math.max(2, Math.ceil(kwp / 1.5)));
  const w = 0.42, h = 0.62, gap = 0.05;
  const width = cols * w + (cols - 1) * gap;
  return (
    // On a raised rack above the roof, as on many Bengaluru rooftops, tilted toward the south sun.
    <group position={[0, top - 0.02, depth * 0.05]} rotation-x={0.18}>
      {glow > 0.05 && <pointLight position={[0, 1.2, 0.6]} color="#ffb547" intensity={6 * glow} distance={4.5} decay={2} />}
      {Array.from({ length: cols * 2 }, (_, i) => {
        const col = i % cols, row = Math.floor(i / cols);
        return (
          <mesh key={i} castShadow position={[-width / 2 + w / 2 + col * (w + gap), 0.03, -0.33 + row * (h + gap)]}>
            <boxGeometry args={[w, 0.04, h]} />
            <meshStandardMaterial color="#2c4f9e" metalness={0.25} roughness={0.3}
              emissive="#5aa0ff" emissiveIntensity={0.08 + 0.45 * glow} />
          </mesh>
        );
      })}
    </group>
  );
}

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
            <meshStandardMaterial color="#f4f6f8" roughness={1} transparent opacity={0.95} />
          </mesh>
        ))}
      </group>
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.03, 0]}>
        <circleGeometry args={[2.6, 40]} />
        <meshBasicMaterial color="#000" transparent opacity={0.18} />
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
      <meshBasicMaterial color="#ff3b30" transparent opacity={0.85} toneMapped={false} />
    </mesh>
  );
}

// --- power between roofs ----------------------------------------------------------------------------

function PowerArc({ contract, tops }: { contract: Contract; tops: Record<string, number> }) {
  const a = new THREE.Vector3(HOUSE_X[contract.seller], (tops[contract.seller] ?? 2.5) + 0.3, 0.4);
  const b = new THREE.Vector3(HOUSE_X[contract.buyer], (tops[contract.buyer] ?? 2.5) + 0.3, 0.4);
  const mid = a.clone().add(b).multiplyScalar(0.5).add(new THREE.Vector3(0, 1.8 + a.distanceTo(b) * 0.18, 0));
  const curve = useMemo(() => new THREE.QuadraticBezierCurve3(a, mid, b), [contract.contract_id, a.y, b.y]);
  const points = useMemo(() => curve.getPoints(48), [curve]);
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
      <Html position={mid.toArray()} center distanceFactor={16}>
        <span className="num whitespace-nowrap rounded-full bg-white/95 px-3 py-1 text-[13px] font-semibold text-sun-ink shadow">
          {contract.kwh.toFixed(2)} kWh · {rupees(contract.price)}
        </span>
      </Html>
    </group>
  );
}

for (const h of HOUSES) useGLTF.preload(model(HOUSE_MODEL[h]));
