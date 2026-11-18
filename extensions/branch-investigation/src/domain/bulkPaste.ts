export type BulkKind = 'path' | 'function' | 'condition' | 'code';
export interface BulkItem { kind: BulkKind; text: string }
export const bulkKindLabel: Record<BulkKind, string> = { path: '경로', function: '함수명', condition: '조건식', code: '코드' };
export const BULK_LIMIT = 100;

const isPath = (s: string): boolean => !/\s/.test(s) && (/[\\/]/.test(s) || /\.[ch](:\d+)?$/i.test(s)) && !/[(){};=]/.test(s);
const isFunction = (s: string): boolean => /^[A-Za-z_]\w*(\(\))?$/.test(s);
// ponytail: text shape only, no parsing. A wrong label is corrected by the user in the preview or in the reason later; use the engine if labels must be reliable.
const isCondition = (s: string): boolean => !s.includes('\n') && (/^(else\s+)?(if|while)\s*\(/.test(s) || (!/[;{}]/.test(s) && /==|!=|<=|>=|&&|\|\||[<>]/.test(s.replaceAll('->', ''))));

export const classifyBulk = (text: string): BulkKind => isPath(text) ? 'path' : isFunction(text) ? 'function' : isCondition(text) ? 'condition' : 'code';

/**
 * Split pasted text into step candidates. Blank lines separate items; a block whose every line is a path or a
 * function name is a list and gives one item per line. Any other multi-line block stays one piece of code.
 * Nothing here is resolved against files or the engine: the kind is a label from the text shape only.
 */
export function splitBulk(text: string): { items: BulkItem[]; truncated: boolean } {
  const items: BulkItem[] = [];
  for (const block of text.replace(/\r\n?/g, '\n').split(/\n[ \t]*\n/)) {
    const lines = block.split('\n').map(l => l.trim()).filter(Boolean); if (!lines.length) { continue; }
    if (lines.every(l => isPath(l) || isFunction(l))) { items.push(...lines.map(l => ({ kind: classifyBulk(l), text: l }))); continue; }
    const body = block.replace(/^\n+|\s+$/g, ''), one = lines.length === 1 ? lines[0] : body;
    items.push({ kind: classifyBulk(one), text: one });
  }
  return { items: items.slice(0, BULK_LIMIT), truncated: items.length > BULK_LIMIT };
}
