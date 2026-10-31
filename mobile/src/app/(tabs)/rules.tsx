// Rules: the wallet's limits (Save = a new mandate version in the ledger), the home's setup, disconnect.
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Switch, Text, View } from "react-native";
import { MandateSteppers } from "../../components/MandateSteppers";
import { Button, Row, Screen, Section, Segmented } from "../../components/ui";
import { api, disconnect, useHub } from "../../lib/store";
import { C, T } from "../../lib/theme";
import type { Mandate } from "../../lib/types";

export default function Rules() {
  const hub = useHub();
  const house = hub.conn!.house;
  const current = hub.mandates[house];
  const info = hub.houses[house];
  const [m, setM] = useState<Mandate | undefined>(current);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  useEffect(() => { setM(current); }, [current?.version]);
  if (!m || !current || !info) return null;
  const dirty = JSON.stringify(m) !== JSON.stringify(current);
  const set = (p: Partial<Mandate>) => { setM({ ...m, ...p }); setState("idle"); };
  const save = async () => {
    setState("saving");
    try { await api().putMandate(house, m); setState("saved"); } catch { setState("error"); }
  };

  return (
    <Screen title="Rules">
      <Section footer="Off means your wallet refuses every offer.">
        <Row title="Trading" accessory={<Switch value={!m.paused} onValueChange={(on) => set({ paused: !on })} trackColor={{ true: C.green }} />} last />
      </Section>

      <Section header={`Your wallet's limits · v${current.version}`}
        footer={state === "saved" ? "Saved. Your wallet uses the new limits now." : state === "error" ? "Couldn't save. Try again." : "Each change is signed into your ledger."}>
        <MandateSteppers m={m} set={set} hasSolar={!!info.roof} />
      </Section>

      <Section header="Trade with">
        <View style={{ padding: 12 }}>
          <Segmented value={m.counterparties} onChange={(v) => set({ counterparties: v })}
            options={[{ value: "same_transformer", label: `My transformer (${info.transformer})` }, { value: "street", label: "Whole street" }]} />
        </View>
      </Section>

      {dirty ? (
        <View style={{ flexDirection: "row", gap: 10, marginTop: 16 }}>
          <Button title="Undo" kind="gray" style={{ flex: 1 }} onPress={() => { setM(current); setState("idle"); }} />
          <Button title="Save" style={{ flex: 1 }} onPress={save} busy={state === "saving"} />
        </View>
      ) : null}

      <Section header="Your home">
        <Row icon={info.roof ? "sunny" : "home"} iconBg={info.roof ? C.orange : C.blue}
          title={info.roof ? `${info.roof.kwp} kWp rooftop solar` : "No rooftop solar"}
          subtitle={info.roof ? `${info.subsidized ? "PM Surya Ghar" : "No subsidy"} · buyback ₹${info.buyback_rate?.toFixed(2)} · ${info.metering} meter` : "Your agent buys from neighbours' roofs"}
          onPress={() => router.push("/onboarding")} chevron last />
      </Section>

      <Section header="Say it in a sentence" footer="Coming next: type “don't buy above ₹5” and your agent proposes the limits.">
        <Row title="Rules from a sentence" value="Soon" last />
      </Section>

      <Section>
        <Row title={`Connected to ${hub.conn!.hub.replace(/^https?:\/\//, "")}`} subtitle={info.label} last />
      </Section>
      <Button title="Disconnect this phone" kind="plain" color={C.red} style={{ marginTop: 8 }}
        onPress={async () => { await disconnect(); router.replace("/connect"); }} />
      <Text style={[T.caption, { textAlign: "center", marginTop: 4 }]}>Weather: {hub.weather_source ?? "—"} · homes and meters simulated</Text>
    </Screen>
  );
}
