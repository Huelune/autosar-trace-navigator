import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CapturedCode, clone, emptyDocument, id, WorkspaceDocument } from '../../src/domain/model';
import { InvestigationService } from '../../src/domain/investigationService';
import { validate } from '../../src/domain/validation';
import { forks, shownChildren, shownParent, startsBranch } from '../../src/ui/treeLayout';
const capture=(file='file:///C:/fictional/a.c'):CapturedCode=>({snippet:'if (pedal >= 60u)',fileUri:file,relativePath:'a.c',range:{start:{line:2,character:0},end:{line:2,character:18}},contextBefore:'',contextAfter:''});
const setup=()=>new InvestigationService(emptyDocument(),{async save(d){const n=clone(d);n.revision++;return n;}});
async function initial(){const s=setup();const root=await s.add(capture(),'목표 입력 확인',{title:'정상 경로',description:'수동 분기 앵커'});return {s,root};}
test('CodeNode shares only exact file/range/fingerprint; Steps and evidence stay independent',async()=>{const {s,root}=await initial();const next=await s.add(capture(),'다시 확인');await s.add(capture('file:///C:/fictional/b.c'),'동명 코드');const d=s.document;assert.equal(d.codeNodes.length,2);assert.notEqual(root,next);assert.equal(d.steps[1].parentStepId,root);assert.equal(d.steps[1].sequence,2);assert.equal(d.relations[0].type,'manual');assert.match(d.relations[0].uncertainty[0],/not_execution/);});
test('manual snippets have no fabricated symbols, shared nodes or source locations',async()=>{const s=setup();const a={snippet:'return value;',contextBefore:'',contextAfter:''};await s.add(a,'붙여넣기',{title:'수동',description:''});await s.add(a,'별도 검토');assert.equal(s.document.codeNodes.length,3);assert.ok(s.document.anchors.every(a=>a.state==='snippet_only'&&!a.fileUri));assert.ok(s.document.codeNodes.every(n=>!n.symbol));});
test('validation rejects cross-goal parents, cycles, duplicate sequence and malformed snapshots',async()=>{const {s,root}=await initial();await s.add(capture(),'자식');await s.createGoal({title:'다른 목표',description:''},capture());const other=await s.add(capture(),'다른 루트');for(const mutation of [(d:WorkspaceDocument)=>{d.steps[0].parentStepId=d.steps[1].id;},(d:WorkspaceDocument)=>{d.steps.find(x=>x.id===other)!.parentStepId=root;},(d:WorkspaceDocument)=>{d.steps[1].sequence=1;},(d:WorkspaceDocument)=>{d.steps[0].goalSnapshot.anchor.id=id();}]){const d=s.document;mutation(d);assert.throws(()=>validate(d));}});
test('status confirmed does not create CT evidence; CT evidence requires provenance',async()=>{const {s,root}=await initial();await s.status(root,'confirmed');assert.equal(s.document.evidence.length,0);await assert.rejects(s.evidence(root,{kind:'ct_observed',text:'분기 통과'}));assert.equal(s.document.evidence.length,0);await s.evidence(root,{kind:'ct_observed',text:'사람이 확인',executionLabel:'CT-가상-01',observedAt:'2026-11-10T01:00:00.000Z',memo:'입력 60 및 성공 분기 관찰'});await assert.rejects(s.evidence(root,{kind:'hypothesis',text:'가설',executionLabel:'잘못 혼합'}));assert.equal(s.document.evidence.length,1);});
test('visits back/forward preserve Steps/Edges, parent differs from previous visit, new visits truncate forward',async()=>{const {s,root}=await initial();const child=await s.add(capture(),'첫 경로');await s.select(root,true);const sibling=await s.add(capture(),'대체 경로');assert.equal(s.document.steps[2].parentStepId,root);const counts=[s.document.steps.length,s.document.relations.length];assert.equal(await s.navigate(-1),root);assert.equal(await s.navigate(-1),child);assert.equal(await s.navigate(1),root);await s.select(child);assert.equal(await s.navigate(1),undefined);assert.deepEqual([s.document.steps.length,s.document.relations.length],counts);assert.equal(s.document.visits.filter(v=>v.stepId===root).length,2);assert.notEqual(child,sibling);});
test('repair creates a new anchor without replacing stored snippet or goal snapshot',async()=>{const {s,root}=await initial();const before=s.document.steps[0];await s.repair(root,{...capture(),snippet:'new code',range:{start:{line:5,character:0},end:{line:5,character:8}}});const after=s.document.steps[0];assert.notEqual(after.codeAnchorId,before.codeAnchorId);assert.equal(after.snippet,before.snippet);assert.deepEqual(after.goalSnapshot,before.goalSnapshot);});
test('queued changes are serialized; failure retains validated dirty draft and can retry',async()=>{let fail=true;const s=new InvestigationService(emptyDocument(),{async save(d){await new Promise(r=>setTimeout(r,2));if(fail){throw Error('disk full');}const n=clone(d);n.revision++;return n;}});await assert.rejects(s.add(capture(),'작성',{title:'목표',description:''}));assert.equal(s.dirty,true);assert.equal(s.document.steps.length,1);await assert.rejects(s.add(capture(),'후속 변경 금지'));fail=false;await s.retrySave();await Promise.all([s.add(capture(),'자식1'),s.add(capture(),'자식2')]);assert.deepEqual(s.document.steps.map(x=>x.sequence),[1,2,3]);assert.equal(s.document.revision,3);assert.equal(s.dirty,false);});
test('invalid edit/oversized data leaves the last document intact',async()=>{const {s,root}=await initial();const before=s.document;await assert.rejects(s.edit(root,{...before.steps[0],reason:''}));await assert.rejects(s.add({...capture(),snippet:'x'.repeat(262145)},'과대'));assert.deepEqual(s.document,before);const d=s.document;d.schemaVersion=2 as 1;assert.throws(()=>validate(d));});
test('deleting a step removes its subtree, evidence, relations and visits but nothing else; the document stays valid',async()=>{
  const {s,root}=await initial();const first=await s.add(capture(),'첫 경로');const below=await s.add(capture('file:///C:/fictional/b.c'),'첫 경로의 하위');await s.evidence(below,{kind:'hypothesis',text:'지워질 근거'});
  await s.select(root);const sibling=await s.add(capture('file:///C:/fictional/c.c'),'대체 경로');await s.select(below);
  assert.equal(await s.removeStep(first),2);const d=s.document;validate(d);
  assert.deepEqual(d.steps.map(x=>x.id),[root,sibling]);assert.equal(d.currentStepId,root);assert.equal(d.evidence.length,0);
  assert.ok(d.relations.every(r=>r.toStepId===sibling));assert.ok(d.visits.every(v=>v.stepId===root||v.stepId===sibling));assert.equal(d.visits[d.visitCursor].stepId,sibling);
  assert.ok(!d.anchors.some(a=>a.fileUri?.endsWith('b.c')));assert.ok(d.anchors.some(a=>a.fileUri?.endsWith('c.c')));assert.equal(d.codeNodes.length,new Set(d.anchors.map(a=>a.codeNodeId)).size);
  await assert.rejects(s.removeStep(first));assert.equal(await s.removeStep(root),2);assert.equal(s.document.steps.length,0);assert.equal(s.document.goals.length,1);assert.equal(s.document.currentStepId,undefined);assert.equal(s.document.visitCursor,-1);
});
test('deleting a goal removes its steps only and leaves no goal current',async()=>{
  const {s,root}=await initial();await s.add(capture(),'자식');const kept=s.document.goals[0].id;await s.createGoal({title:'지울 목표',description:''},capture('file:///C:/fictional/d.c'));const doomed=s.document.currentGoalId!;await s.add(capture('file:///C:/fictional/d.c'),'지울 단계');
  assert.equal(await s.removeGoal(doomed),1);const d=s.document;validate(d);
  assert.deepEqual(d.goals.map(g=>g.id),[kept]);assert.equal(d.steps.length,2);assert.equal(d.steps[0].id,root);assert.equal(d.currentGoalId,undefined);assert.equal(d.currentStepId,undefined);
  assert.ok(!d.anchors.some(a=>a.fileUri?.endsWith('d.c')));assert.ok(d.navigationEvents.every(e=>e.goalId===kept));await assert.rejects(s.removeGoal(doomed));
});
test('tree layout keeps a single path on one level and indents only where the investigation forks',()=>{
  const step=(n:number,parent?:number)=>({id:'s'+n,goalId:'g',parentStepId:parent===undefined?undefined:'s'+parent,sequence:n});
  // 1 -> 2 -> 3, then 3 forks into 4 -> 5 and 6 -> 7; 7 forks again into 8 and 9.
  const steps=[step(1),step(2,1),step(3,2),step(4,3),step(5,4),step(6,3),step(7,6),step(8,7),step(9,7)];
  const ids=(parent:{kind:'goal'|'step';id:string})=>shownChildren(steps,parent).map(s=>s.id);
  assert.deepEqual(ids({kind:'goal',id:'g'}),['s1','s2','s3']);assert.deepEqual(ids({kind:'step',id:'s1'}),[]);assert.deepEqual(ids({kind:'step',id:'s2'}),[]);
  assert.deepEqual(ids({kind:'step',id:'s3'}),['s4','s5','s6','s7']);assert.deepEqual(ids({kind:'step',id:'s7'}),['s8','s9']);assert.deepEqual(ids({kind:'step',id:'s5'}),[]);
  assert.deepEqual(steps.filter(s=>forks(steps,s.id)).map(s=>s.id),['s3','s7']);assert.deepEqual(steps.filter(s=>startsBranch(steps,s)).map(s=>s.id),['s4','s6','s8','s9']);
  // Every step appears exactly once, and the parent used for reveal agrees with where it is listed.
  const seen:string[]=[];const walk=(parent:{kind:'goal'|'step';id:string})=>{for(const s of shownChildren(steps,parent)){seen.push(s.id);assert.deepEqual(shownParent(steps,s),parent);walk({kind:'step',id:s.id});}};walk({kind:'goal',id:'g'});
  assert.deepEqual(seen.sort(),steps.map(s=>s.id).sort());
  // Depth is the number of forks above a step, not the number of steps: nine steps, two levels below the goal.
  const depth=(s:{id:string;goalId:string;parentStepId?:string;sequence:number})=>{let n=0;for(let p=shownParent(steps,s);p.kind==='step';p=shownParent(steps,steps.find(x=>x.id===p.id)!)){n++;}return n;};
  assert.deepEqual(steps.map(depth),[0,0,0,1,1,1,1,2,2]);
  // Two first steps under one goal are both listed at the goal level.
  assert.deepEqual(shownChildren([step(1),step(2,1),step(3)],{kind:'goal',id:'g'}).map(s=>s.id),['s1','s2','s3']);
});
test('selected code becomes a one-line reason default',async()=>{const {reasonFromCode}=await import('../../src/domain/model');
  assert.equal(reasonFromCode('  if (a < 60)\r\n\t  return 0;  \n'),'if (a < 60) return 0;');assert.equal(reasonFromCode('x'.repeat(300)).length,200);assert.equal(reasonFromCode(' \n '),'');});
test('step search rows carry reason, status, goal, place, notes and code of every goal',async()=>{const {stepSearchItems}=await import('../../src/ui/stepSearch');
  const {s,root}=await initial();const second=await s.add(capture(),'두 번째\n  이유');await s.edit(second,{...s.document.steps[1],status:'deferred',requiredConditions:'앞선 조건\n거짓',nextAction:'갱신 순서 확인'});
  await s.createGoal({title:'다른 목표',description:''},capture());const other=await s.add({snippet:'return value;',contextBefore:'',contextAfter:''},'수동 메모');
  const rows=stepSearchItems(s.document);assert.deepEqual(rows.map(r=>r.stepId),[root,second,other]);
  assert.deepEqual(rows[1],{label:'2. 두 번째 이유',description:'보류 · 정상 경로 · a.c:3',detail:'필요 조건: 앞선 조건 거짓 | 다음 할 일: 갱신 순서 확인 | 코드: if (pedal >= 60u)',stepId:second});
  assert.deepEqual([rows[0].description,rows[0].detail],['조사 중 · 정상 경로 · a.c:3','코드: if (pedal >= 60u)']);assert.equal(rows[2].description,'조사 중 · 다른 목표');
  assert.equal(stepSearchItems(emptyDocument()).length,0);});
