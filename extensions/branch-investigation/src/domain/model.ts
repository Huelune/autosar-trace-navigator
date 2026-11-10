import { createHash, randomUUID } from 'node:crypto';

export type Id = string;
export interface Position { line: number; character: number }
export interface Range { start: Position; end: Position }
export type Status = 'investigating' | 'confirmed' | 'deferred' | 'excluded';
export const statusLabels: Record<Status, string> = { investigating: '조사 중', confirmed: '확인', deferred: '보류', excluded: '제외' };
export interface BranchTarget { anchorId: Id; kind: 'if' | 'else_if' | 'else' | 'manual'; condition?: string; requiredTruth?: boolean }
export interface InvestigationGoal { id: Id; title: string; description: string; target: BranchTarget; createdAt: string; updatedAt: string }
export interface CodeNode { id: Id; repositoryId: Id; identityKey: string; symbol?: string }
export interface CodeAnchor { id: Id; codeNodeId: Id; fileUri?: string; relativePath?: string; symbol?: string; revision?: string; documentVersion?: number; range?: Range; textFingerprint: string; contextBefore: string; contextAfter: string; state: 'linked' | 'snippet_only' }
export interface GoalSnapshot { title: string; description: string; target: BranchTarget; anchor: CodeAnchor }
export interface InvestigationStep { id: Id; goalId: Id; parentStepId?: Id; sequence: number; reason: string; goalSnapshot: GoalSnapshot; hypothesis: string; observation: string; requiredConditions: string; derivedConditions: string; result: string; nextAction: string; status: Status; codeAnchorId: Id; snippet: string; createdAt: string; updatedAt: string }
export interface NavigationEvent { id: Id; goalId?: Id; stepId?: Id; fromAnchorId?: Id; toAnchorId: Id; action: 'select_step' | 'open_source' | 'back' | 'forward'; createdAt: string }
export interface RelationEdge { id: Id; fromStepId: Id; toStepId: Id; type: 'call' | 'read' | 'write' | 'data_dependency' | 'manual'; evidence: string; uncertainty: string[] }
export interface Evidence { id: Id; stepId: Id; text: string; kind: 'source_fact' | 'hypothesis' | 'ct_observed'; anchorId?: Id; executionLabel?: string; observedAt?: string; memo?: string }
export interface Visit { goalId: Id; stepId: Id; anchorId: Id }
export interface WorkspaceDocument { schemaVersion: 1; revision: number; repositoryId: Id; goals: InvestigationGoal[]; steps: InvestigationStep[]; codeNodes: CodeNode[]; anchors: CodeAnchor[]; navigationEvents: NavigationEvent[]; relations: RelationEdge[]; evidence: Evidence[]; visits: Visit[]; visitCursor: number; currentGoalId?: Id; currentStepId?: Id }
export interface CapturedCode { snippet: string; fileUri?: string; relativePath?: string; range?: Range; documentVersion?: number; contextBefore: string; contextAfter: string }
export const id = (): Id => randomUUID();
export const now = (): string => new Date().toISOString();
export const fingerprint = (text: string): string => createHash('sha256').update(text, 'utf8').digest('hex');
export const clone = <T>(value: T): T => structuredClone(value);
export function emptyDocument(): WorkspaceDocument { return { schemaVersion: 1, revision: 0, repositoryId: id(), goals: [], steps: [], codeNodes: [], anchors: [], navigationEvents: [], relations: [], evidence: [], visits: [], visitCursor: -1 }; }
