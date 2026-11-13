import { InvestigationStep } from '../domain/model';

/** How the stored parent/child steps are laid out in the tree view. Display only: stored relations are not changed. */
export type LayoutStep = Pick<InvestigationStep, 'id' | 'goalId' | 'parentStepId' | 'sequence'>;
export interface LayoutParent { kind: 'goal' | 'step'; id: string }

// ponytail: each lookup scans all steps (fine for hundreds); build a parent->children map per refresh if trees reach thousands.
const childrenOf = (steps: readonly LayoutStep[], id: string): LayoutStep[] => steps.filter(s => s.parentStepId === id).sort((a, b) => a.sequence - b.sequence);
const rootsOf = (steps: readonly LayoutStep[], goalId: string): LayoutStep[] => steps.filter(s => s.goalId === goalId && !s.parentStepId).sort((a, b) => a.sequence - b.sequence);
/** A fork is a step with two or more children: its alternatives are listed one level deeper. */
export const forks = (steps: readonly LayoutStep[], id: string): boolean => childrenOf(steps, id).length >= 2;
/** The first step of one alternative: a child of a fork, or one of several first steps of a goal. It heads the group of its own route. */
export const startsBranch = (steps: readonly LayoutStep[], step: LayoutStep): boolean => step.parentStepId !== undefined ? forks(steps, step.parentStepId) : rootsOf(steps, step.goalId).length >= 2;

/** A step followed by its single-child descendants, ending at a leaf or at a fork. */
function run(steps: readonly LayoutStep[], start: LayoutStep): LayoutStep[] {
  const out = [start];
  for (let next = childrenOf(steps, start.id); next.length === 1; next = childrenOf(steps, next[0].id)) { out.push(next[0]); }
  return out;
}
/**
 * A single path stays on one level however long it is. Where the investigation forks, each alternative is its own group:
 * the fork lists only the first step of every alternative, and that first step holds the rest of its route.
 */
export function shownChildren(steps: readonly LayoutStep[], parent: LayoutParent): LayoutStep[] {
  if (parent.kind === 'goal') { const roots = rootsOf(steps, parent.id); return roots.length >= 2 ? roots : roots.flatMap(r => run(steps, r)); }
  if (forks(steps, parent.id)) { return childrenOf(steps, parent.id); }
  const head = steps.find(s => s.id === parent.id);
  return head && startsBranch(steps, head) ? run(steps, head).slice(1) : [];
}
/** The node a step is shown under: the fork (or goal) for the first step of an alternative, otherwise the first step of its own route. */
export function shownParent(steps: readonly LayoutStep[], step: LayoutStep): LayoutParent {
  const above = (s: LayoutStep): LayoutParent => s.parentStepId ? { kind: 'step', id: s.parentStepId } : { kind: 'goal', id: s.goalId };
  if (startsBranch(steps, step)) { return above(step); }
  let head = step;
  while (head.parentStepId && !startsBranch(steps, head)) { head = steps.find(x => x.id === head.parentStepId)!; }
  return startsBranch(steps, head) ? { kind: 'step', id: head.id } : { kind: 'goal', id: step.goalId };
}
/** Number of steps in the route that starts at this step, including every route that forks from it later. */
export function branchSize(steps: readonly LayoutStep[], id: string): number { return 1 + childrenOf(steps, id).reduce((n, c) => n + branchSize(steps, c.id), 0); }
/** Whether a step lies on the route that starts at head (head itself included). */
export function onBranch(steps: readonly LayoutStep[], headId: string, stepId: string | undefined): boolean {
  for (let s = steps.find(x => x.id === stepId); s; s = steps.find(x => x.id === s!.parentStepId)) { if (s.id === headId) { return true; } }
  return false;
}
