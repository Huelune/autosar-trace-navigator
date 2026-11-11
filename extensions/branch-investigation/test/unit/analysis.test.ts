import { test } from 'node:test';
import assert from 'node:assert/strict';
import { AnalysisError, parseRelated, PythonTraceAnalysisPort } from '../../src/adapters/traceAnalysisPort';
import { InvestigationService } from '../../src/domain/investigationService';
import { CapturedCode, clone, emptyDocument } from '../../src/domain/model';

// Node stands in for the Python process: the port only cares about stdin, stdout and exit.
const fake = (script: string, timeoutMs = 20000, maxOutputBytes = 1024 * 1024) => new PythonTraceAnalysisPort(process.execPath, ['-e', script], timeoutMs, maxOutputBytes);
const request = { root: 'C:/fictional', file: 'a.c', line: 3, character: 7, includePaths: ['.'] };
const place = { path: 'src/b.c', startLine: 4, endLine: 4, startCharacter: 2, endCharacter: 9, text: 'Writer()' };
const candidate = { relation: 'rte_data', label: 'Speed', functionName: 'Producer', uncertainty: ['name_only_connection'], requiredTruth: null, evidence: place, target: place };
const condition = { ...candidate, relation: 'execution_condition', label: '(mode == 1)', requiredTruth: false };
const empty = { ok: true, function: null, variable: null, notes: [], candidates: [], truncated: false };
const reply = (value: unknown) => `process.stdout.write(${JSON.stringify(JSON.stringify(value))})`;
const code = async (run: Promise<unknown>): Promise<string> => { try { await run; } catch (e) { assert.ok(e instanceof AnalysisError); return e.code; } throw new Error('expected a failure'); };
const idle = new AbortController().signal;

test('request is sent as one JSON document and a valid reply is returned as candidates', async () => {
  const echo = `let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const r=JSON.parse(s);process.stdout.write(JSON.stringify({ok:true,function:{name:[r.file,r.line,r.character,r.includePaths[0]].join(':')},variable:'pedal',notes:['access_path_not_supported'],candidates:${JSON.stringify([condition, candidate])},truncated:false}))})`;
  const result = await fake(echo).related(request, idle);
  assert.deepEqual([result.functionName, result.variable, result.notes], ['a.c:3:7:.', 'pedal', ['access_path_not_supported']]);
  assert.deepEqual(result.candidates, [condition, candidate]);
  assert.deepEqual(await fake(reply(empty)).related(request, idle), { functionName: null, variable: null, notes: [], candidates: [], truncated: false });
});

test('process failures become a kind without the executable path or engine text', async () => {
  const missing = new PythonTraceAnalysisPort('C:/fictional/secret-python.exe');
  await assert.rejects(missing.related(request, idle), (e: AnalysisError) => e.code === 'python_not_runnable' && !e.message.includes('secret'));
  assert.equal(await code(fake('setTimeout(()=>{},60000)', 300).related(request, idle)), 'timeout');
  assert.equal(await code(fake(`process.stdout.write('x'.repeat(5000))`, 20000, 1000).related(request, idle)), 'output_limit');
  assert.equal(await code(fake(`process.stdout.write('Traceback secret')`).related(request, idle)), 'invalid_response');
  assert.equal(await code(fake('process.exit(1)').related(request, idle)), 'invalid_response');
  assert.equal(await code(fake(reply({ ok: false, error: 'analysis_limit' })).related(request, idle)), 'analysis_limit');
  assert.equal(await code(fake(reply({ ok: false, error: 'C:/secret/path not found' })).related(request, idle)), 'internal');
});

test('cancel stops the process and reports cancelled, before or during the run', async () => {
  const during = new AbortController(); setTimeout(() => during.abort(), 200);
  assert.equal(await code(fake('setTimeout(()=>{},60000)').related(request, during.signal)), 'cancelled');
  const before = new AbortController(); before.abort();
  assert.equal(await code(fake('setTimeout(()=>{},60000)').related(request, before.signal)), 'cancelled');
});

