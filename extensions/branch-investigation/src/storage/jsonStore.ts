import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { clone, emptyDocument, fingerprint, id, WorkspaceDocument } from '../domain/model';
import { MAX_FILE_BYTES, requireValue, validate } from '../domain/validation';
import { rejectLink, safeRecordDirectory } from './paths';

export class JsonStore {
  private dir = ''; private knownHash?: string;
  /** Fault injection is local-test only; production uses the OS rename implementation. */
  constructor(private readonly root: string, private readonly rename = fs.rename) {}
  get file(): string { return path.join(this.dir, 'workspace.json'); }
  private async bytes(file: string): Promise<string> { await rejectLink(file); const stat = await fs.stat(file); requireValue(stat.size <= MAX_FILE_BYTES, '조사 파일이 16 MiB 한도를 초과했습니다.'); return fs.readFile(file, 'utf8'); }
  private parse(raw: string): WorkspaceDocument { const d: unknown = JSON.parse(raw); validate(d); return d; }
  async open(): Promise<WorkspaceDocument> {
    this.dir = await safeRecordDirectory(this.root);
    // No writer lock file: one left by a crashed window blocked opening. Concurrent writers are caught by the revision/hash check in save().
    try { const raw = await this.bytes(this.file); const d = this.parse(raw); this.knownHash = fingerprint(raw); return clone(d); }
    catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'ENOENT') { throw new Error('조사 파일을 읽지 못했습니다. 손상/지원하지 않는 버전일 수 있습니다. 원본을 보존하고 백업 복구를 선택하세요.'); }
      const backupExists = await fs.lstat(this.file + '.backup').then(() => true, () => false);
      requireValue(!backupExists, '조사 파일이 없지만 백업이 있습니다. 백업 복구를 선택하세요.');
      this.knownHash = undefined; return emptyDocument();
    }
  }
  private async assertWriter(): Promise<void> { requireValue(await safeRecordDirectory(this.root)===this.dir,'조사 폴더가 변경됐습니다.'); }
  private async atomic(file: string, raw: string): Promise<void> {
    await rejectLink(file); const temp = path.join(this.dir, `.tmp-${id()}`); const h = await fs.open(temp, 'wx', 0o600);
    try { try { await h.writeFile(raw, 'utf8'); await h.sync(); } finally { await h.close(); } await this.rename(temp, file); } finally { await fs.unlink(temp).catch(() => {}); }
  }
  async save(value: WorkspaceDocument, expected: number): Promise<WorkspaceDocument> {
    validate(value); await this.assertWriter();
    let previous: string | undefined;
    try { previous = await this.bytes(this.file); const old = this.parse(previous); requireValue(old.revision === expected && fingerprint(previous) === this.knownHash, '다른 창이나 프로그램이 조사 파일을 먼저 저장했습니다(revision 충돌). 덮어쓰지 않습니다. 이 창의 변경을 버리고 최신 내용을 보려면 창을 다시 불러오세요.'); }
    catch (e) { if ((e as NodeJS.ErrnoException).code !== 'ENOENT') { throw e; } requireValue(expected === 0 && this.knownHash === undefined, '저장 파일이 외부에서 삭제됐습니다.'); }
    const next = clone(value); next.revision = expected + 1; validate(next);
    const raw = JSON.stringify(next, null, 2) + '\n'; requireValue(Buffer.byteLength(raw) <= MAX_FILE_BYTES, '저장 한도 16 MiB를 초과했습니다.');
    if (previous !== undefined) { await this.atomic(this.file + '.backup', previous); }
    await this.atomic(this.file, raw); this.knownHash = fingerprint(raw);
    if (process.platform !== 'win32') { const dir = await fs.open(this.dir, 'r'); try { await dir.sync(); } finally { await dir.close(); } }
    return next;
  }
  async recoverBackup(): Promise<WorkspaceDocument> {
    await this.assertWriter(); const raw = await this.bytes(this.file + '.backup'), d = this.parse(raw);
    // Preserve corrupt/future originals. A future version is never replaced with an older backup.
    try { const current = await this.bytes(this.file); let parsed; try { parsed = JSON.parse(current); } catch { /* preserve malformed bytes below */ }
      requireValue(!parsed || typeof parsed.schemaVersion !== 'number' || parsed.schemaVersion <= 1, '미래 schemaVersion은 백업으로 덮어쓰지 않습니다.');
      await this.atomic(path.join(this.dir, `preserved-${id()}.json`), current);
    } catch (e) { if ((e as NodeJS.ErrnoException).code !== 'ENOENT') { throw e; } }
    await this.atomic(this.file, raw); this.knownHash = fingerprint(raw); return d;
  }
  /** Nothing to release since there is no lock file; kept for callers that close the store on shutdown. */
  async close(): Promise<void> { /* no lock to release */ }
}
