// Rules: the wallet's limits (Save = a new mandate version in the ledger), the home's setup.
import { useEffect, useState } from "react";
import { MandateSteppers } from "../components/MandateSteppers";
import { NotificationsSection } from "../components/Notifications";
import { Button, Row, Screen, Section, Segmented, Toggle } from "../components/ui";
import { api } from "../lib/api";
import { useHubStore } from "../lib/store";
import type { House, Mandate } from "../lib/types";

export default function Rules({ house, onEditSetup, onSwitchHouse }: { house: House; onEditSetup: () => void; onSwitchHouse: () => void }) {
  const current = useHubStore((s) => s.mandates[house]);
  const info = useHubStore((s) => s.houses[house]);
  const weather = useHubStore((s) => s.weather_source);
  const [m, setM] = useState<Mandate | undefined>(current);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  useEffect(() => { setM(current); }, [current?.version]);
  if (!m || !current || !info) return null;
  const dirty = JSON.stringify(m) !== JSON.stringify(current);
  const set = (p: Partial<Mandate>) => { setM({ ...m, ...p }); setState("idle"); };
  const save = async () => {
    setState("saving");
    try { await api.putMandate(house, m); setState("saved"); } catch { setState("error"); }
  };

  return (
    <Screen title="Rules">
      <Section footer="Off means your wallet refuses every offer.">
        <Row title="Trading" last accessory={<Toggle on={!m.paused} onChange={(on) => set({ paused: !on })} label="Trading" />} />
      </Section>

      <Section header={`Your wallet's limits · v${current.version}`}
        footer={state === "saved" ? "Saved. Your wallet uses the new limits now." : state === "error" ? "Couldn't save. Try again." : "Each change is signed into your ledger."}>
        <MandateSteppers m={m} set={set} hasSolar={!!info.roof} />
      </Section>

      <Section header="Trade with">
        <div className="p-3">
          <Segmented value={m.counterparties} onChange={(v) => set({ counterparties: v })}
            options={[{ value: "same_transformer", label: `My transformer (${info.transformer})` }, { value: "street", label: "Whole street" }]} />
        </div>
      </Section>

      {dirty && (
        <div className="mt-4 grid grid-cols-2 gap-2.5">
          <Button kind="gray" onClick={() => { setM(current); setState("idle"); }}>Undo</Button>
          <Button onClick={save} busy={state === "saving"}>Save</Button>
        </div>
      )}

      <NotificationsSection house={house} />

      <Section header="Your home">
        <Row icon={info.roof ? "sun" : "home"} iconBg={info.roof ? "var(--color-orange)" : "var(--color-blue)"}
          title={info.roof ? `${info.roof.kwp} kWp rooftop solar` : "No rooftop solar"}
          subtitle={info.roof ? `${info.subsidized ? "PM Surya Ghar" : "No subsidy"} · buyback ₹${info.buyback_rate?.toFixed(2)} · ${info.metering} meter` : "Your agent buys from neighbours' roofs"}
          onClick={onEditSetup} chevron last />
      </Section>

      <Section header="Say it in a sentence" footer="Coming next: type “don't buy above ₹5” and your agent proposes the limits.">
        <Row title="Rules from a sentence" value="Soon" last />
      </Section>

      <Section footer={`Weather: ${weather ?? "—"} · homes and meters simulated`}>
        <Row title="This phone is for" value={info.label} last />
      </Section>
      <Button kind="danger" className="mt-2 w-full" onClick={onSwitchHouse}>Use this phone for another house</Button>
    </Screen>
  );
}