test('a reply that could move the editor outside the workspace or to a guessed column is refused whole', () => {
  const ok = { ...empty, function: { name: 'F' }, candidates: [candidate] };
  assert.equal(parseRelated(JSON.stringify(ok)).candidates.length, 1);
  const unlocated = { ...place, startCharacter: null, endCharacter: null, text: null };
  assert.equal(parseRelated(JSON.stringify({ ...ok, candidates: [{ ...candidate, target: unlocated }] })).candidates[0].target!.text, null);
  assert.equal(parseRelated(JSON.stringify({ ...ok, candidates: [{ ...candidate, target: null }] })).candidates[0].target, null);
  assert.equal(parseRelated(JSON.stringify({ ...ok, candidates: [{ ...candidate, relation: 'value' }, condition] })).candidates[1].requiredTruth, false);
  for (const bad of [
    { ...candidate, target: { ...place, path: '../outside.c' } }, { ...candidate, target: { ...place, path: 'C:/outside.c' } },
    { ...candidate, target: { ...place, path: '/outside.c' } }, { ...candidate, target: { ...place, path: 'src\\..\\..\\outside.c' } },
    { ...candidate, target: { ...place, startCharacter: null } }, { ...candidate, target: { ...place, endLine: 3 } },
    { ...candidate, target: { ...place, startLine: -1 } }, { ...candidate, relation: 'read' }, { ...candidate, uncertainty: [1] }, { ...candidate, evidence: null },
    // The needed truth value belongs to execution conditions only, and they must carry one.
    { ...candidate, requiredTruth: true }, { ...condition, requiredTruth: null }, { ...condition, requiredTruth: 'false' },
  ]) { assert.throws(() => parseRelated(JSON.stringify({ ...ok, candidates: [bad] })), (e: AnalysisError) => e.code === 'invalid_response'); }
  for (const bad of [{ ...ok, truncated: 'no' }, { ...ok, candidates: {} }, { ...ok, function: { name: 5 } }, { ...ok, variable: 3 }, { ...ok, notes: 'none' }, { ...ok, notes: [1] }, { ok: 'true' }, null, []]) {
    assert.throws(() => parseRelated(JSON.stringify(bad)), (e: AnalysisError) => e.code === 'invalid_response');
  }
});

test('a picked candidate records its relation type and engine uncertainty; manual steps are unchanged', async () => {
  const capture: CapturedCode = { snippet: 'Rte_Write_Speed(v)', fileUri: 'file:///C:/fictional/b.c', relativePath: 'b.c', range: { start: { line: 4, character: 2 }, end: { line: 4, character: 20 } }, contextBefore: '', contextAfter: '' };
  const s = new InvestigationService(emptyDocument(), { async save(d) { const n = clone(d); n.revision++; return n; } });
  await s.add(capture, '읽는 쪽', { title: '목표', description: '' });
  await s.add(capture, 'Writer 후보 조사', undefined, { type: 'data_dependency', uncertainty: ['name_only_connection'] });
  await s.add(capture, '직접 고른 코드');
  await s.add(capture, '앞선 조건이 거짓이어야 함', undefined, { type: 'manual', uncertainty: ['condition_satisfiability_not_proven', 'execution_requirement_false'] });
  const [linked, manual, required] = s.document.relations;
  assert.deepEqual([linked.type, linked.uncertainty], ['data_dependency', ['name_only_connection', 'investigation_order_is_not_execution_order']]);
  assert.deepEqual([manual.type, manual.uncertainty], ['manual', ['investigation_order_is_not_execution_order']]);
  assert.deepEqual([required.type, required.uncertainty], ['manual', ['condition_satisfiability_not_proven', 'execution_requirement_false', 'investigation_order_is_not_execution_order']]);
});
