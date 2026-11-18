import { statusLabels, WorkspaceDocument } from '../domain/model';

export interface StepSearchItem { label: string; description: string; detail: string; stepId: string }
const oneLine = (text: string): string => text.replace(/\s+/g, ' ').trim();
/**
 * One row per step of every goal for a quick pick, which filters on label, description and detail as the user types.
 * The status name sits in the description, so typing a status keeps the steps in that status.
 */
export function stepSearchItems(d: WorkspaceDocument): StepSearchItem[] {
  const goals = new Map(d.goals.map((g, order) => [g.id, { title: g.title, order }])), anchors = new Map(d.anchors.map(a => [a.id, a]));
  return [...d.steps].sort((a, b) => (goals.get(a.goalId)?.order ?? 0) - (goals.get(b.goalId)?.order ?? 0) || a.sequence - b.sequence).map(s => {
    const anchor = anchors.get(s.codeAnchorId), where = anchor?.relativePath ? ` · ${anchor.relativePath}${anchor.range ? `:${anchor.range.start.line + 1}` : ''}` : '';
    const notes = ([['메모', s.memo ?? ''], ['가정', s.hypothesis], ['필요 조건', s.requiredConditions], ['도출 조건', s.derivedConditions], ['관찰', s.observation], ['결과', s.result], ['다음 할 일', s.nextAction]] as const).filter(([, text]) => text.trim()).map(([name, text]) => `${name}: ${oneLine(text)}`);
    // ponytail: only the first 1,000 characters of the notes and code are searchable; search the document itself if longer notes must be found.
    return { label: `${s.sequence}. ${oneLine(s.reason)}`, description: `${statusLabels[s.status]} · ${goals.get(s.goalId)?.title ?? ''}${where}`, detail: [...notes, `코드: ${oneLine(s.snippet)}`].join(' | ').slice(0, 1000), stepId: s.id };
  });
}

const openKinds = { deferred: '보류', next: '다음 할 일 있음', end: '갈래 끝 (조사 중)' } as const;
/**
 * Where the investigation is still open, from what is already recorded: deferred steps, steps under investigation that carry a next action,
 * and route ends still under investigation. Nothing new is stored. The current goal comes first, then deferred, next action, route end.
 */
export function openItems(d: WorkspaceDocument): StepSearchItem[] {
  const rows = new Map(stepSearchItems(d).map(r => [r.stepId, r])), parents = new Set(d.steps.map(s => s.parentStepId)), order = Object.keys(openKinds);
  const kind = (s: WorkspaceDocument['steps'][number]): keyof typeof openKinds | undefined => s.status === 'deferred' ? 'deferred' : s.status !== 'investigating' ? undefined : s.nextAction.trim() ? 'next' : parents.has(s.id) ? undefined : 'end';
  const goalOrder = (goalId: string): number => goalId === d.currentGoalId ? -1 : d.goals.findIndex(g => g.id === goalId);
  return d.steps.flatMap(s => { const k = kind(s); return k ? [{ s, k }] : []; })
    .sort((a, b) => goalOrder(a.s.goalId) - goalOrder(b.s.goalId) || order.indexOf(a.k) - order.indexOf(b.k) || a.s.sequence - b.s.sequence)
    .map(({ s, k }) => { const row = rows.get(s.id)!, notes = ([['다음 할 일', s.nextAction], ['필요 조건', s.requiredConditions], ['결과', s.result]] as const).filter(([, text]) => text.trim()).map(([name, text]) => `${name}: ${oneLine(text)}`);
      return { stepId: s.id, label: `${s.id === d.currentStepId ? '▶ ' : ''}${row.label}`, description: [openKinds[k], ...row.description.split(' · ').slice(1)].join(' · '), detail: (notes.join(' | ') || '다음 할 일을 적지 않았습니다.').slice(0, 1000) }; });
}
