import { spawn } from 'node:child_process';

/** Engine facts and investigation records stay distinct: a candidate is never a Step until the user picks it. */
export interface EngineLocation { path: string; startLine: number; endLine: number; startCharacter: number | null; endCharacter: number | null; text: string | null }
export interface AnalysisCandidate { relation: 'call' | 'rte_data'; label: string; functionName: string | null; uncertainty: string[]; evidence: EngineLocation; target: EngineLocation | null }
export interface RelatedRequest { root: string; file: string; line: number; includePaths: string[] }
export interface RelatedResult { functionName: string | null; candidates: AnalysisCandidate[]; truncated: boolean }
export interface TraceAnalysisPort { related(request: RelatedRequest, signal: AbortSignal): Promise<RelatedResult> }

/** Kind and next action only. Engine or OS error text may contain paths and is never shown. */
const messages = {
  python_not_runnable: 'Python을 실행하지 못했습니다. 설정의 Python 경로와 실행 권한을 확인하세요.',
  timeout: '분석이 제한 시간을 넘었습니다. 분석 범위를 줄이세요.',
  cancelled: '분석을 취소했습니다.',
  output_limit: '분석 결과가 너무 큽니다. 분석 범위를 줄이세요.',
  invalid_response: '분석 엔진의 응답을 해석하지 못했습니다. 엔진 설치와 버전을 확인하세요.',
  invalid_request: '분석 요청이 잘못됐습니다. 파일과 분석 범위 설정을 확인하세요.',
  analysis_limit: '분석 범위가 파일 수 또는 크기 한도를 넘었습니다. 분석 범위를 줄이세요.',
  scope_not_readable: '분석 범위를 읽지 못했습니다. 범위 설정이 작업 폴더 안의 실제 경로인지 확인하세요.',
  file_not_in_scope: '현재 파일이 분석 범위에 없습니다. 분석 범위 설정에 이 파일의 폴더를 추가하세요.',
  internal: '분석 엔진 내부 오류입니다. 엔진 설치를 확인하세요.',
} as const;
export type AnalysisErrorCode = keyof typeof messages;
export class AnalysisError extends Error {
  constructor(readonly code: AnalysisErrorCode) { super(messages[code]); }
}

const count = (v: unknown): v is number => Number.isSafeInteger(v) && (v as number) >= 0;
const text = (v: unknown, max: number): v is string => typeof v === 'string' && v.length <= max;
function location(v: unknown): EngineLocation {
  const l = v as EngineLocation;
  const located = count(l?.startCharacter) && count(l.endCharacter) && text(l.text, 20000);
  const unlocated = l?.startCharacter === null && l.endCharacter === null && l.text === null;
  // A relative path without parent segments: the engine must not send the editor outside the workspace.
  const inside = text(l?.path, 4096) && l.path !== '' && !/^([\\/]|[A-Za-z]:)/.test(l.path) && !l.path.split(/[\\/]/).includes('..');
  if (!inside || !count(l.startLine) || !count(l.endLine) || l.endLine < l.startLine || !(located || unlocated)) { throw new AnalysisError('invalid_response'); }
  return { path: l.path, startLine: l.startLine, endLine: l.endLine, startCharacter: l.startCharacter, endCharacter: l.endCharacter, text: l.text };
}
/** Accept only the documented shape; anything else is one error, never a partial result. */
export function parseRelated(raw: string): RelatedResult {
  let r: { ok?: unknown; error?: unknown; function?: { name?: unknown } | null; candidates?: unknown; truncated?: unknown };
  try { r = JSON.parse(raw); } catch { throw new AnalysisError('invalid_response'); }
  if (r?.ok === false) { throw new AnalysisError(typeof r.error === 'string' && Object.hasOwn(messages, r.error) ? r.error as AnalysisErrorCode : 'internal'); }
  const name = r?.function === null ? null : r?.function?.name;
  if (r?.ok !== true || !(name === null || text(name, 1000)) || !Array.isArray(r.candidates) || r.candidates.length > 200 || typeof r.truncated !== 'boolean') { throw new AnalysisError('invalid_response'); }
  const candidates = r.candidates.map((c: AnalysisCandidate) => {
    const valid = (c?.relation === 'call' || c?.relation === 'rte_data') && text(c.label, 1000) && (c.functionName === null || text(c.functionName, 1000))
      && Array.isArray(c.uncertainty) && c.uncertainty.length <= 50 && c.uncertainty.every(u => text(u, 200));
    if (!valid) { throw new AnalysisError('invalid_response'); }
    return { relation: c.relation, label: c.label, functionName: c.functionName, uncertainty: [...c.uncertainty], evidence: location(c.evidence), target: c.target === null ? null : location(c.target) };
  });
  return { functionName: name, candidates, truncated: r.truncated };
}

/** One short-lived local process per request: no shell, no network, stderr discarded. */
export class PythonTraceAnalysisPort implements TraceAnalysisPort {
  // ponytail: every request re-parses the scope; switch to a long-lived process with a cached snapshot if this is measurably slow.
  constructor(private readonly python: string, private readonly args: readonly string[] = ['-I', '-m', 'autosar_trace_navigator.bridge'],
    private readonly timeoutMs = 60000, private readonly maxOutputBytes = 8 * 1024 * 1024) {}
  related(request: RelatedRequest, signal: AbortSignal): Promise<RelatedResult> {
    return new Promise((resolve, reject) => {
      if (signal.aborted) { reject(new AnalysisError('cancelled')); return; }
      const child = spawn(this.python, [...this.args], { shell: false, windowsHide: true, stdio: ['pipe', 'pipe', 'ignore'] });
      const chunks: Buffer[] = []; let size = 0, failure: AnalysisErrorCode | undefined;
      const stop = (code: AnalysisErrorCode) => { failure ??= code; child.kill(); };
      const timer = setTimeout(() => stop('timeout'), this.timeoutMs), abort = () => stop('cancelled');
      signal.addEventListener('abort', abort, { once: true });
      const finish = (action: () => void) => { clearTimeout(timer); signal.removeEventListener('abort', abort); action(); };
      child.on('error', () => finish(() => reject(new AnalysisError(failure ?? 'python_not_runnable'))));
      child.stdout.on('data', (chunk: Buffer) => { size += chunk.length; if (size > this.maxOutputBytes) { stop('output_limit'); } else { chunks.push(chunk); } });
      child.on('close', () => finish(() => {
        if (failure) { reject(new AnalysisError(failure)); return; }
        try { resolve(parseRelated(Buffer.concat(chunks).toString('utf8'))); } catch (e) { reject(e); }
      }));
      child.stdin.on('error', () => {}); // a process that exits before reading is reported by 'close'
      child.stdin.end(JSON.stringify(request));
    });
  }
}
