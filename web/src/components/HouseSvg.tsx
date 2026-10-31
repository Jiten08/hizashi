/** One house for the street view. `glow` 0..1 = roof solar output (R2.6). */
export function HouseSvg({ x, label, glow = 0, solar = true, dim = false }: {
  x: number; label: string; glow?: number; solar?: boolean; dim?: boolean;
}) {
  return (
    <g transform={`translate(${x},0)`} opacity={dim ? 0.35 : 1}>
      <polygon points="0,60 50,20 100,60" fill={solar ? `rgba(217,138,4,${0.25 + 0.75 * glow})` : "#a8a29e"} />
      <rect x="10" y="60" width="80" height="60" fill="#fafaf9" stroke="#d6d3d1" />
      <rect x="40" y="90" width="20" height="30" fill="#d6d3d1" />
      <text x="50" y="140" textAnchor="middle" fontSize="12" fill="#44403c">{label}</text>
    </g>
  );
}
