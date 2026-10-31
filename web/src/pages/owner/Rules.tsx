// Rules tab: the wallet's limits (PUT = a new mandate version) and the home's setup.
import { Button, Card, Chip, Label, NumberField, Switch, TextArea } from "@heroui/react";
import { useEffect, useState } from "react";
import { Icon, SectionTitle } from "../../components/ui";
import { api } from "../../lib/api";
import type { House, Mandate } from "../../lib/types";
import { useHubStore } from "../../store/hub";

export function Money({ label, hint, value, onChange, step = 0.1, min = 0, max }: {
  label: string; hint: string; value: number; onChange: (v: number) => void; step?: number; min?: number; max?: number;
}) {
  return (
    <NumberField value={value} onChange={(v: number) => !Number.isNaN(v) && onChange(v)} minValue={min} maxValue={max} step={step}
      formatOptions={{ minimumFractionDigits: step < 1 ? 2 : 0, maximumFractionDigits: 2 }} className="w-full">
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <Label className="text-sm font-medium">{label}</Label>
          <p className="text-xs text-stone-500">{hint}</p>
        </div>
        <NumberField.Group className="w-36 shrink-0">
          <NumberField.DecrementButton />
          <NumberField.Input className="num text-center" />
          <NumberField.IncrementButton />
        </NumberField.Group>
      </div>
    </NumberField>
  );
}

export function MandateFields({ m, set, hasSolar }: { m: Mandate; set: (p: Partial<Mandate>) => void; hasSolar: boolean }) {
  return (
    <div className="space-y-4">
      {hasSolar && (
        <Money label="Never sell below (₹/unit)" hint="BESCOM would pay you your buyback rate instead."
          value={m.min_sell_price} onChange={(v) => set({ min_sell_price: v })} />
      )}
      <Money label="Never buy above (₹/unit)" hint="BESCOM charges ₹5.80; above that a deal saves nothing."
        value={m.max_buy_price} onChange={(v) => set({ max_buy_price: v })} />
      <Money label="Daily budget (₹)" hint="Most your agent may spend on neighbours' power in a day."
        value={m.daily_budget} onChange={(v) => set({ daily_budget: v })} step={5} />
      <Money label="Ask me above (₹)" hint="Buy plans worth more than this wait for your OK."
        value={m.approve_above} onChange={(v) => set({ approve_above: v })} step={1} />
      {hasSolar && (
        <Money label="Max promise per block (kWh)" hint="Caps each 15-minute promise, so a cloud can't cost much."
          value={m.max_promise_kwh} onChange={(v) => set({ max_promise_kwh: v })} step={0.1} min={0.1} max={5} />
      )}
    </div>
  );
}

export default function Rules({ house, onEditSetup }: { house: House; onEditSetup: () => void }) {
  const current = useHubStore((s) => s.mandates[house]);
  const info = useHubStore((s) => s.houses[house]);
  const [m, setM] = useState<Mandate | undefined>(current);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  useEffect(() => { setM(current); }, [current?.version]);       // a new version from the hub wins
  if (!m || !current) return null;
  const dirty = JSON.stringify(m) !== JSON.stringify(current);
  const set = (p: Partial<Mandate>) => { setM({ ...m, ...p }); setState("idle"); };
  const save = async () => {
    setState("saving");
    try {
      await api.putMandate(house, m);
      setState("saved");
    } catch {
      setState("error");
    }
  };

  return (
    <>
      <SectionTitle action={<Chip size="sm" variant="soft">v{current.version}</Chip>}>Your wallet's limits</SectionTitle>
      <Card>
        <Card.Content className="gap-5 p-4">
          <Switch isSelected={!m.paused} onChange={(on: boolean) => set({ paused: !on })}>
            <Switch.Content className="flex w-full items-center justify-between">
              <span>
                <Label className="text-sm font-medium">Trading on</Label>
                <span className="block text-xs text-stone-500">Off = the wallet refuses every offer.</span>
              </span>
              <Switch.Control><Switch.Thumb /></Switch.Control>
            </Switch.Content>
          </Switch>
          <MandateFields m={m} set={set} hasSolar={!!info?.roof} />
          <div>
            <p className="mb-2 text-sm font-medium">Trade with</p>
            <div className="grid grid-cols-2 gap-2">
              {(["same_transformer", "street"] as const).map((c) => (
                <button key={c} onClick={() => set({ counterparties: c })}
                  className={`rounded-xl border px-3 py-2.5 text-left text-sm transition ${m.counterparties === c ? "border-sun bg-sun-soft font-medium" : "border-stone-200 bg-white"}`}>
                  {c === "same_transformer" ? `My transformer (${info?.transformer})` : "Whole street"}
                  <span className="block text-xs font-normal text-stone-500">{c === "street" ? "Uses open access" : "Simplest, no extra charges"}</span>
                </button>
              ))}
            </div>
          </div>
        </Card.Content>
        <Card.Footer className="flex items-center gap-3 border-t border-stone-100 p-4">
          <span className="flex-1 text-sm text-stone-500">
            {state === "saved" ? "Saved. The wallet uses it now." : state === "error" ? "Couldn't save. Try again." : dirty ? "Unsaved changes" : "Signed into the ledger on save."}
          </span>
          <Button variant="secondary" isDisabled={!dirty} onPress={() => { setM(current); setState("idle"); }}>Undo</Button>
          <Button variant="primary" isDisabled={!dirty || state === "saving"} onPress={save}>Save</Button>
        </Card.Footer>
      </Card>

      <SectionTitle>Say it in a sentence</SectionTitle>
      <Card>
        <Card.Content className="gap-2 p-4">
          <TextArea disabled placeholder="“Don't buy above ₹5 and ask me before spending more than ₹20”" className="w-full" />
          <p className="text-xs text-stone-500">Coming next: your agent turns this into the limits above, and you confirm.</p>
        </Card.Content>
      </Card>

      <SectionTitle>Your home</SectionTitle>
      <Card>
        <Card.Content className="gap-3 p-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-sun-soft text-amber-700">
              <Icon name={info?.roof ? "sun" : "home"} />
            </span>
            <div className="flex-1 text-sm">
              <p className="font-medium">{info?.roof ? `${info.roof.kwp} kWp rooftop solar` : "No rooftop solar"}</p>
              <p className="text-stone-500">
                {info?.roof
                  ? `${info.subsidized ? "PM Surya Ghar subsidy" : "No subsidy"} · BESCOM buyback ₹${info.buyback_rate?.toFixed(2)} · ${info.metering} metering`
                  : "Your agent buys from neighbours' roofs."}
              </p>
            </div>
          </div>
          <Button variant="secondary" fullWidth onPress={onEditSetup}>Change setup</Button>
        </Card.Content>
      </Card>
    </>
  );
}
