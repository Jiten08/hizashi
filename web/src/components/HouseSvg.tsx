// One house for the street SVG. Roof glow follows solar kW / kWp; dims in an outage.
export function HouseSvg({ x, y, label, glow, hasSolar, outage, cloud, spareKw }: {
  x: number; y: number; label: string; glow: number; hasSolar: boolean; outage: boolean; cloud: boolean; spareKw: number | null;
}) {
  const g = Math.max(0, Math.min(1, glow));
  const spare = spareKw !== null && spareKw >= 0.05;
  const short = spareKw !== null && spareKw <= -0.05;
  return (
    <g transform={`translate(${x} ${y})`} opacity={outage ? 0.45 : 1}>
      {hasSolar && g > 0.05 && !outage && (
        <circle cx="0" cy="-58" r={46 + 26 * g} fill="#fbbf24" opacity={0.18 + 0.32 * g} className="sun-glow" />
      )}
      <rect x="-62" y="-20" width="124" height="86" rx="6" fill="#fff" stroke="#e7e5e4" strokeWidth="2" />
      <rect x="-14" y="26" width="28" height="40" rx="3" fill="#f5f5f4" stroke="#e7e5e4" />
      <rect x="-48" y="0" width="24" height="20" rx="3" fill={outage ? "#e7e5e4" : "#fef3c7"} />
      <rect x="24" y="0" width="24" height="20" rx="3" fill={outage ? "#e7e5e4" : "#fef3c7"} />
      <polygon points="-76,-18 0,-78 76,-18" fill={hasSolar ? "#44403c" : "#a8a29e"} />
      {hasSolar && (
        <polygon points="-50,-30 0,-68 50,-30" fill={`rgba(217,138,4,${0.25 + 0.75 * g})`} stroke="#fde68a" strokeWidth="1.5" />
      )}
      {cloud && (
        <g transform="translate(18 -112)" opacity="0.95">
          <ellipse cx="0" cy="0" rx="34" ry="16" fill="#cbd5e1" />
          <ellipse cx="-18" cy="-8" rx="18" ry="14" fill="#cbd5e1" />
          <ellipse cx="14" cy="-12" rx="20" ry="16" fill="#e2e8f0" />
        </g>
      )}
      <text x="0" y="92" textAnchor="middle" className="fill-stone-800 text-[15px] font-semibold">{label}</text>
      {spareKw !== null && (
        <g transform="translate(0 112)">
          <rect x="-46" y="-12" width="92" height="22" rx="11" fill={spare ? "#dcfce7" : short ? "#e0f2fe" : "#f5f5f4"} />
          <text x="0" y="4" textAnchor="middle" className={`text-[11px] font-semibold ${spare ? "fill-emerald-800" : short ? "fill-sky-800" : "fill-stone-500"}`}>
            {spare ? `spare ${spareKw.toFixed(2)} kW` : short ? `short ${(-spareKw).toFixed(2)} kW` : "balanced"}
          </text>
        </g>
      )}
    </g>
  );
}
