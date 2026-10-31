"""A2A server side: answer incoming asks (section 7.3).

Phase 0: politely refuses every ask with {"type": "refuse", "reason": "not trading yet"}.
Trap (7.1): the executor must enqueue a Task before any status update.
Real negotiation logic: TODO(R1.5, Anurag).
"""
import logging

from a2a.helpers import get_data_parts, new_data_message, new_task
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Role, TaskState

log = logging.getLogger("hizashi.agent.executor")


class HouseExecutor(AgentExecutor):
    def __init__(self, house: str) -> None:
        self.house = house

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.current_task is None:
            await event_queue.enqueue_event(
                new_task(
                    context.task_id,
                    context.context_id,
                    TaskState.TASK_STATE_SUBMITTED,
                    history=[context.message],
                )
            )
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        data = get_data_parts(context.message.parts)
        log.info("%s got %s", self.house, data[0] if data else "(no data)")
        reply = {"type": "refuse", "reason": "not trading yet"}
        await updater.reject(self._msg(reply, context))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()

    @staticmethod
    def _msg(data: dict, context: RequestContext) -> Message:
        return new_data_message(
            data, context_id=context.context_id, task_id=context.task_id, role=Role.ROLE_AGENT
        )
