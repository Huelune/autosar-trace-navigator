import { WorkspaceDocument, Range, Status } from './model';
export const MAX_FILE_BYTES = 16 * 1024 * 1024;
export const MAX_HISTORY = 2000;
export function requireValue(ok: unknown, message: string): asserts ok { if (!ok) { throw new Error(message); } }
export const validId = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v);
export const utc = (s: unknown): s is string => typeof s === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(s) && Number.isFinite(Date.parse(s)) && new Date(s).toISOString() === s;
export function text(v: unknown, max = 65536): asserts v is string { requireValue(typeof v === 'string' && v.length <= max, '문자열 형식 또는 크기가 잘못됐습니다.'); }
export function nonempty(v: unknown, max = 65536): asserts v is string { text(v, max); requireValue(v.trim().length > 0, '필수 내용을 입력하세요.'); }
export function validRange(r: Range): void { requireValue(r && r.start && r.end, '범위가 없습니다.'); for (const p of [r.start, r.end]) { requireValue(Number.isSafeInteger(p.line) && p.line >= 0 && Number.isSafeInteger(p.character) && p.character >= 0, 'UTF-16 위치가 잘못됐습니다.'); } requireValue(r.start.line < r.end.line || r.start.line === r.end.line && r.start.character <= r.end.character, '범위 끝은 시작 이후여야 합니다.'); }
export const validStatus = (v: unknown): v is Status => ['investigating', 'confirmed', 'deferred', 'excluded'].includes(v as string);
/** Validate relationships before accepting disk data or a transactional change. */
export function validate(value: unknown): asserts value is WorkspaceDocument {
  requireValue(value !== null && typeof value === 'object', '조사 문서가 아닙니다.');
  const d = value as WorkspaceDocument;
  requireValue(d.schemaVersion === 1, '지원하지 않는 조사 schemaVersion입니다. 원본을 보존합니다.');
  requireValue(Number.isSafeInteger(d.revision) && d.revision >= 0 && validId(d.repositoryId), '문서 revision/ID가 잘못됐습니다.');
  const lists: [unknown, number][] = [[d.goals, 1000], [d.steps, 10000], [d.codeNodes, 20000], [d.anchors, 20000], [d.navigationEvents, MAX_HISTORY], [d.relations, 20000], [d.evidence, 20000], [d.visits, MAX_HISTORY]];
  for (const [a, max] of lists) { requireValue(Array.isArray(a) && a.length <= max, '목록 형식/보존 한도를 초과했습니다.'); }
  const ids = new Set<string>();
  for (const a of [d.goals, d.steps, d.codeNodes, d.anchors, d.navigationEvents, d.relations, d.evidence]) { for (const x of a) { requireValue(x && validId(x.id) && !ids.has(x.id), 'ID 형식 또는 중복 오류입니다.'); ids.add(x.id); } }
  const nodes = new Set(d.codeNodes.map(n => n.id)), anchors = new Map(d.anchors.map(a => [a.id, a])), goals = new Map(d.goals.map(g => [g.id, g])), steps = new Map(d.steps.map(s => [s.id, s]));
  const keys = new Set<string>();
  for (const n of d.codeNodes) { requireValue(n.repositoryId === d.repositoryId && !keys.has(n.identityKey), '코드 실체 식별 충돌입니다.'); nonempty(n.identityKey); keys.add(n.identityKey); if (n.symbol !== undefined) { text(n.symbol); } }
  const checkAnchor = (a: typeof d.anchors[number]) => {
    requireValue(a && validId(a.id) && nodes.has(a.codeNodeId) && /^[a-f0-9]{64}$/.test(a.textFingerprint), '앵커 참조/지문 오류입니다.');
    text(a.contextBefore, 4096); text(a.contextAfter, 4096);
    requireValue(a.state === 'linked' || a.state === 'snippet_only', '앵커 상태 오류입니다.');
    if (a.fileUri !== undefined) { const u = new URL(a.fileUri); requireValue(u.protocol === 'file:' && !u.host, '로컬 file URI만 지원합니다.'); requireValue(a.range !== undefined && a.relativePath !== undefined, '파일 범위/상대 경로가 없습니다.'); }
    if (a.relativePath !== undefined) { text(a.relativePath, 4096); requireValue(!/^(?:[\\/]|[A-Za-z]:)/.test(a.relativePath) && !a.relativePath.split(/[\\/]/).includes('..'), '작업 공간 외부 경로입니다.'); }
    if (a.range !== undefined) { validRange(a.range); }
    if (a.documentVersion !== undefined) { requireValue(Number.isSafeInteger(a.documentVersion) && a.documentVersion >= 0, '문서 버전 오류입니다.'); }
    if (a.revision !== undefined) { text(a.revision); } if (a.symbol !== undefined) { text(a.symbol); }
    requireValue(a.state !== 'linked' || a.fileUri !== undefined, '연결된 파일이 없습니다.');
  };
  for (const a of d.anchors) { checkAnchor(a); }
  const checkTarget = (t: typeof d.goals[number]['target']) => { requireValue(t && anchors.has(t.anchorId) && ['if', 'else_if', 'else', 'manual'].includes(t.kind), '목표 앵커/종류 오류입니다.'); if (t.condition !== undefined) { text(t.condition); requireValue(t.kind !== 'else', 'else 조건식을 임의로 만들 수 없습니다.'); } if (t.requiredTruth !== undefined) { requireValue(typeof t.requiredTruth === 'boolean', '진릿값 오류입니다.'); } };
  for (const g of d.goals) { nonempty(g.title, 200); text(g.description); checkTarget(g.target); requireValue(utc(g.createdAt) && utc(g.updatedAt), '목표 시각 오류입니다.'); }
  const sequences = new Set<string>();
  for (const s of d.steps) {
    requireValue(goals.has(s.goalId) && anchors.has(s.codeAnchorId) && validStatus(s.status), '단계 참조/상태 오류입니다.');
    requireValue(Number.isSafeInteger(s.sequence) && s.sequence > 0 && !sequences.has(`${s.goalId}:${s.sequence}`), '목표 내 순번 오류입니다.'); sequences.add(`${s.goalId}:${s.sequence}`);
    nonempty(s.reason); text(s.snippet, 262144); for (const k of ['hypothesis','observation','requiredConditions','derivedConditions','result','nextAction'] as const) { text(s[k]); }
    requireValue(utc(s.createdAt) && utc(s.updatedAt), '단계 시각 오류입니다.');
    requireValue(s.goalSnapshot && s.goalSnapshot.anchor.id === s.goalSnapshot.target.anchorId, '당시 목표 오류입니다.'); nonempty(s.goalSnapshot.title, 200); text(s.goalSnapshot.description); checkTarget(s.goalSnapshot.target); checkAnchor(s.goalSnapshot.anchor);
    if (s.parentStepId !== undefined) { const p = steps.get(s.parentStepId); requireValue(p && p.goalId === s.goalId && p.sequence < s.sequence, '부모는 같은 목표의 이전 단계여야 합니다.'); }
    let p = s, depth = 0; while (p.parentStepId) { requireValue(++depth <= 128, '조사 트리 깊이 한도를 초과했습니다.'); p = steps.get(p.parentStepId)!; }
  }
  for (const e of d.relations) { requireValue(steps.has(e.fromStepId) && steps.has(e.toStepId) && steps.get(e.fromStepId)!.goalId === steps.get(e.toStepId)!.goalId && e.fromStepId !== e.toStepId, '관계 참조 오류입니다.'); requireValue(['call','read','write','data_dependency','manual'].includes(e.type), '관계 종류 오류입니다.'); text(e.evidence); requireValue(Array.isArray(e.uncertainty) && e.uncertainty.length <= 100, '불확실성 오류입니다.'); e.uncertainty.forEach(x => text(x)); }
  for (const e of d.evidence) { requireValue(steps.has(e.stepId) && ['source_fact','hypothesis','ct_observed'].includes(e.kind), '근거 종류/단계 오류입니다.'); nonempty(e.text); if (e.anchorId !== undefined) { requireValue(anchors.has(e.anchorId), '근거 앵커 오류입니다.'); } if (e.kind === 'ct_observed') { nonempty(e.executionLabel, 200); nonempty(e.memo); requireValue(utc(e.observedAt), 'CT 실측에는 UTC 관찰 시각이 필요합니다.'); } else { requireValue(e.executionLabel === undefined && e.observedAt === undefined && e.memo === undefined, '가설/소스 근거에 CT 실측 메타데이터를 섞지 마세요.'); } }
  for (const e of d.navigationEvents) { requireValue(anchors.has(e.toAnchorId) && (e.fromAnchorId === undefined || anchors.has(e.fromAnchorId)) && utc(e.createdAt) && ['select_step','open_source','back','forward'].includes(e.action), '방문 이벤트 오류입니다.'); if (e.stepId !== undefined) { requireValue(steps.get(e.stepId)?.goalId === e.goalId, '방문 목표/단계 오류입니다.'); } }
  for (const v of d.visits) { requireValue(steps.get(v.stepId)?.goalId === v.goalId && anchors.has(v.anchorId), '방문 커서 참조 오류입니다.'); }
  requireValue(Number.isSafeInteger(d.visitCursor) && d.visitCursor >= -1 && d.visitCursor < d.visits.length && (d.visits.length === 0 ? d.visitCursor === -1 : d.visitCursor >= 0), '방문 커서 오류입니다.');
  if (d.currentGoalId !== undefined) { requireValue(goals.has(d.currentGoalId), '현재 목표 오류입니다.'); }
  if (d.currentStepId !== undefined) { requireValue(steps.get(d.currentStepId)?.goalId === d.currentGoalId, '현재 단계 오류입니다.'); }
  requireValue(Buffer.byteLength(JSON.stringify(d,null,2),'utf8')<=MAX_FILE_BYTES,'조사 문서의 16 MiB 보존 한도를 초과했습니다.');
}
