/**
 * First-run setup: solar or not, size and facing, PM Surya Ghar subsidy, meter, then the wallet's
 * limits. The hub previews the buyback rate and clear-day output; nothing is priced on the phone.
 * Finish = POST /api/houses/{h}/setup (+ PUT mandate if the limits changed).
 */
import { type ReactNode, useEffect, useState } from "react";
import { MandateSteppers } from "../components/MandateSteppers";
import { Button, Card, Icon, type IconName, IconTile, Section, Segmented, Stepper } from "../components/ui";
import { api } from "../lib/api";
import type { House, HouseInfo, Mandate, SetupBody, SetupResult } from "../lib/types";

type Step = "welcome" | "solar" | "system" | "subsidy" | "limits" | "review";
type Facing = SetupBody["facing"];

export default function Onboarding({ house, info, mandate, onDone, onCancel }: {
  house: House; info: HouseInfo; mandate: Mandate; onDone: () => void; onCancel?: () => void;
}) {
  const [step, setStep] = useState<Step>("welcome");
  const [hasSolar, setHasSolar] = useState(!!info.roof);
  const [kwp, setKwp] = useState(info.roof?.kwp ?? 3);
  const [facing, setFacing] = useState<Facing>(info.roof?.azimuth === 90 ? "east" : info.roof?.azimuth === 270 ? "west" : "south");
  const [subsidized, setSubsidized] = useState(!!info.subsidized);
  const [metering, setMetering] = useState<"net" | "gross">(info.metering === "gross" ? "gross" : "net");
  const [limits, setLimits] = useState<Mandate>(mandate);
  const [preview, setPreview] = useState<SetupResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const body: SetupBody = { has_solar: hasSolar, kwp, facing, subsidized, metering };
  useEffect(() => {
    const t = setTimeout(() => { api.setup(house, { ...body, preview: true }).then(setPreview).catch(() => {}); }, 200);
    return () => clearTimeout(t);
  }, [house, hasSolar, kwp, facing, subsidized, metering]);

  const steps: Step[] = hasSolar ? ["welcome", "solar", "system", "subsidy", "limits", "review"] : ["welcome", "solar", "limits", "review"];
  const at = steps.indexOf(step);
  const next = () => { setStep(steps[Math.min(at + 1, steps.length - 1)]); window.scrollTo(0, 0); };
  const back = () => (at === 0 ? onCancel?.() : setStep(steps[at - 1]));

  const finish = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.setup(house, body);
      if (JSON.stringify(limits) !== JSON.stringify(mandate)) await api.putMandate(house, limits);
      onDone();
    } catch (e) {
      setError((e as Error).message);
      setSaving(false);
    }
  };

  const t = preview?.tariffs;
  return (
    <div className="mx-auto flex min-h-dvh max-w-[560px] flex-col pt-[env(safe-area-inset-top)]">
      <header className="flex h-11 items-center px-2">
        <div className="w-20">
          {(at > 0 || onCancel) && (
            <button onClick={back} className="t-body flex items-center p-2 text-orange"><Icon name="back" className="h-6 w-6" strokeWidth={2.2} />Back</button>
          )}
        </div>
        <div className="flex flex-1 justify-center gap-1.5">
          {steps.map((s, i) => (
            <span key={s} className={`h-1.5 rounded-full transition-all ${i === at ? "w-[18px]" : "w-1.5"} ${i <= at ? "bg-orange" : "bg-label-3"}`} />
          ))}
        </div>
        <div className="w-20" />
      </header>

      <main key={step} className="rise flex-1 px-4 pb-6 pt-2">
        {step === "welcome" && (
          <>
            <p className="t-footnote font-semibold !text-orange">{info.label}</p>
            <h1 className="t-large mt-1">Your home gets its own energy agent</h1>
            <p className="t-body mt-2.5 text-label-2">Two minutes to set up. Then it trades with your neighbours every 15 minutes, inside limits only you can change.</p>
            <div className="mt-7 space-y-[22px]">
              <Point icon="swap" bg="var(--color-orange)" title="It haggles for you">Sells spare rooftop power, or buys a neighbour's, for less than BESCOM.</Point>
              <Point icon="shield" bg="var(--color-blue)" title="Your wallet says no">Anything outside your limits is refused before it's ever sent.</Point>
              <Point icon="trend" bg="var(--color-green)" title="You see what you saved">Every deal settles under KERC rules and shows against your BESCOM bill.</Point>
            </div>
          </>
        )}

        {step === "solar" && (
          <Question title="Do you have rooftop solar?" sub="Homes without solar save too: they buy neighbours' spare power below the BESCOM rate.">
            <Choice icon="sun" title="Yes, I have solar panels" hint="Sell what you don't use, buy when you're short" selected={hasSolar} onClick={() => setHasSolar(true)} />
            <Choice icon="home" title="No solar" hint="Buy from neighbours' roofs" selected={!hasSolar} onClick={() => setHasSolar(false)} />
          </Question>
        )}

        {step === "system" && (
          <Question title="About your panels" sub="It's on your installation papers or the inverter label.">
            <div className="overflow-hidden rounded-xl bg-card">
              <Stepper label="System size" value={kwp} step={0.5} min={1} max={10} onChange={setKwp} format={(v) => `${v.toFixed(1)} kWp`} last />
            </div>
            <p className="t-section ml-4 mt-3.5">Panels face</p>
            <Segmented value={facing} onChange={setFacing} options={[{ value: "south", label: "South" }, { value: "east", label: "East" }, { value: "west", label: "West" }]} />
            <Estimate preview={preview} />
          </Question>
        )}

        {step === "subsidy" && (
          <Question title="PM Surya Ghar subsidy?" sub="Subsidised systems get a lower BESCOM buyback rate, so selling to a neighbour is worth more to you.">
            <Choice icon="ribbon" title="Yes, subsidised" selected={subsidized} onClick={() => setSubsidized(true)}
              hint={t ? `BESCOM pays ₹${t.buyback.subsidized_upto_2kw.toFixed(2)} (up to 2 kW) or ₹${t.buyback.subsidized_above_2kw.toFixed(2)} per unit` : "Lower buyback rate"} />
            <Choice icon="cash" title="No subsidy" selected={!subsidized} onClick={() => setSubsidized(false)}
              hint={t ? `BESCOM pays ₹${t.buyback.unsubsidized.toFixed(2)} per unit` : "Standard buyback rate"} />
            <p className="t-section ml-4 mt-3.5">Meter</p>
            <Segmented value={metering} onChange={setMetering} options={[{ value: "net", label: "Net metering" }, { value: "gross", label: "Gross metering" }]} />
            <Estimate preview={preview} />
          </Question>
        )}

        {step === "limits" && (
          <Question title="Set your limits" sub="Your wallet signs nothing outside these. Change them any time in Rules.">
            <div className="overflow-hidden rounded-xl bg-card">
              <MandateSteppers m={limits} set={(p) => setLimits({ ...limits, ...p })} hasSolar={hasSolar} />
            </div>
          </Question>
        )}

        {step === "review" && (
          <Question title="All set?" sub="Your agent starts with the next 15-minute block.">
            <Section className="!mt-0">
              <Line k="Solar" v={hasSolar ? `${kwp.toFixed(1)} kWp, facing ${facing}` : "None"} />
              {hasSolar && <Line k="Subsidy" v={subsidized ? "PM Surya Ghar" : "None"} />}
              {hasSolar && <Line k="BESCOM buyback" v={preview?.house.buyback_rate != null ? `₹${preview.house.buyback_rate.toFixed(2)}` : "…"} />}
              {hasSolar && <Line k="Clear-day output" v={preview ? `≈ ${preview.clear_day_kwh} kWh` : "…"} />}
              {hasSolar && <Line k="Never sell below" v={`₹${limits.min_sell_price.toFixed(2)}`} />}
              <Line k="Never buy above" v={`₹${limits.max_buy_price.toFixed(2)}`} />
              <Line k="Daily budget" v={`₹${limits.daily_budget.toFixed(0)}`} />
              <Line k="Ask me above" v={`₹${limits.approve_above.toFixed(0)}`} last />
            </Section>
            {error && <p className="t-footnote !text-red">{error}</p>}
          </Question>
        )}
      </main>

      <div className="sticky bottom-0 bg-bg px-4 pb-[calc(12px+env(safe-area-inset-bottom))] pt-3">
        {step === "review"
          ? <Button className="w-full" onClick={finish} busy={saving}>Start trading</Button>
          : <Button className="w-full" onClick={next}>{step === "welcome" ? "Set up my home" : "Continue"}</Button>}
      </div>
    </div>
  );
}

