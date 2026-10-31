/**
 * First-run setup: solar or not, size and facing, PM Surya Ghar subsidy, meter, then the wallet's
 * limits. The hub previews the buyback rate and clear-day output; nothing is priced on the phone.
 * Finish = POST /api/houses/{h}/setup (+ PUT mandate if the limits changed).
 */
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { type ReactNode, useEffect, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Button, Card, IconTile, type IconName, Section, Segmented, Separator, Stepper } from "../components/ui";
import { MandateSteppers } from "../components/MandateSteppers";
import { api, useHub } from "../lib/store";
import { C, T } from "../lib/theme";
import type { Mandate, SetupBody, SetupResult } from "../lib/types";

type Step = "welcome" | "solar" | "system" | "subsidy" | "limits" | "review";
type Facing = SetupBody["facing"];

export default function Onboarding() {
  const insets = useSafeAreaInsets();
  const hub = useHub();
  const house = hub.conn!.house;
  const info = hub.houses[house];
  const [step, setStep] = useState<Step>("welcome");
  const [hasSolar, setHasSolar] = useState(!!info?.roof);
  const [kwp, setKwp] = useState(info?.roof?.kwp ?? 3);
  const [facing, setFacing] = useState<Facing>(info?.roof?.azimuth === 90 ? "east" : info?.roof?.azimuth === 270 ? "west" : "south");
  const [subsidized, setSubsidized] = useState(!!info?.subsidized);
  const [metering, setMetering] = useState<"net" | "gross">(info?.metering === "gross" ? "gross" : "net");
  const [limits, setLimits] = useState<Mandate>(hub.mandates[house]);
  const [preview, setPreview] = useState<SetupResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const body: SetupBody = { has_solar: hasSolar, kwp, facing, subsidized, metering };
  useEffect(() => {
    const t = setTimeout(() => { api().setup(house, { ...body, preview: true }).then(setPreview).catch(() => {}); }, 200);
    return () => clearTimeout(t);
  }, [hasSolar, kwp, facing, subsidized, metering]);

  const steps: Step[] = hasSolar ? ["welcome", "solar", "system", "subsidy", "limits", "review"] : ["welcome", "solar", "limits", "review"];
  const at = steps.indexOf(step);
  const next = () => setStep(steps[Math.min(at + 1, steps.length - 1)]);
  const back = () => (at === 0 ? (info?.onboarded ? router.back() : undefined) : setStep(steps[at - 1]));

  const finish = async () => {
    setSaving(true);
    setError(null);
    try {
      await api().setup(house, body);
      if (JSON.stringify(limits) !== JSON.stringify(hub.mandates[house])) await api().putMandate(house, limits);
      router.replace("/today");
    } catch (e) {
      setError((e as Error).message);
      setSaving(false);
    }
  };

  const tariffs = preview?.tariffs;
  return (
    <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: insets.top }}>
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: 8, height: 44 }}>
        {at > 0 || info?.onboarded ? (
          <Pressable onPress={back} hitSlop={10} style={{ flexDirection: "row", alignItems: "center", padding: 8 }}>
            <Ionicons name="chevron-back" size={24} color={C.orange} />
            <Text style={[T.body, { color: C.orange }]}>Back</Text>
          </Pressable>
        ) : null}
        <View style={{ flex: 1, flexDirection: "row", justifyContent: "center", gap: 6 }}>
          {steps.map((s, i) => (
            <View key={s} style={{ width: i === at ? 18 : 6, height: 6, borderRadius: 3, backgroundColor: i <= at ? C.orange : C.label3 }} />
          ))}
        </View>
        <View style={{ width: 70 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 24 }}>
        {step === "welcome" && (
          <>
            <Text style={[T.footnote, { fontWeight: "600", color: C.orange }]}>{info?.label}</Text>
            <Text style={[T.largeTitle, { marginTop: 4 }]}>Your home gets its own energy agent</Text>
            <Text style={[T.body, { color: C.label2, marginTop: 10 }]}>
              Two minutes to set up. Then it trades with your neighbours every 15 minutes, inside limits only you can change.
            </Text>
            <View style={{ marginTop: 28, gap: 22 }}>
              <Point icon="swap-horizontal" bg={C.orange} title="It haggles for you">Sells spare rooftop power, or buys a neighbour's, for less than BESCOM.</Point>
              <Point icon="shield-checkmark" bg={C.blue} title="Your wallet says no">Anything outside your limits is refused before it's ever sent.</Point>
              <Point icon="trending-up" bg={C.green} title="You see what you saved">Every deal settles under KERC rules and shows against your BESCOM bill.</Point>
            </View>
          </>
        )}

        {step === "solar" && (
          <Question title="Do you have rooftop solar?" sub="Homes without solar save too: they buy neighbours' spare power below the BESCOM rate.">
            <Choice icon="sunny" title="Yes, I have solar panels" hint="Sell what you don't use, buy when you're short" selected={hasSolar} onPress={() => setHasSolar(true)} />
            <Choice icon="home" title="No solar" hint="Buy from neighbours' roofs" selected={!hasSolar} onPress={() => setHasSolar(false)} />
          </Question>
        )}

        {step === "system" && (
          <Question title="About your panels" sub="It's on your installation papers or the inverter label.">
            <View style={{ backgroundColor: C.card, borderRadius: 12, overflow: "hidden" }}>
              <Stepper label="System size" value={kwp} step={0.5} min={1} max={10} onChange={setKwp} format={(v) => `${v.toFixed(1)} kWp`} />
            </View>
            <Text style={[T.sectionHeader, { marginLeft: 16, marginTop: 14 }]}>Panels face</Text>
            <Segmented value={facing} onChange={setFacing}
              options={[{ value: "south", label: "South" }, { value: "east", label: "East" }, { value: "west", label: "West" }]} />
            <Estimate preview={preview} />
          </Question>
        )}

        {step === "subsidy" && (
          <Question title="PM Surya Ghar subsidy?" sub="Subsidised systems get a lower BESCOM buyback rate, so selling to a neighbour is worth more to you.">
            <Choice icon="ribbon" title="Yes, subsidised" selected={subsidized} onPress={() => setSubsidized(true)}
              hint={tariffs ? `BESCOM pays ₹${tariffs.buyback.subsidized_upto_2kw.toFixed(2)} (up to 2 kW) or ₹${tariffs.buyback.subsidized_above_2kw.toFixed(2)} per unit` : "Lower buyback rate"} />
            <Choice icon="cash" title="No subsidy" selected={!subsidized} onPress={() => setSubsidized(false)}
              hint={tariffs ? `BESCOM pays ₹${tariffs.buyback.unsubsidized.toFixed(2)} per unit` : "Standard buyback rate"} />
            <Text style={[T.sectionHeader, { marginLeft: 16, marginTop: 14 }]}>Meter</Text>
            <Segmented value={metering} onChange={setMetering} options={[{ value: "net", label: "Net metering" }, { value: "gross", label: "Gross metering" }]} />
            <Estimate preview={preview} />
          </Question>
        )}

        {step === "limits" && (
          <Question title="Set your limits" sub="Your wallet signs nothing outside these. Change them any time in Rules.">
            <View style={{ backgroundColor: C.card, borderRadius: 12, overflow: "hidden" }}>
              <MandateSteppers m={limits} set={(p) => setLimits({ ...limits, ...p })} hasSolar={hasSolar} />
            </View>
          </Question>
        )}

        {step === "review" && (
          <Question title="All set?" sub="Your agent starts with the next 15-minute block.">
            <Section style={{ marginTop: 0 }}>
              <Line k="Solar" v={hasSolar ? `${kwp.toFixed(1)} kWp, facing ${facing}` : "None"} />
              {hasSolar ? <Line k="Subsidy" v={subsidized ? "PM Surya Ghar" : "None"} /> : null}
              {hasSolar ? <Line k="BESCOM buyback" v={preview?.house.buyback_rate != null ? `₹${preview.house.buyback_rate.toFixed(2)}` : "…"} /> : null}
              {hasSolar ? <Line k="Clear-day output" v={preview ? `≈ ${preview.clear_day_kwh} kWh` : "…"} /> : null}
              {hasSolar ? <Line k="Never sell below" v={`₹${limits.min_sell_price.toFixed(2)}`} /> : null}
              <Line k="Never buy above" v={`₹${limits.max_buy_price.toFixed(2)}`} />
              <Line k="Daily budget" v={`₹${limits.daily_budget.toFixed(0)}`} />
              <Line k="Ask me above" v={`₹${limits.approve_above.toFixed(0)}`} last />
            </Section>
            {error ? <Text style={[T.footnote, { color: C.red }]}>{error}</Text> : null}
          </Question>
        )}
      </ScrollView>

      <View style={{ padding: 16, paddingBottom: insets.bottom + 12 }}>
        {step === "review"
          ? <Button title="Start trading" onPress={finish} busy={saving} />
          : <Button title={step === "welcome" ? "Set up my home" : "Continue"} onPress={next} />}
      </View>
    </View>
  );
}

