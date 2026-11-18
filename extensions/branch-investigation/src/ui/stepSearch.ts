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
    const notes = ([['가정', s.hypothesis], ['필요 조건', s.requiredConditions], ['도출 조건', s.derivedConditions], ['관찰', s.observation], ['결과', s.result], ['다음 할 일', s.nextAction]] as const).filter(([, text]) => text.trim()).map(([name, text]) => `${name}: ${oneLine(text)}`);
    // ponytail: only the first 1,000 characters of the notes and code are searchable; search the document itself if longer notes must be found.
    return { label: `${s.sequence}. ${oneLine(s.reason)}`, description: `${statusLabels[s.status]} · ${goals.get(s.goalId)?.title ?? ''}${where}`, detail: [...notes, `코드: ${oneLine(s.snippet)}`].join(' | ').slice(0, 1000), stepId: s.id };
  });
}
