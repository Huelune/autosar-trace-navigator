import { InvestigationStep } from '../domain/model';

/** How the stored parent/child steps are laid out in the tree view. Display only: stored relations are not changed. */
export type LayoutStep = Pick<InvestigationStep, 'id' | 'goalId' | 'parentStepId' | 'sequence'>;
export interface LayoutParent { kind: 'goal' | 'step'; id: string }

// ponytail: each lookup scans all steps (fine for hundreds); build a parent->children map per refresh if trees reach thousands.
const childrenOf = (steps: readonly LayoutStep[], id: string): LayoutStep[] => steps.filter(s => s.parentStepId === id).sort((a, b) => a.sequence - b.sequence);
/** A fork is a step with two or more children: the only place where the view indents. */
export const forks = (steps: readonly LayoutStep[], id: string): boolean => childrenOf(steps, id).length >= 2;
/** The first step of one alternative under a fork. */
export const startsBranch = (steps: readonly LayoutStep[], step: LayoutStep): boolean => step.parentStepId !== undefined && forks(steps, step.parentStepId);

/** A step followed by its single-child descendants, ending at a leaf or at a fork. */
function run(steps: readonly LayoutStep[], start: LayoutStep): LayoutStep[] {
  const out = [start];
  for (let next = childrenOf(steps, start.id); next.length === 1; next = childrenOf(steps, next[0].id)) { out.push(next[0]); }
  return out;
}
/** A single path stays on one level however long it is; only a fork puts its alternatives one level deeper. */
export function shownChildren(steps: readonly LayoutStep[], parent: LayoutParent): LayoutStep[] {
  if (parent.kind === 'step' && !forks(steps, parent.id)) { return []; }
  const heads = parent.kind === 'goal' ? steps.filter(s => s.goalId === parent.id && !s.parentStepId).sort((a, b) => a.sequence - b.sequence) : childrenOf(steps, parent.id);
  return heads.flatMap(head => run(steps, head));
}
/** The node a step is shown under: the nearest fork above it, or the goal. */
export function shownParent(steps: readonly LayoutStep[], step: LayoutStep): LayoutParent {
  for (let s: LayoutStep | undefined = step; s?.parentStepId; s = steps.find(x => x.id === s!.parentStepId)) {
    if (forks(steps, s.parentStepId)) { return { kind: 'step', id: s.parentStepId }; }
  }
  return { kind: 'goal', id: step.goalId };
}
