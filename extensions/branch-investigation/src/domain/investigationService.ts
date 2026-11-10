import { CapturedCode, clone, CodeAnchor, Evidence, fingerprint, id, InvestigationStep, now, Status, WorkspaceDocument } from './model';
import { nonempty, requireValue, validate, validStatus } from './validation';
import { visit } from '../navigation/history';
export interface InvestigationRepository { save(d: WorkspaceDocument, expected: number): Promise<WorkspaceDocument> }
export interface GoalInput { title: string; description: string }
export type StepEdit = Pick<InvestigationStep, 'reason'|'hypothesis'|'observation'|'requiredConditions'|'derivedConditions'|'result'|'nextAction'|'status'>;
/** Pure investigation domain, independent of VS Code and the Python parser. */
export class InvestigationService {
  private value: WorkspaceDocument; private queue: Promise<unknown> = Promise.resolve();
  dirty = false; error?: string; onChange: () => void = () => {};
  constructor(document: WorkspaceDocument, private readonly repository: InvestigationRepository) { validate(document); this.value = clone(document); }
  get document(): WorkspaceDocument { return clone(this.value); }
  async whenIdle(): Promise<void> { await this.queue; }
  private enqueue<T>(fn: () => Promise<T>): Promise<T> { const p = this.queue.then(fn); this.queue = p.catch(() => {}); return p; }
  private async change<T>(fn: (d: WorkspaceDocument) => T): Promise<T> {
    return this.enqueue(async () => { requireValue(!this.dirty, '저장하지 못한 변경이 있습니다. 먼저 저장을 재시도하세요.'); const draft = clone(this.value), result = fn(draft); validate(draft); this.value = draft; this.dirty = true; this.onChange(); await this.persist(); return result; });
  }
  private async persist(): Promise<void> { try { this.value = await this.repository.save(this.value, this.value.revision); this.dirty = false; this.error = undefined; } catch (e) { this.error = (e as Error).message; throw e; } finally { this.onChange(); } }
  retrySave(): Promise<void> { return this.enqueue(async () => { if (this.dirty) { await this.persist(); } }); }
  private anchor(d: WorkspaceDocument, capture: CapturedCode): CodeAnchor {
    const fp = fingerprint(capture.snippet), key = capture.fileUri && capture.range ? fingerprint(JSON.stringify([d.repositoryId, capture.fileUri, capture.range, fp])) : `manual:${id()}`;
    let node = d.codeNodes.find(n => n.identityKey === key); if (!node) { node = { id: id(), repositoryId: d.repositoryId, identityKey: key }; d.codeNodes.push(node); }
    const anchor: CodeAnchor = { id: id(), codeNodeId: node.id, fileUri: capture.fileUri, relativePath: capture.relativePath, documentVersion: capture.documentVersion, range: clone(capture.range), textFingerprint: fp, contextBefore: capture.contextBefore, contextAfter: capture.contextAfter, state: capture.fileUri ? 'linked' : 'snippet_only' };
    d.anchors.push(anchor); return anchor;
  }
  private goal(d: WorkspaceDocument, input: GoalInput, capture: CapturedCode): string { nonempty(input.title, 200); const anchor = this.anchor(d, capture), time = now(), goalId = id(); d.goals.push({ id: goalId, title: input.title.trim(), description: input.description, target: { anchorId: anchor.id, kind: 'manual' }, createdAt: time, updatedAt: time }); d.currentGoalId = goalId; d.currentStepId = undefined; return goalId; }
  createGoal(input: GoalInput, capture: CapturedCode): Promise<string> { return this.change(d => this.goal(d, input, capture)); }
  async add(capture: CapturedCode, reason: string, newGoal?: GoalInput): Promise<string> {
    nonempty(reason); nonempty(capture.snippet, 262144);
    return this.change(d => {
      if (newGoal) { this.goal(d, newGoal, capture); } const goal = d.goals.find(g => g.id === d.currentGoalId); requireValue(goal, '조사 목표를 먼저 만드세요.');
      const anchor = this.anchor(d, capture), stepId = id(), time = now(), parent = d.currentStepId;
      const step: InvestigationStep = { id: stepId, goalId: goal.id, parentStepId: parent, sequence: Math.max(0, ...d.steps.filter(s => s.goalId === goal.id).map(s => s.sequence)) + 1, reason: reason.trim(), goalSnapshot: { title: goal.title, description: goal.description, target: clone(goal.target), anchor: clone(d.anchors.find(a => a.id === goal.target.anchorId)!) }, hypothesis: '', observation: '', requiredConditions: '', derivedConditions: '', result: '', nextAction: '', status: 'investigating', codeAnchorId: anchor.id, snippet: capture.snippet, createdAt: time, updatedAt: time };
      d.steps.push(step); if (parent) { d.relations.push({ id: id(), fromStepId: parent, toStepId: stepId, type: 'manual', evidence: step.reason, uncertainty: ['investigation_order_is_not_execution_order'] }); }
      visit(d, { goalId: goal.id, stepId, anchorId: anchor.id }, 'select_step'); return stepId;
    });
  }
  switchGoal(goalId: string): Promise<void> { return this.change(d => { requireValue(d.goals.some(g => g.id === goalId), '목표가 없습니다.'); d.currentGoalId = goalId; d.currentStepId = undefined; }); }
  select(stepId: string, sourceOpened = false): Promise<void> { return this.change(d => { const s = d.steps.find(s => s.id === stepId); requireValue(s, '단계가 없습니다.'); visit(d, { goalId: s.goalId, stepId: s.id, anchorId: s.codeAnchorId }, 'select_step'); if (sourceOpened) { visit(d, { goalId: s.goalId, stepId: s.id, anchorId: s.codeAnchorId }, 'open_source'); } }); }
  navigate(delta: -1 | 1): Promise<string | undefined> { return this.change(d => { const i = d.visitCursor + delta; if (i < 0 || i >= d.visits.length) { return undefined; } const from = d.visits[d.visitCursor]; d.visitCursor = i; const target = d.visits[i]; visit(d, target, delta < 0 ? 'back' : 'forward'); d.navigationEvents.at(-1)!.fromAnchorId = from?.anchorId; return target.stepId; }); }
  edit(stepId: string, edit: StepEdit): Promise<void> { return this.change(d => { const s = d.steps.find(s => s.id === stepId); requireValue(s, '단계가 없습니다.'); nonempty(edit.reason); requireValue(validStatus(edit.status), '조사 상태가 잘못됐습니다.'); for (const k of ['reason','hypothesis','observation','requiredConditions','derivedConditions','result','nextAction','status'] as const) { s[k] = edit[k] as never; } s.updatedAt = now(); }); }
  status(stepId: string, status: Status): Promise<void> { const s = this.value.steps.find(s => s.id === stepId); requireValue(s, '단계가 없습니다.'); return this.edit(stepId, { ...s, status }); }
  evidence(stepId: string, evidence: Omit<Evidence, 'id'|'stepId'>): Promise<void> { return this.change(d => { requireValue(d.steps.some(s => s.id === stepId), '단계가 없습니다.'); d.evidence.push({ ...clone(evidence), id: id(), stepId }); }); }
  repair(stepId: string, capture: CapturedCode): Promise<void> { return this.change(d => { const s = d.steps.find(s => s.id === stepId); requireValue(s, '단계가 없습니다.'); requireValue(capture.fileUri && capture.range, '재연결에는 파일 선택 범위가 필요합니다.'); s.codeAnchorId = this.anchor(d, capture).id; s.updatedAt = now(); }); }
}
