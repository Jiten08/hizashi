// One house in the street illustration. Roof panels glow with live solar; dims in an outage.
export function HouseSvg({ x, y, label, glow, hasSolar, outage, cloud, spareKw }: {
  x: number; y: number; label: string; glow: number; hasSolar: boolean; outage: boolean; cloud: boolean; spareKw: number | null;
}) {
  const g = Math.max(0, Math.min(1, glow));
  const spare = spareKw !== null && spareKw >= 0.05;
  const short = spareKw !== null && spareKw <= -0.05;
  return (
    <g transform={`translate(${x} ${y})`} opacity={outage ? 0.4 : 1}>
      {hasSolar && g > 0.05 && !outage && (
        <circle cx="0" cy="-46" r={40 + 30 * g} fill="url(#sunGlow)" opacity={0.35 + 0.5 * g} className="breathe" />
      )}
      <rect x="-58" y="-16" width="116" height="78" rx="10" fill="#fff" stroke="rgba(0,0,0,0.07)" />
      <rect x="-12" y="24" width="24" height="38" rx="5" fill="#f2f2f7" />
      <rect x="-44" y="4" width="22" height="18" rx="4" fill={outage ? "#e5e5ea" : "#fff4d6"} />
      <rect x="22" y="4" width="22" height="18" rx="4" fill={outage ? "#e5e5ea" : "#fff4d6"} />
      <path d="M-70 -14 L0 -66 L70 -14 Z" fill={hasSolar ? "#3a3a3c" : "#c7c7cc"} strokeLinejoin="round" />
      {hasSolar && <path d="M-44 -26 L0 -58 L44 -26 Z" fill={`rgba(255,149,0,${0.3 + 0.7 * g})`} />}
      {cloud && (
        <g transform="translate(22 -100)">
          <ellipse cx="0" cy="0" rx="34" ry="15" fill="#d1d1d6" />
          <ellipse cx="-16" cy="-8" rx="17" ry="13" fill="#d1d1d6" />
          <ellipse cx="13" cy="-11" rx="19" ry="15" fill="#e5e5ea" />
        </g>
      )}
      <text x="0" y="86" textAnchor="middle" fill="#1d1d1f" style={{ fontSize: 15, fontWeight: 600 }}>{label}</text>
      {spareKw !== null && (
        <g transform="translate(0 108)">
          <rect x="-48" y="-12" width="96" height="22" rx="11" fill={spare ? "#e9f8ee" : short ? "#e5f1ff" : "#f2f2f7"} />
          <text x="0" y="4" textAnchor="middle" fill={spare ? "#248a3d" : short ? "#0060df" : "#6e6e73"} style={{ fontSize: 11.5, fontWeight: 600 }}>
            {spare ? `${spareKw.toFixed(2)} kW spare` : short ? `${(-spareKw).toFixed(2)} kW short` : "balanced"}
          </text>
        </g>
      )}
    </g>
  );
}
