/**
 * First-run setup for a home: solar or not, system size and facing, PM Surya Ghar subsidy,
 * then the wallet's limits. The hub previews the result (buyback rate, clear-day output),
 * so no tariff is computed here. Finish = POST /api/houses/{h}/setup + PUT mandate.
 */
import { Button, Card, Chip, Label, ProgressBar, Slider, Spinner } from "@heroui/react";
import { type ReactNode, useEffect, useState } from "react";
import { Icon, type IconName, SunMark } from "../components/ui";
import { api } from "../lib/api";
import type { House, HouseInfo, Mandate, SetupBody, SetupResult } from "../lib/types";
import { MandateFields } from "./owner/Rules";

type Step = "welcome" | "solar" | "system" | "subsidy" | "limits" | "review";
type Facing = SetupBody["facing"];

const FACING: { id: Facing; label: string; hint: string }[] = [
  { id: "south", label: "South", hint: "Most energy over the day" },
  { id: "east", label: "East", hint: "Strong mornings" },
  { id: "west", label: "West", hint: "Strong evenings" },
];

function facingOf(info: HouseInfo): Facing {
  const az = info.roof?.azimuth ?? 180;
  return az === 90 ? "east" : az === 270 ? "west" : az === 0 ? "north" : "south";
}

export default function Onboarding({ house, info, mandate, onDone, onCancel }: {
  house: House; info: HouseInfo; mandate: Mandate; onDone: () => void; onCancel?: () => void;
}) {
  const [step, setStep] = useState<Step>("welcome");
  const [hasSolar, setHasSolar] = useState<boolean>(!!info.roof);
  const [kwp, setKwp] = useState<number>(info.roof?.kwp ?? 3);
  const [facing, setFacing] = useState<Facing>(facingOf(info));
  const [subsidized, setSubsidized] = useState<boolean>(!!info.subsidized);
  const [metering, setMetering] = useState<"net" | "gross">(info.metering === "gross" ? "gross" : "net");
  const [limits, setLimits] = useState<Mandate>(mandate);
  const [preview, setPreview] = useState<SetupResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const body: SetupBody = { has_solar: hasSolar, kwp, facing, subsidized, metering };
  useEffect(() => {
    const t = setTimeout(() => {
      api.setup(house, { ...body, preview: true }).then(setPreview).catch(() => setPreview(null));
    }, 200);
    return () => clearTimeout(t);
  }, [house, hasSolar, kwp, facing, subsidized, metering]);

  const steps: Step[] = hasSolar
    ? ["welcome", "solar", "system", "subsidy", "limits", "review"]
    : ["welcome", "solar", "limits", "review"];
  const at = steps.indexOf(step);
  const next = () => setStep(steps[Math.min(at + 1, steps.length - 1)]);
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

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pb-8 pt-5">
      <div className="flex items-center gap-3">
        {(at > 0 || onCancel) ? (
          <Button isIconOnly variant="ghost" size="sm" aria-label="Back" onPress={back}><Icon name="back" /></Button>
        ) : <SunMark className="h-8 w-8" />}
        <ProgressBar aria-label="Setup progress" value={((at + 1) / steps.length) * 100} className="flex-1" size="sm" color="accent">
          <ProgressBar.Track><ProgressBar.Fill /></ProgressBar.Track>
        </ProgressBar>
        <span className="num w-10 text-right text-xs text-stone-500">{at + 1}/{steps.length}</span>
      </div>

      <div key={step} className="pop-in flex flex-1 flex-col pt-8">
        {step === "welcome" && (
          <>
            <Chip size="sm" variant="soft" color="accent" className="self-start">{info.label}</Chip>
            <h1 className="mt-3 text-3xl font-bold leading-tight">Your home gets its own energy agent.</h1>
            <p className="mt-2 text-stone-600">Two minutes to set up. Then it trades with your neighbours every 15 minutes, inside limits only you can change.</p>
            <ul className="mt-6 space-y-3">
              <Point icon="hand" title="It haggles for you">Sells spare rooftop power, or buys a neighbour's, for less than BESCOM.</Point>
              <Point icon="shield" title="Your wallet says no">Anything outside your limits is refused before it's ever sent.</Point>
              <Point icon="rupee" title="You see what you saved">Every deal is settled under KERC rules and shown against your BESCOM bill.</Point>
            </ul>
          </>
        )}

        {step === "solar" && (
          <Question title="Do you have rooftop solar?" sub="Homes without solar save too: they buy neighbours' spare power below the BESCOM rate.">
            <Choice icon="sun" selected={hasSolar} onPress={() => setHasSolar(true)} title="Yes, I have solar panels" hint="Sell what you don't use, buy when you're short" />
            <Choice icon="home" selected={!hasSolar} onPress={() => setHasSolar(false)} title="No solar" hint="Buy from neighbours' roofs" />
          </Question>
        )}

        {step === "system" && (
          <Question title="Tell us about your panels" sub="It's on your installation papers or the inverter label.">
            <Card>
              <Card.Content className="gap-3 p-4">
                <Slider value={kwp} onChange={(v) => setKwp(Array.isArray(v) ? v[0] : v)} minValue={1} maxValue={10} step={0.5} className="w-full">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm font-medium">System size</Label>
                    <span className="num text-lg font-semibold">{kwp.toFixed(1)} kWp</span>
                  </div>
                  <Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track>
                </Slider>
              </Card.Content>
            </Card>
            <p className="mt-2 text-sm font-medium">Which way do they face?</p>
            <div className="grid grid-cols-3 gap-2">
              {FACING.map((f) => (
                <button key={f.id} onClick={() => setFacing(f.id)}
                  className={`rounded-2xl border p-3 text-left transition ${facing === f.id ? "border-sun bg-sun-soft ring-2 ring-sun/30" : "border-stone-200 bg-white"}`}>
                  <p className="font-semibold">{f.label}</p>
                  <p className="text-[11px] leading-tight text-stone-500">{f.hint}</p>
                </button>
              ))}
            </div>
            <Estimate preview={preview} />
          </Question>
        )}

        {step === "subsidy" && (
          <Question title="Did you get the PM Surya Ghar subsidy?" sub="Subsidised systems get a lower BESCOM buyback rate, so selling to a neighbour is worth more to you.">
            <Choice icon="sparkle" selected={subsidized} onPress={() => setSubsidized(true)} title="Yes, subsidised"
              hint={preview?.tariffs ? `BESCOM pays ₹${preview.tariffs.buyback.subsidized_upto_2kw.toFixed(2)} (up to 2 kW) or ₹${preview.tariffs.buyback.subsidized_above_2kw.toFixed(2)}/unit for export` : "Lower buyback rate"} />
            <Choice icon="rupee" selected={!subsidized} onPress={() => setSubsidized(false)} title="No subsidy"
              hint={preview?.tariffs ? `BESCOM pays ₹${preview.tariffs.buyback.unsubsidized.toFixed(2)}/unit for export` : "Standard buyback rate"} />
            <p className="mt-2 text-sm font-medium">Meter</p>
            <div className="grid grid-cols-2 gap-2">
              {(["net", "gross"] as const).map((m) => (
                <button key={m} onClick={() => setMetering(m)}
                  className={`rounded-2xl border px-3 py-2.5 text-left text-sm transition ${metering === m ? "border-sun bg-sun-soft font-medium" : "border-stone-200 bg-white"}`}>
                  {m === "net" ? "Net metering" : "Gross metering"}
                  <span className="block text-xs font-normal text-stone-500">{m === "net" ? "One meter, both ways" : "Separate export meter"}</span>
                </button>
              ))}
            </div>
            <Estimate preview={preview} />
          </Question>
        )}

        {step === "limits" && (
          <Question title="Set your limits" sub="Your wallet signs nothing outside these. You can change them any time in Rules.">
            <Card><Card.Content className="p-4"><MandateFields m={limits} set={(p) => setLimits({ ...limits, ...p })} hasSolar={hasSolar} /></Card.Content></Card>
          </Question>
        )}

        {step === "review" && (
          <Question title="All set?" sub="Your agent starts with the next 15-minute block.">
            <Card>
              <Card.Content className="divide-y divide-stone-100 p-0 text-sm">
                <Row k="Solar" v={hasSolar ? `${kwp.toFixed(1)} kWp, facing ${facing}` : "None, buying from neighbours"} />
                {hasSolar && <Row k="Subsidy" v={subsidized ? "PM Surya Ghar" : "None"} />}
                {hasSolar && <Row k="BESCOM buyback" v={preview ? `₹${preview.house.buyback_rate?.toFixed(2)}/unit` : "…"} />}
                {hasSolar && <Row k="Clear-day output" v={preview ? `≈ ${preview.clear_day_kwh} kWh` : "…"} />}
                {hasSolar && <Row k="Never sell below" v={`₹${limits.min_sell_price.toFixed(2)}`} />}
                <Row k="Never buy above" v={`₹${limits.max_buy_price.toFixed(2)}`} />
                <Row k="Daily budget" v={`₹${limits.daily_budget.toFixed(0)}`} />
                <Row k="Ask me above" v={`₹${limits.approve_above.toFixed(0)}`} />
              </Card.Content>
            </Card>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </Question>
        )}
      </div>

      <div className="pt-6">
        {step === "review" ? (
          <Button variant="primary" size="lg" fullWidth onPress={finish} isDisabled={saving}>
            {saving ? <Spinner size="sm" color="current" /> : <>Start trading <Icon name="arrow" className="h-4 w-4" /></>}
          </Button>
        ) : (
          <Button variant="primary" size="lg" fullWidth onPress={next}>
            {step === "welcome" ? "Set up my home" : "Continue"} <Icon name="arrow" className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}

function Point({ icon, title, children }: { icon: IconName; title: string; children: ReactNode }) {
  return (
    <li className="flex gap-3 rounded-2xl bg-white p-4 ring-1 ring-black/5">
      <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sun-soft text-amber-700"><Icon name={icon} /></span>
      <span>
        <span className="block font-semibold">{title}</span>
        <span className="block text-sm text-stone-600">{children}</span>
      </span>
    </li>
  );
}

function Question({ title, sub, children }: { title: string; sub: string; children: ReactNode }) {
  return (
    <>
      <h1 className="text-2xl font-bold leading-tight">{title}</h1>
      <p className="mt-1.5 text-stone-600">{sub}</p>
      <div className="mt-6 space-y-3">{children}</div>
    </>
  );
}

function Choice({ icon, title, hint, selected, onPress }: { icon: IconName; title: string; hint: string; selected: boolean; onPress: () => void }) {
  return (
    <button onClick={onPress} aria-pressed={selected}
      className={`flex w-full items-center gap-4 rounded-2xl border p-4 text-left transition ${selected ? "border-sun bg-sun-soft ring-2 ring-sun/30" : "border-stone-200 bg-white hover:border-stone-300"}`}>
      <span className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${selected ? "bg-sun text-white" : "bg-stone-100 text-stone-600"}`}>
        <Icon name={icon} />
      </span>
      <span className="flex-1">
        <span className="block font-semibold">{title}</span>
        <span className="block text-sm text-stone-600">{hint}</span>
      </span>
      <span className={`inline-flex h-6 w-6 items-center justify-center rounded-full border-2 ${selected ? "border-sun bg-sun text-white" : "border-stone-300"}`}>
        {selected && <Icon name="check" className="h-3.5 w-3.5" strokeWidth={3} />}
      </span>
    </button>
  );
}

function Estimate({ preview }: { preview: SetupResult | null }) {
  if (!preview?.house.roof) return null;
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-ink p-4 text-white">
      <Icon name="sun" className="h-6 w-6 text-amber-300" />
      <div className="flex-1 text-sm">
        <p>On a clear day: <b className="num">≈ {preview.clear_day_kwh} kWh</b></p>
        <p className="text-white/70">BESCOM buyback <b className="num text-white">₹{preview.house.buyback_rate?.toFixed(2)}</b>/unit · neighbours pay ~₹{preview.tariffs.expected_p2p_price.toFixed(2)}</p>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <span className="text-stone-500">{k}</span>
      <span className="num font-medium">{v}</span>
    </div>
  );
}
