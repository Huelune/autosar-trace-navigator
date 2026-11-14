import { shownChildren, shownParent } from './treeLayout';
import { CodeAnchor, InvestigationStep, WorkspaceDocument } from '../domain/model';

export type TraceViewMode = 'path' | 'branches';
export type TraceEntry = { kind: 'goal' | 'step'; id: string } | { kind: 'group'; id: string; goalId: string; stepIds: string[] };
export const shortText = (text: string, length = 65): string => {
  const characters = [...text.replace(/\s+/g, ' ').trim()];
  return characters.length > length ? characters.slice(0, length - 1).join('') + '…' : characters.join('');
};
/** Display saved text, not an inferred/resolved function symbol. */
export const codeLabel = (step: InvestigationStep): string => shortText(step.snippet.split(/\r?\n/).find(line => line.trim()) ?? '코드 메모', 55);
export const sourceLabel = (anchor?: CodeAnchor): string => anchor?.relativePath
  ? `${anchor.relativePath.split('/').at(-1)}${anchor.range ? ':' + (anchor.range.start.line + 1) : ''}` : '파일 없는 메모';

/** Stored ancestry is preserved; this is the selected investigation path, never execution order. */
export function currentPath(document: WorkspaceDocument): InvestigationStep[] {
  const byId = new Map(document.steps.map(step => [step.id, step]));
  const path: InvestigationStep[] = [], seen = new Set<string>();
  for (let step = byId.get(document.currentStepId ?? ''); step && step.goalId === document.currentGoalId && !seen.has(step.id); step = byId.get(step.parentStepId ?? '')) {
    seen.add(step.id); path.push(step);
  }
  return path.reverse();
}

/** Presentation only: rows have a goal parent or one collapsible history-group parent. */
export class TracePresentation {
  private children = new Map<string, TraceEntry[]>();
  private parents = new Map<string, TraceEntry>();
  readonly path: InvestigationStep[];
  constructor(readonly document: WorkspaceDocument, readonly mode: TraceViewMode) {
    this.path = currentPath(document);
    if (mode === 'branches') { return; }
    for (const goal of document.goals) {
      const goalEntry: TraceEntry = { kind: 'goal', id: goal.id };
      const all = document.steps.filter(step => step.goalId === goal.id).sort((a, b) => a.sequence - b.sequence);
      const selected = this.path.at(-1);
      const next = all.filter(step => step.parentStepId === selected?.id);
      const rows = goal.id === document.currentGoalId && selected
        ? [...this.path, ...next]
        : all.filter(step => !step.parentStepId);
      const entries: TraceEntry[] = [];
      // The selected block stays visible; expanding other blocks does not change stored data or selection.
      for (let offset = 0; offset < rows.length; offset += 10) {
        const block = rows.slice(offset, offset + 10);
        const immediateChoice = mode === 'path' && next.length <= 10 && block.some(step => step.parentStepId === document.currentStepId);
        const group: TraceEntry | undefined = rows.length > 20 && !immediateChoice && !block.some(step => step.id === document.currentStepId)
          ? { kind: 'group', id: `history:${goal.id}:${block[0].id}:${block.at(-1)!.id}`, goalId: goal.id, stepIds: block.map(step => step.id) } : undefined;
        const items: TraceEntry[] = block.map(step => ({ kind: 'step', id: step.id }));
        if (group) { entries.push(group); this.children.set(group.id, items); this.parents.set(group.id, goalEntry); }
        else { entries.push(...items); }
        for (const item of items) { this.parents.set(item.id, group ?? goalEntry); }
      }
      this.children.set(goal.id, entries);
    }
  }
  getChildren(parent?: TraceEntry): TraceEntry[] {
    if (this.mode === 'branches') {
      if (!parent) { return this.document.goals.map(goal=>({kind:'goal',id:goal.id})); }
      return parent.kind === 'group' ? [] : shownChildren(this.document.steps,parent).map(step=>({kind:'step',id:step.id}));
    }
    return parent ? this.children.get(parent.id) ?? [] : this.document.goals.map(goal => ({ kind: 'goal', id: goal.id }));
  }
  getParent(entry: TraceEntry): TraceEntry | undefined {
    if (this.mode === 'branches') {
      const step=entry.kind==='step'?this.document.steps.find(step=>step.id===entry.id):undefined;
      return step?shownParent(this.document.steps,step):undefined;
    }
    return this.parents.get(entry.id);
  }
  /** Goal, current source and reason above the scrollable list. */
  get message(): string {
    const goal = this.document.goals.find(goal => goal.id === this.document.currentGoalId);
    if (!goal) { return '목표를 선택하거나 새 조사를 시작하세요.'; }
    const step = this.path.at(-1), count = this.document.steps.filter(s => s.goalId === goal.id).length;
    if (!step) { return `목표: ${shortText(goal.title, 55)}\n조사를 선택하세요 · 전체 ${count}단계`; }
    const anchor = this.document.anchors.find(anchor => anchor.id === step.codeAnchorId);
    return `목표: ${shortText(step.goalSnapshot.title, 55)}\n현재 #${step.sequence} · ${sourceLabel(anchor)} · 경로 ${this.path.length} / 전체 ${count}단계\n이유: ${shortText(step.reason, 85)}`;
  }
}
