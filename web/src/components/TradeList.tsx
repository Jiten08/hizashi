// Today's contracts for one house, newest block first, with their settlement once it lands.
import { Card, Chip } from "@heroui/react";
import { blockLabel, rupees } from "../lib/api";
import type { Contract, House, Settlement } from "../lib/types";
import { Empty, Icon } from "./ui";

export function TradeList({ house, contracts, settlements }: { house: House; contracts: Contract[]; settlements: Settlement[] }) {
  const mine = contracts
    .filter((c) => c.seller === house || c.buyer === house)
    .sort((a, b) => b.block.index - a.block.index);
  if (!mine.length) return <Empty icon="hand" title="No deals yet today">Deals your agent books show up here.</Empty>;
  return (
    <Card>
      <Card.Content className="p-0">
        <ul className="divide-y divide-stone-100">
          {mine.map((c) => {
            const s = settlements.find((x) => x.contract_id === c.contract_id);
            const selling = c.seller === house;
            const other = (selling ? c.buyer : c.seller).replace("h", "House ");
            return (
              <li key={c.contract_id} className="flex items-center gap-3 px-4 py-3">
                <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${selling ? "bg-sun-soft text-amber-700" : "bg-sky-50 text-sky-700"}`}>
                  <Icon name={selling ? "sun" : "home"} className="h-4.5 w-4.5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{selling ? "Sold to" : "Bought from"} {other}</p>
                  <p className="num text-xs text-stone-500">
                    {blockLabel(c.block.index)} · {c.route === "auction" ? "auction" : "haggled"}{c.open_access ? " · open access" : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="num text-sm font-semibold">{c.kwh.toFixed(2)} kWh</p>
                  <p className="num text-xs text-stone-500">at {rupees(c.price)}</p>
                </div>
                {s ? (
                  s.shortfall_kwh > 0
                    ? <Chip size="sm" variant="soft" color="danger">short</Chip>
                    : <Chip size="sm" variant="soft" color="success">settled</Chip>
                ) : <Chip size="sm" variant="soft">booked</Chip>}
              </li>
            );
          })}
        </ul>
      </Card.Content>
    </Card>
  );
}
