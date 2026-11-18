import { test } from 'node:test';
import assert from 'node:assert/strict';
import { clone, emptyDocument } from '../../src/domain/model';
import { InvestigationService } from '../../src/domain/investigationService';
import { codeLabel, currentPath, shortText, sourceLabel, TraceEntry, TracePresentation } from '../../src/ui/tracePresentation';

async function history(forks = false) {
  const s = new InvestigationService(emptyDocument(), { async save(d) { const next = clone(d); next.revision++; return next; } });
  const main: string[] = [], alternatives: string[] = [];
  for (let n = 1; n <= 40; n++) {
    main.push(await s.add({ snippet: `Supply_${n}();`, fileUri: 'file:///C:/synthetic/a.c', relativePath: 'module/a.c', range: { start: { line: n, character: 0 }, end: { line: n, character: 12 } }, contextBefore: '', contextAfter: '' },
      `입력 ${n}의 출처 확인`, n === 1 ? { title: 'pedal >= 60u', description: '원래 목표 보존' } : undefined));
    if (forks && n % 2 === 0 && n < 40) {
      alternatives.push(await s.add({ snippet: `Alternative_${n}();`, contextBefore: '', contextAfter: '' }, '대체 경로'));
      await s.status(alternatives.at(-1)!, 'deferred'); await s.select(main.at(-1)!);
    }
  }
  return { s, main, alternatives };
}

function rows(layout: TracePresentation) {
  const ids: string[] = [], depths: number[] = [];
  const walk = (parent: TraceEntry, depth: number) => {
    for (const entry of layout.getChildren(parent)) {
      assert.deepEqual(layout.getParent(entry), parent);
      if (entry.kind === 'step') { ids.push(entry.id); depths.push(depth); }
      walk(entry, depth + 1);
    }
  };
  for (const goal of layout.getChildren()) { walk(goal, 1); }
  return { ids, depths };
}

test('40 sequential investigations stay within two display levels; all records and parents are untouched', async () => {
  const { s, main } = await history(), before = s.document, serialized = JSON.stringify(before);
  const view = new TracePresentation(before, 'path'), goal = view.getChildren()[0], visible = view.getChildren(goal);
  assert.equal(visible.filter(row => row.kind === 'group').length, 3);
  assert.equal(visible.filter(row => row.kind === 'step').length, 10);
  assert.deepEqual(rows(view).ids, main);
  assert.ok(rows(view).depths.every(depth => depth <= 2));
  assert.equal(view.getParent({ kind: 'step', id: main.at(-1)! })?.kind, 'goal');
  assert.equal(JSON.stringify(before), serialized);
  assert.match(view.message, /목표: pedal >= 60u/); assert.match(view.message, /현재 #40/);
  assert.match(view.message, /경로 40 \/ 전체 40단계/); assert.match(view.message, /입력 40의 출처 확인/);
});

test('current path stays shallow across 19 forks; full branch view retains every alternative', async () => {
  const { s, main, alternatives } = await history(true), document = s.document;
  assert.equal(document.steps.length, 59);
  assert.deepEqual(currentPath(document).map(step => step.id), main);
  const path = rows(new TracePresentation(document, 'path'));
  assert.deepEqual(path.ids, main); assert.ok(path.depths.every(depth => depth <= 2));
  const all = rows(new TracePresentation(document, 'branches'));
  assert.equal(new Set(all.ids).size, 59); assert.ok(alternatives.every(id => all.ids.includes(id)));
  assert.ok(all.depths.some(depth=>depth>2),'full branch mode keeps the original branch grouping');
  assert.equal(s.document.revision, document.revision);
});

test('selecting an ancestor exposes its immediate alternatives without folding them away', async () => {
  const { s, main } = await history(true); await s.select(main[19]);
  const document = s.document, layout = new TracePresentation(document, 'path');
  const children = document.steps.filter(step => step.parentStepId === main[19]);
  const visible = layout.getChildren(layout.getChildren()[0]);
  assert.equal(children.length, 2);
  assert.ok(children.every(step => visible.some(row => row.kind === 'step' && row.id === step.id)));
  assert.equal(currentPath(document).length, 20);
  assert.match(layout.message, /경로 20 \/ 전체 59단계/);
});

test('view groups keep stable IDs as a path grows; labels distinguish repeated reasons and Unicode stays whole', async () => {
  const { s } = await history();
  const first = new TracePresentation(s.document, 'path').getChildren({ kind: 'goal', id: s.document.currentGoalId! })[0];
  await s.add({ snippet: 'Next();', contextBefore: '', contextAfter: '' }, '입력 확인');
  const next = new TracePresentation(s.document, 'path').getChildren({ kind: 'goal', id: s.document.currentGoalId! })[0];
  assert.deepEqual(first, next);
  assert.equal(codeLabel({ ...s.document.steps[0], snippet: '😀\nreturn value;' }), '😀');
  assert.equal(shortText('가😀나다', 3), '가😀…');
  assert.equal(sourceLabel(s.document.anchors.find(a => a.id === s.document.steps[0].codeAnchorId)), 'a.c:2');
  assert.equal(sourceLabel(), '파일 없는 메모');
});

test('empty goals and another goal do not inherit an unrelated current path or reason', async () => {
  const { s } = await history();
  await s.createGoal({ title: '별도 목표', description: '' }, { snippet: '', contextBefore: '', contextAfter: '' });
  const document = s.document, view = new TracePresentation(document, 'path');
  assert.deepEqual(currentPath(document), []); assert.match(view.message, /별도 목표/);
  assert.doesNotMatch(view.message, /입력 40/);
  assert.deepEqual(view.getChildren({ kind: 'goal', id: document.currentGoalId! }), []);
  const blank = new TracePresentation(emptyDocument(), 'branches'); assert.deepEqual(blank.getChildren(), []);
});
