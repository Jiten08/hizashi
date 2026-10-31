// Approvals tab: what's waiting, then everything decided today.
import { Card, Chip } from "@heroui/react";
import { ApprovalCard } from "../../components/ApprovalCard";
import { Empty, SectionTitle } from "../../components/ui";
import { hhmm } from "../../lib/api";
import type { House } from "../../lib/types";
import { useHubStore } from "../../store/hub";

const COLOR = { approved: "success", declined: "danger", expired: "default", pending: "warning" } as const;

export default function Approvals({ house }: { house: House }) {
  const approvals = useHubStore((s) => s.approvals).filter((a) => a.house === house);
  const pending = approvals.filter((a) => a.status === "pending");
  const done = approvals.filter((a) => a.status !== "pending").reverse();
  return (
    <>
      <SectionTitle>Waiting for you</SectionTitle>
      {pending.length
        ? <div className="space-y-3">{pending.map((a) => <ApprovalCard key={a.approval_id} approval={a} />)}</div>
        : <Empty icon="check" title="Nothing to approve">Big buy plans over your limit will ask here first.</Empty>}

      <SectionTitle>Decided</SectionTitle>
      {done.length ? (
        <Card>
          <Card.Content className="p-0">
            <ul className="divide-y divide-stone-100">
              {done.map((a) => (
                <li key={a.approval_id} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{a.summary}</p>
                    <p className="text-xs text-stone-500">asked {hhmm(a.created_at)}</p>
                  </div>
                  <Chip size="sm" variant="soft" color={COLOR[a.status]}>{a.status}</Chip>
                </li>
              ))}
            </ul>
          </Card.Content>
        </Card>
      ) : <p className="px-1 text-sm text-stone-500">No decisions yet today.</p>}
    </>
  );
}
