// iOS-style building blocks: large-title screens, inset grouped sections, rows, buttons,
// rings, steppers and a segmented control. Colours and type come from lib/theme.
import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import type { ComponentProps, ReactNode } from "react";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View, type ViewStyle } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Circle } from "react-native-svg";
import { C, R, T } from "../lib/theme";

export type IconName = ComponentProps<typeof Ionicons>["name"];

export function Screen({ title, subtitle, right, children, onRefresh, refreshing = false }: {
  title: string; subtitle?: ReactNode; right?: ReactNode; children: ReactNode; onRefresh?: () => void; refreshing?: boolean;
}) {
  const insets = useSafeAreaInsets();
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: C.bg }}
      contentContainerStyle={{ paddingTop: insets.top + 8, paddingBottom: 32, paddingHorizontal: 16 }}
      refreshControl={onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} /> : undefined}
    >
      <View style={s.titleRow}>
        <View style={{ flex: 1 }}>
          {subtitle ? <Text style={[T.footnote, { fontWeight: "600" }]}>{subtitle}</Text> : null}
          <Text style={T.largeTitle}>{title}</Text>
        </View>
        {right}
      </View>
      {children}
    </ScrollView>
  );
}

export function Section({ header, footer, children, style }: { header?: string; footer?: string; children: ReactNode; style?: ViewStyle }) {
  return (
    <View style={[{ marginTop: 22 }, style]}>
      {header ? <Text style={[T.sectionHeader, { marginLeft: 16, marginBottom: 7 }]}>{header}</Text> : null}
      <View style={s.group}>{children}</View>
      {footer ? <Text style={[T.footnote, { marginHorizontal: 16, marginTop: 7 }]}>{footer}</Text> : null}
    </View>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[s.group, { padding: 16 }, style]}>{children}</View>;
}

export function IconTile({ name, bg, size = 29 }: { name: IconName; bg: string; size?: number }) {
  return (
    <View style={{ width: size, height: size, borderRadius: size * 0.24, backgroundColor: bg, alignItems: "center", justifyContent: "center" }}>
      <Ionicons name={name} size={size * 0.62} color="#fff" />
    </View>
  );
}

export function Row({ icon, iconBg = C.orange, title, subtitle, value, valueColor, onPress, chevron, last, accessory }: {
  icon?: IconName; iconBg?: string; title: string; subtitle?: string; value?: string; valueColor?: string;
  onPress?: () => void; chevron?: boolean; last?: boolean; accessory?: ReactNode;
}) {
  const body = (
    <View style={s.row}>
      {icon ? <View style={{ marginRight: 12 }}><IconTile name={icon} bg={iconBg} /></View> : null}
      <View style={[s.rowMain, !last && s.rowSep]}>
        <View style={{ flex: 1, paddingVertical: subtitle ? 9 : 12 }}>
          <Text style={T.body} numberOfLines={2}>{title}</Text>
          {subtitle ? <Text style={[T.footnote, { marginTop: 1 }]} numberOfLines={2}>{subtitle}</Text> : null}
        </View>
        {value ? <Text style={[T.body, T.number, { color: valueColor ?? C.label2, marginLeft: 8 }]}>{value}</Text> : null}
        {accessory}
        {chevron ? <Ionicons name="chevron-forward" size={17} color={C.label3} style={{ marginLeft: 6 }} /> : null}
      </View>
    </View>
  );
  return onPress ? <Pressable onPress={onPress} style={({ pressed }) => pressed && { backgroundColor: "#E5E5EA" }}>{body}</Pressable> : body;
}

export function Button({ title, onPress, kind = "filled", color = C.orange, icon, disabled, busy, style }: {
  title: string; onPress: () => void; kind?: "filled" | "tinted" | "gray" | "plain"; color?: string;
  icon?: IconName; disabled?: boolean; busy?: boolean; style?: ViewStyle;
}) {
  const bg = kind === "filled" ? color : kind === "tinted" ? `${color}22` : kind === "gray" ? C.fill2 : "transparent";
  const fg = kind === "filled" ? "#fff" : kind === "gray" ? C.label : color;
  return (
    <Pressable
      disabled={disabled || busy}
      onPress={() => { Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {}); onPress(); }}
      style={({ pressed }) => [s.button, { backgroundColor: bg, opacity: disabled ? 0.4 : pressed ? 0.75 : 1 }, style]}
    >
      {busy ? <ActivityIndicator color={fg} /> : (
        <>
          {icon ? <Ionicons name={icon} size={18} color={fg} style={{ marginRight: 6 }} /> : null}
          <Text style={[T.headline, { color: fg }]}>{title}</Text>
        </>
      )}
    </Pressable>
  );
}

