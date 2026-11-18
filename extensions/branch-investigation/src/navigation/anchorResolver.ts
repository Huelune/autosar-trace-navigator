import { CodeAnchor, fingerprint, Range } from '../domain/model';
import { sourcePath } from '../storage/paths';
import { validRange } from '../domain/validation';
export type AnchorResolution = { state: 'verified'; range: Range; fileUri: string } | { state: 'snippet_only' | 'needs_review' | 'missing'; message: string };
/** JS string offsets and VS Code characters are UTF-16; CRLF counts as one line break. */
function lineStarts(text: string): number[] { const starts = [0]; const eol = /\r\n|\r|\n/g; let match; while ((match = eol.exec(text))) { starts.push(match.index + match[0].length); } return starts; }
export function offsets(text: string, range: Range): [number, number] {
  validRange(range); const starts = lineStarts(text);
  const offset = (p: Range['start']) => { if (p.line >= starts.length) { throw new Error('저장된 행이 없습니다.'); }
    const start = starts[p.line], end = p.line + 1 < starts.length ? starts[p.line + 1] : text.length;
    const line = text.slice(start, end).replace(/[\r\n]+$/, ''); if (p.character > line.length) { throw new Error('저장된 열이 없습니다.'); } return start + p.character; };
  return [offset(range.start), offset(range.end)];
}
export async function resolveAnchor(root: string, anchor: CodeAnchor, readOpenDocument: (uri: string) => Promise<string>): Promise<AnchorResolution> {
  if (!anchor.fileUri || !anchor.range) { return { state: 'snippet_only', message: '연결된 파일 없음 — 저장한 스니펫을 표시합니다.' }; }
  try {
    await sourcePath(root, anchor.fileUri); const text = await readOpenDocument(anchor.fileUri), [start, end] = offsets(text, anchor.range);
    if (fingerprint(text.slice(start, end)) !== anchor.textFingerprint) { return { state: 'needs_review', message: '위치 확인 필요 — 현재 텍스트가 저장 당시와 다릅니다. 자동 이동하지 않습니다.' }; }
    return { state: 'verified', range: anchor.range, fileUri: anchor.fileUri };
  } catch (e) { return { state: (e as NodeJS.ErrnoException).code === 'ENOENT' ? 'missing' : 'needs_review', message: '위치 확인 필요 — 파일/작업 공간 경계/범위를 검증할 수 없습니다. 자동 이동하지 않습니다.' }; }
}

export interface AnchorCandidate { range: Range; context: 'both' | 'partial' | 'none'; lineDelta?: number }
/**
 * Every place in the same file where the saved snippet text occurs now, best surrounding-context match first.
 * A text match is a suggestion, never proof of the same code: the caller asks before relinking, even for one candidate.
 */
export function anchorCandidates(text: string, snippet: string, anchor: Pick<CodeAnchor, 'range' | 'contextBefore' | 'contextAfter'>, limit = 20): { candidates: AnchorCandidate[]; truncated: boolean } {
  if (!snippet) { return { candidates: [], truncated: false }; }
  // The snippet keeps the line endings of the day it was saved; the file may have been converted since.
  const needle = text.includes(snippet) ? snippet : snippet.replace(/\r\n|\r|\n/g, text.includes('\r\n') ? '\r\n' : '\n');
  const starts = lineStarts(text), before = anchor.contextBefore, after = anchor.contextAfter;
  const position = (offset: number) => { let line = starts.length - 1; while (starts[line] > offset) { line--; } return { line, character: offset - starts[line] }; };
  // ponytail: stops at 200 occurrences and scans line starts linearly per hit; index the file if snippets this common in files this large matter.
  const found: (AnchorCandidate & { score: number })[] = []; let truncated = false;
  for (let at = text.indexOf(needle); at >= 0; at = text.indexOf(needle, at + 1)) {
    if (found.length === 200) { truncated = true; break; }
    const end = at + needle.length; let b = 0, a = 0;
    while (b < before.length && b < at && text[at - 1 - b] === before[before.length - 1 - b]) { b++; }
    while (a < after.length && end + a < text.length && text[end + a] === after[a]) { a++; }
    const start = position(at);
    found.push({ range: { start, end: position(end) }, context: b === before.length && a === after.length ? 'both' : b + a ? 'partial' : 'none', lineDelta: anchor.range ? start.line - anchor.range.start.line : undefined, score: b + a });
  }
  found.sort((x, y) => y.score - x.score || Math.abs(x.lineDelta ?? 0) - Math.abs(y.lineDelta ?? 0));
  return { candidates: found.slice(0, limit).map(({ score: _score, ...candidate }) => candidate), truncated: truncated || found.length > limit };
}