function Point({ icon, bg, title, children }: { icon: IconName; bg: string; title: string; children: ReactNode }) {
  return (
    <View style={{ flexDirection: "row", gap: 14, alignItems: "flex-start" }}>
      <IconTile name={icon} bg={bg} size={40} />
      <View style={{ flex: 1 }}>
        <Text style={T.headline}>{title}</Text>
        <Text style={[T.subhead, { marginTop: 2 }]}>{children}</Text>
      </View>
    </View>
  );
}

function Question({ title, sub, children }: { title: string; sub: string; children: ReactNode }) {
  return (
    <>
      <Text style={T.largeTitle}>{title}</Text>
      <Text style={[T.body, { color: C.label2, marginTop: 8, marginBottom: 22 }]}>{sub}</Text>
      <View style={{ gap: 10 }}>{children}</View>
    </>
  );
}

function Choice({ icon, title, hint, selected, onPress }: { icon: IconName; title: string; hint: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={{ flexDirection: "row", alignItems: "center", gap: 14, backgroundColor: C.card, borderRadius: 14, padding: 14,
      borderWidth: 2, borderColor: selected ? C.orange : "transparent" }}>
      <IconTile name={icon} bg={selected ? C.orange : "#C7C7CC"} size={40} />
      <View style={{ flex: 1 }}>
        <Text style={T.headline}>{title}</Text>
        <Text style={[T.footnote, { marginTop: 2 }]}>{hint}</Text>
      </View>
      <Ionicons name={selected ? "checkmark-circle" : "ellipse-outline"} size={26} color={selected ? C.orange : C.label3} />
    </Pressable>
  );
}

function Estimate({ preview }: { preview: SetupResult | null }) {
  if (!preview?.house.roof) return null;
  return (
    <Card style={{ flexDirection: "row", alignItems: "center", gap: 12, marginTop: 6 }}>
      <Ionicons name="sunny" size={26} color={C.orange} />
      <View style={{ flex: 1 }}>
        <Text style={T.callout}>About <Text style={{ fontWeight: "700" }}>{preview.clear_day_kwh} kWh</Text> on a clear day</Text>
        <Text style={T.footnote}>BESCOM buys yours at ₹{preview.house.buyback_rate?.toFixed(2)} · neighbours pay ~₹{preview.tariffs.expected_p2p_price.toFixed(2)}</Text>
      </View>
    </Card>
  );
}

function Line({ k, v, last }: { k: string; v: string; last?: boolean }) {
  return (
    <>
      <View style={{ flexDirection: "row", justifyContent: "space-between", paddingHorizontal: 16, paddingVertical: 12 }}>
        <Text style={T.body}>{k}</Text>
        <Text style={[T.body, T.number, { color: C.label2 }]}>{v}</Text>
      </View>
      {!last ? <Separator /> : null}
    </>
  );
}
