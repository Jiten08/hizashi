// Today: savings, live power, what needs the owner, the live block, the latest haggle, today's deals.
import { Ionicons } from "@expo/vector-icons";
import { Text, View } from "react-native";
import { ApprovalCard } from "../../components/ApprovalCard";
import { Card, Pill, Ring, Row, Screen, Section } from "../../components/ui";
import { blockIndex, blockLabel, hhmm, houseName, kwh, rupees } from "../../lib/format";
import { useHub } from "../../lib/store";
import { C, T } from "../../lib/theme";
import type { BlockState, Offer } from "../../lib/types";

const STEPS: { state: BlockState; label: string }[] = [
  { state: "PLANNED", label: "Planned" }, { state: "OPEN", label: "Deals" }, { state: "GATE_CLOSED", label: "Locked" },
  { state: "DELIVERING", label: "Live" }, { state: "SETTLED", label: "Settled" },
];

export default function Today() {
  const hub = useHub();
  const house = hub.conn!.house;
  const info = hub.houses[house];
  const sv = hub.savings[house];
  const live = hub.live[house];
  const pending = hub.approvals.filter((a) => a.house === house && a.status === "pending");
  const blocked = hub.blocked.filter((b) => b.house === house && b.owner_rule !== false).slice(-1);

  const entries = Object.entries(hub.blocks).sort(([a], [b]) => a.localeCompare(b));
  const cur = entries.find(([, s]) => s === "DELIVERING") ?? entries.find(([, s]) => s === "OPEN") ?? entries.find(([, s]) => s !== "SETTLED") ?? entries.at(-1);
  const curIndex = cur ? blockIndex(cur[0]) : null;
  const curStep = cur ? STEPS.findIndex((s) => s.state === cur[1]) : -1;
  const inBlock = hub.contracts.filter((c) => c.block.index === curIndex && (c.seller === house || c.buyer === house));

  const haggle: Offer[] = Object.values(hub.negotiations).filter((os) => os[0]?.to != null && os.some((o) => o.house === house || o.to === house)).at(-1) ?? [];
  const deal = haggle.length ? hub.contracts.find((c) => c.negotiation_id === haggle[0].negotiation_id) : undefined;
  const deals = hub.contracts.filter((c) => c.seller === house || c.buyer === house).sort((a, b) => b.block.index - a.block.index);

  const solar = live?.solar_kw ?? 0;
  const use = live?.use_kw ?? 0;
  const net = solar - use;
  const scale = Math.max(info?.roof?.kwp ?? 0, 3);

  return (
    <Screen title="Today" subtitle={`${houseName(house).toUpperCase()} · ${hhmm(hub.sim_time)}${hub.connected ? "" : " · OFFLINE"}`}>
      {/* Saved vs BESCOM */}
      <Card style={{ marginTop: 12 }}>
        <Text style={[T.footnote, { fontWeight: "600" }]}>SAVED VS BESCOM</Text>
        <Text style={[T.number, { fontSize: 52, fontWeight: "700", letterSpacing: -1, color: C.greenText, marginTop: 2 }]}>
          {rupees(sv?.saved_today ?? 0)}
        </Text>
        <Text style={T.subhead}>
          {sv && sv.projected_year > 0
            ? `≈ ₹${Math.round(sv.projected_year).toLocaleString("en-IN")} a year at today's pace`
            : info?.roof ? "Your first deal settles 15 minutes after its block." : "You save on every unit bought from a neighbour."}
        </Text>
        {sv && sv.trades > 0 ? (
          <View style={{ flexDirection: "row", marginTop: 14, paddingTop: 12, borderTopWidth: 0.5, borderTopColor: C.sep }}>
            <Mini label="Sold" value={kwh(sv.sold_kwh)} />
            <Mini label="Bought" value={kwh(sv.bought_kwh)} />
            <Mini label="Trades" value={String(sv.trades)} />
          </View>
        ) : null}
      </Card>

      {/* Live power */}
      <Card style={{ marginTop: 12, flexDirection: "row", alignItems: "center", gap: 18 }}>
        <Ring size={96} stroke={11} progress={solar / scale} color={C.orange}>
          <Ring size={70} stroke={11} progress={use / scale} color={C.blue} />
        </Ring>
        <View style={{ flex: 1, gap: 6 }}>
          <Legend color={C.orange} label="Solar" value={info?.roof ? `${solar.toFixed(2)} kW` : "none"} />
          <Legend color={C.blue} label="Using" value={`${use.toFixed(2)} kW`} />
          <Text style={[T.footnote, { fontWeight: "600", color: live?.outage ? C.label2 : net >= 0 ? C.greenText : C.blue }]}>
            {live?.outage ? "Grid outage" : !live ? "Waiting for the meter…" : net >= 0.05 ? `${net.toFixed(2)} kW spare for neighbours` : net <= -0.05 ? `${(-net).toFixed(2)} kW short` : "Balanced"}
          </Text>
        </View>
      </Card>

      {pending[0] ? <ApprovalCard approval={pending[0]} /> : null}

      {blocked.map((b, i) => (
        <View key={i} style={{ marginTop: 12, backgroundColor: C.redSoft, borderRadius: 12, padding: 14, flexDirection: "row", gap: 10 }}>
          <Ionicons name="shield" size={20} color={C.red} />
          <View style={{ flex: 1 }}>
            <Text style={[T.headline, { color: C.red }]}>Blocked by your wallet</Text>
            <Text style={[T.subhead, { color: C.label, marginTop: 2 }]}>{String(b.text ?? b.reason ?? "").replace(/^BLOCKED · /, "")}</Text>
          </View>
        </View>
      ))}

      {curIndex !== null ? (
        <Section header="Now">
          <View style={{ padding: 16 }}>
            <View style={{ flexDirection: "row", alignItems: "baseline", justifyContent: "space-between" }}>
              <Text style={[T.title2, T.number]}>{blockLabel(curIndex)}</Text>
              <Pill text={STEPS[curStep]?.label ?? ""} color={cur?.[1] === "DELIVERING" ? C.orange : C.label2}
                bg={cur?.[1] === "DELIVERING" ? C.orangeSoft : C.fill2} />
            </View>
            <View style={{ flexDirection: "row", gap: 4, marginTop: 12 }}>
              {STEPS.map((s, i) => (
                <View key={s.state} style={{ flex: 1 }}>
                  <View style={{ height: 4, borderRadius: 2, backgroundColor: i < curStep ? `${C.orange}80` : i === curStep ? C.orange : C.fill2 }} />
                  <Text style={[T.caption, { marginTop: 4, fontSize: 10, color: i === curStep ? C.label : C.label3 }]}>{s.label}</Text>
                </View>
              ))}
            </View>
          </View>
          {inBlock.map((c, i) => (
            <Row key={c.contract_id} last={i === inBlock.length - 1} title={c.seller === house ? `Selling to ${houseName(c.buyer)}` : `Buying from ${houseName(c.seller)}`}
              value={`${kwh(c.kwh)} · ${rupees(c.price)}`} />
          ))}
        </Section>
      ) : null}

      {haggle.length ? (
        <Section header="Latest haggle">
          <View style={{ padding: 16 }}>
            <Text style={T.subhead}>
              {haggle[0].house === house ? "Selling to" : "Buying from"} {houseName(haggle[0].house === house ? haggle[0].to : haggle[0].house)} · {blockLabel(haggle[0].block.index)}
            </Text>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
              {[...haggle].sort((a, b) => a.round - b.round || (a.side === "ask" ? -1 : 1)).map((o) => (
                <Pill key={o.offer_id} text={`${o.side === "ask" ? "Ask" : "Bid"} ${rupees(o.price)}`}
                  color={o.side === "ask" ? "#9A5B00" : C.blue} bg={o.side === "ask" ? C.orangeSoft : C.blueSoft} />
              ))}
              {deal ? <Pill text={`✓ Deal ${kwh(deal.kwh)} at ${rupees(deal.price)}`} color="#fff" bg={C.green} /> : null}
            </View>
          </View>
        </Section>
      ) : null}

      <Section header="Today's deals" footer={deals.length ? undefined : "Deals your agent books show up here."}>
        {deals.length ? deals.slice(0, 20).map((c, i) => {
          const selling = c.seller === house;
          const st = hub.settlements.find((x) => x.contract_id === c.contract_id);
          return (
            <Row key={c.contract_id} last={i === Math.min(deals.length, 20) - 1}
              icon={selling ? "sunny" : "home"} iconBg={selling ? C.orange : C.blue}
              title={`${selling ? "Sold to" : "Bought from"} ${houseName(selling ? c.buyer : c.seller)}`}
              subtitle={`${blockLabel(c.block.index)} · ${c.route === "auction" ? "auction" : "haggled"}${st ? (st.shortfall_kwh >= 0.005 ? ` · short ${st.shortfall_kwh.toFixed(2)} kWh` : " · settled") : ""}`}
              accessory={<View style={{ alignItems: "flex-end", marginLeft: 8 }}>
                <Text style={[T.headline, T.number]}>{kwh(c.kwh)}</Text>
                <Text style={[T.footnote, T.number]}>{rupees(c.price)}</Text>
              </View>} />
          );
        }) : <Row title="No deals yet" />}
      </Section>
    </Screen>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flex: 1 }}>
      <Text style={T.caption}>{label}</Text>
      <Text style={[T.headline, T.number]}>{value}</Text>
    </View>
  );
}

function Legend({ color, label, value }: { color: string; label: string; value: string }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: color }} />
      <Text style={[T.subhead, { flex: 1 }]}>{label}</Text>
      <Text style={[T.headline, T.number]}>{value}</Text>
    </View>
  );
}
