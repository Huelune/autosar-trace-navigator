/** P1 boundary: engine facts and investigation records stay distinct. No subprocess in P0. */
export interface EngineSourceRange { path: string; startLine: number; startByteColumn: number; endLine: number; endByteColumn: number; startByte: number; endByte: number; encoding: string }
export interface AnalysisCandidate { id: string; kind: 'call'|'rte_data'|'value'|'execution_condition'; label: string; source: EngineSourceRange; uncertainty: readonly string[] }
export interface TraceAnalysisPort {
  readonly available: boolean;
  /** Reuse analyze_project/ProjectSnapshot.search_functions in a future approved Python adapter. */
  analyze(root: string, includePaths: readonly string[], signal: AbortSignal): Promise<void>;
  searchFunctions(query: string, offset: number, limit: number, signal: AbortSignal): Promise<readonly AnalysisCandidate[]>;
  /** Reuse Workbench.candidates/value_candidates/execution_candidates without copying parser logic. */
  candidates(functionId: string, signal: AbortSignal): Promise<readonly AnalysisCandidate[]>;
}
export class DisabledTraceAnalysisPort implements TraceAnalysisPort {
  readonly available = false;
  async analyze(): Promise<never> { throw new Error('Python 분석 엔진 연결은 P1이며 P0에서는 실행하지 않습니다.'); }
  async searchFunctions(): Promise<never> { throw new Error('Python 분석 엔진 연결은 P1입니다.'); }
  async candidates(): Promise<never> { throw new Error('Python 분석 엔진 연결은 P1입니다.'); }
}
