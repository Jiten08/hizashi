// Apple system palette (light) + type scale. One accent: system orange, for the sun.
import { Platform } from "react-native";

export const C = {
  bg: "#F2F2F7",            // systemGroupedBackground
  card: "#FFFFFF",          // secondarySystemGroupedBackground
  fill: "#F2F2F7",
  fill2: "rgba(120,120,128,0.12)",
  label: "#000000",
  label2: "rgba(60,60,67,0.6)",
  label3: "rgba(60,60,67,0.3)",
  sep: "rgba(60,60,67,0.18)",
  orange: "#FF9500",
  orangeSoft: "#FFF4E0",
  green: "#34C759",
  greenText: "#248A3D",
  greenSoft: "#E9F8EE",
  red: "#FF3B30",
  redSoft: "#FFECEB",
  blue: "#007AFF",
  blueSoft: "#E5F1FF",
  indigo: "#5856D6",
};

const rounded = Platform.select({ ios: "System", default: undefined });

export const T = {
  largeTitle: { fontSize: 34, fontWeight: "700" as const, letterSpacing: 0.37, color: C.label },
  title2: { fontSize: 22, fontWeight: "700" as const, letterSpacing: 0.35, color: C.label },
  title3: { fontSize: 20, fontWeight: "600" as const, letterSpacing: 0.38, color: C.label },
  headline: { fontSize: 17, fontWeight: "600" as const, letterSpacing: -0.41, color: C.label },
  body: { fontSize: 17, letterSpacing: -0.41, color: C.label },
  callout: { fontSize: 16, letterSpacing: -0.32, color: C.label },
  subhead: { fontSize: 15, letterSpacing: -0.24, color: C.label2 },
  footnote: { fontSize: 13, letterSpacing: -0.08, color: C.label2 },
  caption: { fontSize: 12, color: C.label2 },
  sectionHeader: { fontSize: 13, letterSpacing: -0.08, color: C.label2, textTransform: "uppercase" as const },
  number: { fontFamily: rounded, fontVariant: ["tabular-nums" as const] },
};

export const R = { card: 12, big: 22 };