export function Pill({ text, color = C.label2, bg = C.fill2 }: { text: string; color?: string; bg?: string }) {
  return (
    <View style={{ backgroundColor: bg, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3 }}>
      <Text style={{ fontSize: 12, fontWeight: "600", color }}>{text}</Text>
    </View>
  );
}

/** Apple Fitness-style ring. progress 0..1 (clamped). */
export function Ring({ size, stroke, progress, color, children }: { size: number; stroke: number; progress: number; color: string; children?: ReactNode }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const p = Math.max(0, Math.min(1, progress));
  return (
    <View style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
      <Svg width={size} height={size} style={StyleSheet.absoluteFill}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={`${color}2E`} strokeWidth={stroke} fill="none" />
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={`${c * p} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </Svg>
      {children}
    </View>
  );
}

export function Stepper({ label, hint, value, onChange, step, min = 0, max = 999, format }: {
  label: string; hint?: string; value: number; onChange: (v: number) => void; step: number; min?: number; max?: number; format: (v: number) => string;
}) {
  const bump = (d: number) => {
    const v = Math.round((value + d) * 100) / 100;
    if (v >= min && v <= max) { Haptics.selectionAsync().catch(() => {}); onChange(v); }
  };
  return (
    <View style={[s.row, { paddingVertical: 10 }]}>
      <View style={{ flex: 1, paddingRight: 8 }}>
        <Text style={T.body}>{label}</Text>
        {hint ? <Text style={T.footnote}>{hint}</Text> : null}
      </View>
      <Text style={[T.headline, T.number, { minWidth: 64, textAlign: "right", marginRight: 10 }]}>{format(value)}</Text>
      <View style={s.stepper}>
        <Pressable onPress={() => bump(-step)} hitSlop={6} style={s.stepBtn}><Ionicons name="remove" size={20} color={C.label} /></Pressable>
        <View style={{ width: StyleSheet.hairlineWidth, height: 18, backgroundColor: C.label3 }} />
        <Pressable onPress={() => bump(step)} hitSlop={6} style={s.stepBtn}><Ionicons name="add" size={20} color={C.label} /></Pressable>
      </View>
    </View>
  );
}

export function Segmented<T extends string>({ options, value, onChange }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <View style={s.segment}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <Pressable key={o.value} onPress={() => { Haptics.selectionAsync().catch(() => {}); onChange(o.value); }}
            style={[s.segmentItem, on && s.segmentOn]}>
            <Text style={{ fontSize: 13, fontWeight: on ? "600" : "500", color: C.label }}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Separator() {
  return <View style={{ height: StyleSheet.hairlineWidth, backgroundColor: C.sep, marginLeft: 16 }} />;
}

export const s = StyleSheet.create({
  titleRow: { flexDirection: "row", alignItems: "flex-end", marginBottom: 4 },
  group: { backgroundColor: C.card, borderRadius: R.card, overflow: "hidden" },
  row: { flexDirection: "row", alignItems: "center", paddingLeft: 16, minHeight: 44 },
  rowMain: { flex: 1, flexDirection: "row", alignItems: "center", paddingRight: 16 },
  rowSep: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: C.sep },
  button: { height: 50, borderRadius: 14, flexDirection: "row", alignItems: "center", justifyContent: "center", paddingHorizontal: 16 },
  stepper: { flexDirection: "row", alignItems: "center", backgroundColor: C.fill2, borderRadius: 9, height: 32 },
  stepBtn: { width: 46, height: 32, alignItems: "center", justifyContent: "center" },
  segment: { flexDirection: "row", backgroundColor: C.fill2, borderRadius: 9, padding: 2 },
  segmentItem: { flex: 1, height: 30, alignItems: "center", justifyContent: "center", borderRadius: 7 },
  segmentOn: { backgroundColor: "#fff", shadowColor: "#000", shadowOpacity: 0.12, shadowRadius: 4, shadowOffset: { width: 0, height: 2 }, elevation: 2 },
});
