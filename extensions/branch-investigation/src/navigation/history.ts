import { id, now, WorkspaceDocument, Visit } from '../domain/model';
import { MAX_HISTORY } from '../domain/validation';
export function visit(d: WorkspaceDocument, to: Visit, action: 'select_step' | 'open_source' | 'back' | 'forward'): void {
  const from = d.visits[d.visitCursor];
  if (action === 'select_step') {
    d.visits = d.visits.slice(0, d.visitCursor + 1); d.visits.push(to);
    if (d.visits.length > MAX_HISTORY) { d.visits.shift(); } d.visitCursor = d.visits.length - 1;
  }
  d.navigationEvents.push({ id: id(), goalId: to.goalId, stepId: to.stepId, fromAnchorId: from?.anchorId, toAnchorId: to.anchorId, action, createdAt: now() });
  d.navigationEvents = d.navigationEvents.slice(-MAX_HISTORY); d.currentGoalId = to.goalId; d.currentStepId = to.stepId;
}
