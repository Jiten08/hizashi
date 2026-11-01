// "Say it in a sentence": the owner types a rule, the hub (Gemini, or a rule-based reader)
// proposes the changes, the owner checks them and taps Save. Nothing changes until Save.
import { useState } from "react";
import { api } from "../lib/api";
import type { House, MandateProposal } from "../lib/types";
import { Button, Icon, Row, Section } from "./ui";

const EXAMPLES = ["Don't buy above ₹5, ask me over ₹20", "Sell to anyone on the street, never below ₹4.50", "Pause trading"];

export function SayItRules({ house }: { house: House }) {
  const [text, setText] = useState("");
  const [proposal, setProposal] = useState<MandateProposal | null>(null);
  const [busy, setBusy] = useState<"parse" | "save" | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const parse = async (t = text) => {
    if (!t.trim()) return;
    setText(t);
    setBusy("parse");
    setMsg(null);
    setProposal(null);
    try {
      const p = await api.parseMandate(house, t);
      if (p.changes.length) setProposal(p); else setMsg(p.note);
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  const save = async () => {
    if (!proposal) return;
    setBusy("save");
    try {
      await api.putMandate(house, proposal.mandate);
      setProposal(null);
      setText("");
      setMsg("Saved. Your wallet uses the new limits now.");
      navigator.vibrate?.(15);
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Section header="Say it in a sentence"
      footer={msg ?? (proposal ? proposal.note : "Your agent only proposes; nothing changes until you tap Save.")}>
      <div className="p-3">
        <div className="flex items-center gap-2">
          <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && parse()}
            placeholder="e.g. don't buy above ₹5" enterKeyHint="go"
            className="t-body h-11 min-w-0 flex-1 rounded-[10px] bg-fill px-3 outline-none placeholder:text-label-3" />
          <Button className="!h-11 shrink-0" onClick={() => parse()} busy={busy === "parse"} disabled={!text.trim()}>
            <Icon name="chevron" className="h-5 w-5" strokeWidth={2.6} />
          </Button>
        </div>
        {!proposal && !text && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {EXAMPLES.map((x) => (
              <button key={x} onClick={() => parse(x)} className="rounded-full bg-orange-soft px-2.5 py-1 text-[13px] text-orange-ink active:opacity-60">{x}</button>
            ))}
          </div>
        )}
      </div>
      {proposal && (
        <>
          {proposal.changes.map((c) => (
            <Row key={c.field} title={c.label}
              accessory={<span className="t-body num ml-2 whitespace-nowrap"><span className="text-label-3 line-through">{c.from}</span> <span className="font-semibold">{c.to}</span></span>} />
          ))}
          <div className="grid grid-cols-2 gap-2.5 p-3">
            <Button kind="gray" onClick={() => setProposal(null)}>Cancel</Button>
            <Button onClick={save} busy={busy === "save"}>Save</Button>
          </div>
          <p className="t-caption px-4 pb-3">{proposal.source === "gemini" ? "Read by Gemini" : "Read without the LLM"} · checked by your wallet</p>
        </>
      )}
    </Section>
  );
}
