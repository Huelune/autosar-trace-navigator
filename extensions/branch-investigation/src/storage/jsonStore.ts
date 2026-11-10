import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { hostname } from 'node:os';
import { clone, emptyDocument, fingerprint, id, now, WorkspaceDocument } from '../domain/model';
import { MAX_FILE_BYTES, requireValue, validate } from '../domain/validation';
import { rejectLink, safeRecordDirectory } from './paths';

export class JsonStore {
  private dir = ''; private token?: string; private knownHash?: string;
  /** Fault injection is local-test only; production uses the OS rename implementation. */
  constructor(private readonly root: string, private readonly rename = fs.rename) {}
  get file(): string { return path.join(this.dir, 'workspace.json'); }
  private get lock(): string { return path.join(this.dir, 'writer.lock'); }
  private async bytes(file: string): Promise<string> { await rejectLink(file); const stat = await fs.stat(file); requireValue(stat.size <= MAX_FILE_BYTES, '조사 파일이 16 MiB 한도를 초과했습니다.'); return fs.readFile(file, 'utf8'); }
  private parse(raw: string): WorkspaceDocument { const d: unknown = JSON.parse(raw); validate(d); return d; }
  async open(): Promise<WorkspaceDocument> {
    this.dir = await safeRecordDirectory(this.root);
    if (!this.token) {
      requireValue(!await fs.lstat(path.join(this.dir,'recovery.lock')).then(()=>true,()=>false), '잠금 복구 작업이 진행 중입니다. 잠시 후 다시 여세요.');
      const token = id(); let handle;
      try { handle = await fs.open(this.lock, 'wx', 0o600); }
      catch (e) { if ((e as NodeJS.ErrnoException).code === 'EEXIST') { throw new Error('다른 작성 창 또는 종료된 작성자의 잠금이 있습니다. 기존 잠금을 임의 삭제하지 않습니다.'); } throw e; }
      try { await handle.writeFile(JSON.stringify({ token, pid: process.pid, host: hostname(), createdAt: now() })); await handle.sync(); this.token = token; } catch(e) { await handle.close(); await fs.unlink(this.lock).catch(()=>{}); throw e; } finally { await handle.close().catch(()=>{}); }
    }
    try { const raw = await this.bytes(this.file); const d = this.parse(raw); this.knownHash = fingerprint(raw); return clone(d); }
    catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'ENOENT') { throw new Error('조사 파일을 읽지 못했습니다. 손상/지원하지 않는 버전일 수 있습니다. 원본을 보존하고 백업 복구를 선택하세요.'); }
      const backupExists = await fs.lstat(this.file + '.backup').then(() => true, () => false);
      requireValue(!backupExists, '조사 파일이 없지만 백업이 있습니다. 백업 복구를 선택하세요.');
      this.knownHash = undefined; return emptyDocument();
    }
  }
  private async assertWriter(): Promise<void> { requireValue(await safeRecordDirectory(this.root)===this.dir,'조사 폴더가 변경됐습니다.'); const lock = JSON.parse(await this.bytes(this.lock)); requireValue(this.token && lock.token === this.token && lock.pid === process.pid, '작성 잠금을 잃었습니다. 저장을 중단합니다.'); }
  private async atomic(file: string, raw: string): Promise<void> {
    await rejectLink(file); const temp = path.join(this.dir, `.tmp-${id()}`); const h = await fs.open(temp, 'wx', 0o600);
    try { try { await h.writeFile(raw, 'utf8'); await h.sync(); } finally { await h.close(); } await this.rename(temp, file); } finally { await fs.unlink(temp).catch(() => {}); }
  }
  async save(value: WorkspaceDocument, expected: number): Promise<WorkspaceDocument> {
    validate(value); await this.assertWriter();
    let previous: string | undefined;
    try { previous = await this.bytes(this.file); const old = this.parse(previous); requireValue(old.revision === expected && fingerprint(previous) === this.knownHash, '동시 변경 또는 revision 충돌입니다. 덮어쓰지 않습니다.'); }
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
  /** Explicit recovery only after a same-host owner is proved absent. Never terminates a process. */
  async recoverStaleLock(): Promise<void> {
    this.dir = await safeRecordDirectory(this.root); requireValue(!this.token, '현재 창이 이미 작성 잠금을 보유합니다.');
    const guardPath=path.join(this.dir,'recovery.lock'), guard=await fs.open(guardPath,'wx',0o600);
    try {
    await guard.writeFile(JSON.stringify({pid:process.pid,host:hostname(),createdAt:now()}));await guard.sync();
    const raw = await this.bytes(this.lock), l = JSON.parse(raw);
    requireValue(l.host === hostname() && typeof l.token === 'string' && Number.isSafeInteger(l.pid) && l.pid > 0, '잠금 소유자를 확인할 수 없습니다.');
    let dead = false; try { process.kill(l.pid, 0); } catch (e) { dead = (e as NodeJS.ErrnoException).code === 'ESRCH'; }
    requireValue(dead, '소유 프로세스가 실행 중이거나 종료를 확인할 수 없습니다.');
    requireValue(await this.bytes(this.lock) === raw, '잠금이 변경됐습니다.'); await fs.unlink(this.lock);
    } finally {await guard.close();await fs.unlink(guardPath);}
  }
  async close(): Promise<void> { if (this.token) { await this.assertWriter(); await fs.unlink(this.lock); this.token = undefined; } }
}
