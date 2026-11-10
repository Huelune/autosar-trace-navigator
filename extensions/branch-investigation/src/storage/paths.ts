import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

export function within(root: string, target: string): boolean { const relative = path.relative(root, target); return relative === '' || !relative.startsWith('..' + path.sep) && relative !== '..' && !path.isAbsolute(relative); }
/** Resolve links before accessing source; an existing file outside the root is never followed. */
export async function sourcePath(root: string, uri: string): Promise<string> {
  const u = new URL(uri); if (u.protocol !== 'file:' || u.host) { throw new Error('로컬 file URI만 지원합니다.'); }
  const real = await fs.realpath(fileURLToPath(u));
  if (!within(await fs.realpath(root), real)) { throw new Error('작업 공간 밖의 파일/심볼릭 링크는 접근하지 않습니다.'); }
  return real;
}
export async function safeRecordDirectory(root: string): Promise<string> {
  const realRoot = await fs.realpath(root), dir = path.join(realRoot, '.branch-investigation');
  await fs.mkdir(dir, { recursive: false }).catch(e => { if (e.code !== 'EEXIST') { throw e; } });
  if ((await fs.lstat(dir)).isSymbolicLink() || await fs.realpath(dir) !== dir) { throw new Error('조사 저장 폴더의 링크는 허용하지 않습니다.'); }
  return dir;
}
export async function rejectLink(file: string): Promise<void> {
  await fs.lstat(file).then(s => { if (s.isSymbolicLink() || !s.isFile()) { throw new Error('조사 파일의 링크/특수 파일은 허용하지 않습니다.'); } }).catch(e => { if (e.code !== 'ENOENT') { throw e; } });
}