function Point({ icon, bg, title, children }: { icon: IconName; bg: string; title: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3.5">
      <IconTile name={icon} bg={bg} size={40} />
      <div>
        <p className="t-headline">{title}</p>
        <p className="t-subhead mt-0.5">{children}</p>
      </div>
    </div>
  );
}

function Question({ title, sub, children }: { title: string; sub: string; children: ReactNode }) {
  return (
    <>
      <h1 className="t-large">{title}</h1>
      <p className="t-body mb-[22px] mt-2 text-label-2">{sub}</p>
      <div className="space-y-2.5">{children}</div>
    </>
  );
}

function Choice({ icon, title, hint, selected, onClick }: { icon: IconName; title: string; hint: string; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} aria-pressed={selected}
      className={`flex w-full items-center gap-3.5 rounded-[14px] border-2 bg-card p-3.5 text-left transition ${selected ? "border-orange" : "border-transparent"}`}>
      <IconTile name={icon} bg={selected ? "var(--color-orange)" : "#c7c7cc"} size={40} />
      <span className="flex-1">
        <span className="t-headline block">{title}</span>
        <span className="t-footnote mt-0.5 block">{hint}</span>
      </span>
      <span className={`inline-flex h-[26px] w-[26px] items-center justify-center rounded-full border-2 ${selected ? "border-orange bg-orange text-white" : "border-label-3"}`}>
        {selected && <Icon name="check" className="h-4 w-4" strokeWidth={3} />}
      </span>
    </button>
  );
}

function Estimate({ preview }: { preview: SetupResult | null }) {
  if (!preview?.house.roof) return null;
  return (
    <Card className="mt-1.5 flex items-center gap-3">
      <Icon name="sun" className="h-7 w-7 text-orange" strokeWidth={2} />
      <div>
        <p className="t-callout">About <b>{preview.clear_day_kwh} kWh</b> on a clear day</p>
        <p className="t-footnote">BESCOM buys yours at ₹{preview.house.buyback_rate?.toFixed(2)} · neighbours pay ~₹{preview.tariffs.expected_p2p_price.toFixed(2)}</p>
      </div>
    </Card>
  );
}

function Line({ k, v, last }: { k: string; v: string; last?: boolean }) {
  return (
    <div className="flex items-center pl-4">
      <div className={`flex flex-1 justify-between py-3 pr-4 ${last ? "" : "hairline"}`}>
        <span className="t-body">{k}</span>
        <span className="t-body num text-label-2">{v}</span>
      </div>
    </div>
  );
}
