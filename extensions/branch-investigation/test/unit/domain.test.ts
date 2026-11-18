import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CapturedCode, clone, emptyDocument, id, WorkspaceDocument } from '../../src/domain/model';
import { InvestigationService } from '../../src/domain/investigationService';
import { validate } from '../../src/domain/validation';
import { branchSize, forks, onBranch, shownChildren, shownParent, startsBranch } from '../../src/ui/treeLayout';
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
test('tree layout keeps a single path on one level and groups each alternative under its first step',()=>{
  const step=(n:number,parent?:number)=>({id:'s'+n,goalId:'g',parentStepId:parent===undefined?undefined:'s'+parent,sequence:n});
  // 1 -> 2 -> 3, then 3 forks into 4 -> 5 and 6 -> 7; 7 forks again into 8 and 9.
  const steps=[step(1),step(2,1),step(3,2),step(4,3),step(5,4),step(6,3),step(7,6),step(8,7),step(9,7)];
  const ids=(parent:{kind:'goal'|'step';id:string})=>shownChildren(steps,parent).map(s=>s.id);
  assert.deepEqual(ids({kind:'goal',id:'g'}),['s1','s2','s3']);assert.deepEqual(ids({kind:'step',id:'s1'}),[]);assert.deepEqual(ids({kind:'step',id:'s2'}),[]);
  assert.deepEqual(ids({kind:'step',id:'s3'}),['s4','s6']);assert.deepEqual(ids({kind:'step',id:'s4'}),['s5']);assert.deepEqual(ids({kind:'step',id:'s6'}),['s7']);assert.deepEqual(ids({kind:'step',id:'s7'}),['s8','s9']);assert.deepEqual(ids({kind:'step',id:'s5'}),[]);assert.deepEqual(ids({kind:'step',id:'s8'}),[]);
  assert.deepEqual(steps.filter(s=>forks(steps,s.id)).map(s=>s.id),['s3','s7']);assert.deepEqual(steps.filter(s=>startsBranch(steps,s)).map(s=>s.id),['s4','s6','s8','s9']);
  // Every step appears exactly once, and the parent used for reveal agrees with where it is listed.
  const seen:string[]=[];const walk=(parent:{kind:'goal'|'step';id:string})=>{for(const s of shownChildren(steps,parent)){seen.push(s.id);assert.deepEqual(shownParent(steps,s),parent);walk({kind:'step',id:s.id});}};walk({kind:'goal',id:'g'});
  assert.deepEqual(seen.sort(),steps.map(s=>s.id).sort());
  // Depth grows only at forks: a fork's alternatives are one level down and the rest of each alternative one more.
  const depth=(s:{id:string;goalId:string;parentStepId?:string;sequence:number})=>{let n=0;for(let p=shownParent(steps,s);p.kind==='step';p=shownParent(steps,steps.find(x=>x.id===p.id)!)){n++;}return n;};
  assert.deepEqual(steps.map(depth),[0,0,0,1,2,1,2,3,3]);
  // A route counts every step below its first step; the current step is on the routes of all its ancestors only.
  assert.deepEqual(['s4','s6','s8'].map(id=>branchSize(steps,id)),[2,4,1]);assert.deepEqual(['s4','s6','s8','s9'].map(id=>onBranch(steps,id,'s9')),[false,true,false,true]);assert.equal(onBranch(steps,'s6',undefined),false);
  // Two first steps under one goal are two routes as well: each heads its own group at the goal level.
  const two=[step(1),step(2,1),step(3)];assert.deepEqual(shownChildren(two,{kind:'goal',id:'g'}).map(s=>s.id),['s1','s3']);assert.deepEqual(shownChildren(two,{kind:'step',id:'s1'}).map(s=>s.id),['s2']);
  assert.deepEqual(shownParent(two,two[1]),{kind:'step',id:'s1'});assert.deepEqual(two.filter(s=>startsBranch(two,s)).map(s=>s.id),['s1','s3']);
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
test('bulk paste splits lists and blocks, labels by text shape, and adds siblings in one save',async()=>{const {splitBulk}=await import('../../src/domain/bulkPaste');
  const text='Rte_Read_A\r\nsrc/app/secret_like.c:42\r\nFoo()\r\n\r\nif (a < 60 && p->ok)\r\n\r\n  x = a > b;\r\n  return x;\r\n\r\n\r\np->v >= 3\n\nvalue = 1;';
  assert.deepEqual(splitBulk(text).items,[{kind:'function',text:'Rte_Read_A'},{kind:'path',text:'src/app/secret_like.c:42'},{kind:'function',text:'Foo()'},{kind:'condition',text:'if (a < 60 && p->ok)'},{kind:'code',text:'  x = a > b;\n  return x;'},{kind:'condition',text:'p->v >= 3'},{kind:'code',text:'value = 1;'}]);
  assert.deepEqual(splitBulk(' \n\n').items,[]);assert.equal(splitBulk('p->v').items[0].kind,'code');
  const many=splitBulk(Array.from({length:150},(_,i)=>`f${i}`).join('\n'));assert.equal(many.items.length,100);assert.equal(many.truncated,true);
  const {s,root}=await initial(),rev=s.document.revision,ids=await s.addMany([{capture:{snippet:'Foo',contextBefore:'',contextAfter:''},reason:'함수명: Foo'},{capture:{snippet:'a < 1',contextBefore:'',contextAfter:''},reason:'조건식: a < 1'}]);
  const d=s.document;assert.equal(d.revision,rev+1);assert.equal(d.currentStepId,root);assert.deepEqual(ids.map(i=>d.steps.find(x=>x.id===i)!.parentStepId),[root,root]);assert.deepEqual(ids.map(i=>d.steps.find(x=>x.id===i)!.sequence),[2,3]);
  assert.equal(d.relations.filter(r=>r.fromStepId===root).length,2);assert.ok(ids.every(i=>d.anchors.find(a=>a.id===d.steps.find(x=>x.id===i)!.codeAnchorId)!.state==='snippet_only'));validate(d);
  await assert.rejects(s.addMany([]));await assert.rejects(s.addMany([{capture:{snippet:'x',contextBefore:'',contextAfter:''},reason:' '}]));assert.equal(s.document.steps.length,d.steps.length);});
test('exports of one goal: handover text with or without code, a self-contained diagram page and a graph',async()=>{const {exportGoal,exportFileName}=await import('../../src/ui/exporter');
  const {s,root}=await initial();const child=await s.add({...capture(),snippet:'a ``` b\n<script>x</script>'},'갈래 하나 <b>&',undefined,{type:'call',uncertainty:[]});
  await s.edit(child,{...s.document.steps.find(x=>x.id===child)!,status:'deferred',hypothesis:'# 제목 아님\n둘째 줄',nextAction:'순서 확인'});await s.evidence(child,{kind:'ct_observed',text:'값 확인',executionLabel:'CT-가상-01',observedAt:'2026-11-10T01:00:00.000Z',memo:'메모'});
  await s.select(root);const other=await s.add({snippet:'manual "note"',contextBefore:'',contextAfter:''},'다른 갈래');await s.add({snippet:'next()',contextBefore:'',contextAfter:''},'갈래 안 다음');await s.createGoal({title:'다른 목표',description:''},capture());await s.add(capture(),'secret_other_goal_step');
  const d=s.document,goal=d.steps.find(x=>x.id===root)!.goalId,at='2026. 11. 13.';
  const md=exportGoal(d,goal,'handover',at);
  assert.ok(md.startsWith('# 조사 기록: '));assert.ok(md.includes('- 단계 4개 (조사 중 3, 확인 0, 보류 1, 제외 0)'));assert.ok(md.includes('실제 실행 순서가 아닙니다'));
  assert.match(md,/\n- 1\. .* — 조사 중\n  - 2\. 갈래 하나 <b>& — 보류\n  - 3\. 다른 갈래 — 조사 중\n    - 4\. 갈래 안 다음 — 조사 중\n/);assert.ok(md.includes('- 이어진 곳: 1번 단계 (호출)'));assert.ok(md.includes('- 위치: a.c:3'));assert.ok(md.includes('- 위치: 파일 미연결'));
  assert.ok(md.includes('- 가정:\n  > # 제목 아님\n  > 둘째 줄'));assert.ok(md.includes('- 근거 — CT 실측 · CT-가상-01 · 2026-11-10T01:00:00.000Z:\n  > 값 확인\n  > 메모'));assert.ok(md.includes('````c\na ``` b\n<script>x</script>\n````'),'fence outlasts backticks in code');
  assert.ok(!md.includes('secret_other_goal_step'),'other goals are not exported');assert.ok(!md.includes('file:///'),'no absolute file uri');  const plain=exportGoal(d,goal,'handoverNoCode',at);assert.ok(!plain.includes('<script>'));assert.ok(!plain.includes('```'));assert.ok(plain.includes('- 다음 할 일:\n  > 순서 확인'));
  const html=exportGoal(d,goal,'diagram',at);assert.ok(html.startsWith('<!DOCTYPE html>'));assert.ok(html.includes("default-src 'none'"));assert.ok(!/<script|https?:|src=|href=/.test(html),'no script and nothing fetched');
  assert.ok(html.includes('갈래 하나 &lt;b&gt;&amp;'));assert.ok(html.includes('&lt;script&gt;x&lt;/script&gt;'));assert.ok(html.includes('class="node deferred"'));assert.ok(html.includes('<span class="badge">호출</span>'));
  assert.equal((html.match(/<li>/g)??[]).length,5);assert.equal((html.match(/<ul>/g)??[]).length,3);assert.ok(!html.includes('secret_other_goal_step'));
  const graph=exportGoal(d,goal,'mermaid',at);assert.ok(graph.includes('```mermaid\nflowchart TD\n  goal(["목표: '));assert.ok(graph.includes('  s1 -->|호출| s2'));assert.ok(graph.includes('  s1 --> s3'));assert.ok(graph.includes('  s3 --> s4'));assert.ok(graph.includes('  goal --> s1'));
  assert.match(graph,/  s2\["2\. 갈래 하나  b  <br\/>보류 · a\.c:3"\]:::deferred/);assert.ok(graph.includes("  s3[\"3. 다른 갈래<br/>조사 중 · 파일 미연결\"]:::investigating"));assert.ok(!graph.includes('<script>'));
  assert.throws(()=>exportGoal(d,'missing','handover',at));
  assert.equal(exportFileName('a/b: "c"? .. d','handover','2026-11-13'),'조사-a_b_c_d-2026-11-13.md');assert.equal(exportFileName(' / ','diagram','2026-11-13'),'조사-목표-2026-11-13.html');assert.equal(exportFileName('목표','mermaid','2026-11-13'),'조사-목표-2026-11-13-graph.md');
});
