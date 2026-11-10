import { CodeAnchor, fingerprint, Range } from '../domain/model';
import { sourcePath } from '../storage/paths';
import { validRange } from '../domain/validation';
export type AnchorResolution = { state: 'verified'; range: Range; fileUri: string } | { state: 'snippet_only' | 'needs_review' | 'missing'; message: string };
/** JS string offsets and VS Code characters are UTF-16; CRLF counts as one line break. */
export function offsets(text: string, range: Range): [number, number] {
  validRange(range); const starts = [0]; const eol = /\r\n|\r|\n/g; let match;
  while ((match = eol.exec(text))) { starts.push(match.index + match[0].length); }
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
