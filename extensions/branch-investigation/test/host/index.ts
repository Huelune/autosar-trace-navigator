import * as assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as vscode from 'vscode';
import type { InvestigationController } from '../../src/extension';
import { decodeDetailMessage } from '../../src/ui/detailsPanel';

export async function run():Promise<void>{
  const phase=process.env.BRANCH_HOST_PHASE!,base=process.env.BRANCH_HOST_BASE!,root=vscode.workspace.workspaceFolders![0].uri.fsPath;
  const ext=vscode.extensions.getExtension<InvestigationController>('huelune.branch-investigation')!;assert.ok(ext);
  if(process.env.BRANCH_EXTENSION_PATH){assert.equal(ext.extensionPath.toLowerCase(),process.env.BRANCH_EXTENSION_PATH.toLowerCase());}
  if(phase==='untrusted'){
    assert.equal(vscode.workspace.isTrusted,false);let rejected=false;try{await ext.activate();}catch{rejected=true;}assert.ok(rejected||!ext.exports?.service);console.log('PASS Host: Restricted Mode refuses active recording');return;
  }
  const app=await ext.activate();assert.ok(app.service);const service=app.service!; const resolutionState=()=>app.lastResolution?.state;
  const command=(name:string,...args:unknown[])=>vscode.commands.executeCommand('branchInvestigation.'+name,...args);
  const select=async(file:string,needle:string)=>{const doc=await vscode.workspace.openTextDocument(vscode.Uri.file(path.join(root,file)));const editor=await vscode.window.showTextDocument(doc,{viewColumn:vscode.ViewColumn.One});const i=doc.getText().indexOf(needle);assert.ok(i>=0,needle);editor.selection=new vscode.Selection(doc.positionAt(i),doc.positionAt(i+needle.length));return {doc,editor,range:editor.selection,snippet:needle};};
  try{
    if(phase==='restart'){
      const expected=JSON.parse(await fs.readFile(path.join(base,'expected.json'),'utf8'));const d=service.document;
      assert.equal(d.steps.length,expected.steps);assert.equal(d.currentStepId,expected.current);assert.equal(d.evidence[0].executionLabel,'CT-가상-01');assert.ok(d.steps.some(s=>s.status==='deferred'&&s.nextAction.includes('갱신 순서')));assert.ok(d.steps.some(s=>s.snippet.includes('수동')));assert.equal(d.revision,expected.revision);console.log('PASS Host: restart restores goal / current step / alternatives / evidence');return;
    }
    // Real command captures selection before the first prompt. Only prompt answers are deterministic.
    const original=await select('unicode.c','/*한글 😀*/ if (a < 60) return 0;\r\n  else return 1;');
    app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined});await command('addSelection');assert.equal(service.document.steps.length,0);assert.equal(service.document.goals.length,0);
    let answers=['정상 경로 통과','else 앞선 조건이 거짓이어야 함을 수동 조사','선택 당시 분기와 입력 조건을 보존'];let switched=false;
    app.setPromptsForTests({input:async()=>{if(!switched){switched=true;await select('producer.c','Rte_Write_Struct_State(&built)');}return answers.shift();},snippet:async()=>undefined});
    await command('addSelection');let d=service.document;assert.equal(d.steps.length,1);const first=d.steps[0],anchor=d.anchors.find(a=>a.id===first.codeAnchorId)!;
    assert.equal(first.snippet,original.snippet);assert.equal(anchor.documentVersion,original.doc.version);assert.equal(vscode.Uri.parse(anchor.fileUri!).fsPath.toLowerCase(),vscode.Uri.file(path.join(root,'unicode.c')).fsPath.toLowerCase());assert.equal(anchor.range!.start.character,2);assert.equal(anchor.range!.end.character,16);assert.equal(resolutionState(),'verified');assert.equal(app.details.isOpen,false,'adding a step must not open the detail panel');assert.equal(first.goalSnapshot.target.kind,'manual');
    // A click on a step only goes to its code. The detail panel opens from its own command and nowhere else.
    await command('openStep',first.id);assert.equal(app.details.isOpen,false);await command('editStep',first.id);assert.equal(app.details.isOpen,true);app.details.dispose();assert.equal(app.details.isOpen,false);
    const rootItems=app.tree!.getChildren();assert.equal(rootItems.length,1);assert.equal(app.tree!.getChildren(rootItems[0]).length,1);assert.ok(app.tree!.getTreeItem({kind:'step',id:first.id}).command);
    console.log('PASS Host: selection / prompt editor switch / Unicode CRLF / tree / source navigation');
    const before=service.document.revision;app.setPromptsForTests({input:async()=>'',snippet:async()=>undefined});await command('addSelection');assert.equal(service.document.revision,before);
    // The reason prompt starts from the selected code, so a step can be found in the tree by its code.
    let offeredReason:string|undefined='unset';app.setPromptsForTests({input:async o=>{offeredReason=o.value;return '분기에 쓰이는 입력 출처 확인';},snippet:async()=>undefined});await select('consumer.c','Rte_Read_Struct_State(&b)');await command('addSelection');const reader=service.document.currentStepId!;assert.equal(offeredReason,'Rte_Read_Struct_State(&b)');
    app.setPromptsForTests({input:async()=> '이 값이 읽힐 가능성 — 연결/초기값/Runnable 순서 미확인',snippet:async()=>undefined});await select('producer.c','Rte_Write_Struct_State(&built)');await command('addSelection');const writer=service.document.currentStepId!;
    const step=service.document.steps.find(s=>s.id===writer)!;await service.edit(writer,{...step,status:'deferred',hypothesis:'이 값이 읽힐 가능성',requiredConditions:'앞선 조건 거짓 필요',nextAction:'초기화와 갱신 순서 확인'});
    await command('goParent');assert.equal(service.document.currentStepId,reader);app.setPromptsForTests({input:async()=> '다른 입력 반환값 조사',snippet:async()=>undefined});await select('consumer.c','Struct_ConsumePointer(&local)');await command('addSelection');const sibling=service.document.steps.find(s=>s.id===service.document.currentStepId)!;assert.equal(sibling.parentStepId,step.parentStepId);assert.equal(service.document.steps.find(s=>s.id===writer)!.status,'deferred');
    await service.evidence(writer,{kind:'ct_observed',text:'사람이 가상 결과 확인',executionLabel:'CT-가상-01',observedAt:'2026-11-10T01:00:00.000Z',memo:'실제 CT 자동 실행 없음'});
    const count=[service.document.steps.length,service.document.relations.length];await command('navigateBack');await command('navigateForward');await command('openStep',writer);assert.deepEqual([service.document.steps.length,service.document.relations.length],count);
    assert.equal(resolutionState(),'verified');assert.equal(vscode.window.activeTextEditor!.document.uri.fsPath.toLowerCase(),path.join(root,'producer.c').toLowerCase());assert.equal(vscode.window.activeTextEditor!.document.getText(vscode.window.activeTextEditor!.selection),'Rte_Write_Struct_State(&built)');
    {// Search lists every step; typing is the quick pick's own filter. Picking one visits it and creates nothing.
      const counts=[service.document.steps.length,service.document.relations.length];let rows:{label:string;description?:string;detail?:string}[]=[];
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,pick:async items=>{rows=items;return items.find(i=>i.description?.startsWith('보류'));}});await command('openStep',reader);await command('searchSteps');
      assert.equal(rows.length,counts[0]);const deferred=rows.filter(r=>r.description?.startsWith('보류'));assert.equal(deferred.length,1);assert.ok(deferred[0].description!.includes('정상 경로 통과')&&deferred[0].description!.includes('producer.c:'));assert.ok(deferred[0].detail!.includes('다음 할 일: 초기화와 갱신 순서 확인'));
      assert.equal(service.document.currentStepId,writer);assert.equal(resolutionState(),'verified');assert.deepEqual([service.document.steps.length,service.document.relations.length],counts);
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,pick:async()=>undefined});const visits=service.document.navigationEvents.length;await command('searchSteps');assert.equal(service.document.currentStepId,writer);assert.equal(service.document.navigationEvents.length,visits);}
    {// Two routes from one step: the fork lists the first step of each route, and each first step says how long its route is and where the work is.
      const item=(id:string)=>app.tree!.getTreeItem({kind:'step',id}),text=(id:string)=>`${item(id).label}|${item(id).description}`;
      assert.deepEqual(app.tree!.getChildren({kind:'step',id:reader}).map(e=>e.id),[writer,sibling.id]);assert.match(text(writer),/^↳ .*\|▶ 보류 · 갈래 1단계$/);assert.match(text(sibling.id),/^↳ .*\|조사 중 · 갈래 1단계$/);
      app.setPromptsForTests({input:async()=>'갈래 안의 다음 단계',snippet:async()=>'route_next();'});await command('openStep',sibling.id);await command('addSnippet');const deeper=service.document.currentStepId!;
      assert.deepEqual(app.tree!.getChildren({kind:'step',id:sibling.id}).map(e=>e.id),[deeper]);assert.deepEqual(app.tree!.getParent({kind:'step',id:deeper}),{kind:'step',id:sibling.id});
      assert.match(text(sibling.id),/\|조사 중 · 갈래 2단계 · ▶ 진행 중$/);assert.equal(item(sibling.id).collapsibleState,vscode.TreeItemCollapsibleState.Expanded);assert.match(text(writer),/\|보류 · 갈래 1단계$/);
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,confirm:async()=>true});await command('deleteStep',{kind:'step',id:deeper});await command('openStep',writer);}
    console.log('PASS Host: RTE manual investigation / deferred sibling / CT provenance / back-forward / search visits the picked step only');
    {// Bulk paste: every split piece is offered ticked; only what stays ticked becomes a sibling step under the current step, which stays current.
      await command('openStep',writer);const counts=[service.document.steps.length,service.document.relations.length,service.document.revision];let shown:string[]=[];
      const pasted='Rte_Read_Struct_State\r\nconsumer.c:3\r\n\r\nif (a < 60)\r\n\r\n  local = 1;\r\n  return local;';
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>pasted,pickMany:async items=>{shown=items.map(i=>`${i.label}|${i.description??''}|${i.picked}`);return undefined;}});await command('addBulk');
      assert.deepEqual(shown,['함수명: Rte_Read_Struct_State||true','경로: consumer.c:3||true','조건식: if (a < 60)||true','코드: local = 1; return local;|2줄|true']);assert.deepEqual([service.document.steps.length,service.document.relations.length,service.document.revision],counts,'cancelled preview records nothing');
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>pasted,pickMany:async items=>items.filter(i=>!i.label.startsWith('경로'))});await command('addBulk');
      const d2=service.document,made=d2.steps.slice(-3);assert.equal(d2.steps.length,counts[0]+3);assert.equal(d2.revision,counts[2]+1);assert.equal(d2.currentStepId,writer);assert.ok(made.every(m=>m.parentStepId===writer));
      assert.deepEqual(made.map(m=>m.reason),['함수명: Rte_Read_Struct_State','조건식: if (a < 60)','코드: local = 1; return local;']);assert.equal(made[2].snippet,'  local = 1;\n  return local;');
      await command('openStep',made[0].id);assert.equal(resolutionState(),'snippet_only');
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,confirm:async()=>true});for(const m of made){await command('deleteStep',{kind:'step',id:m.id});}await command('openStep',writer);assert.equal(service.document.steps.length,counts[0]);
      console.log('PASS Host: bulk paste previews split pieces / cancel records nothing / ticked pieces become sibling steps in one save');}
    {// Saving a step keeps the screen as it was: the code does not scroll and another sidebar tab (Search) is not replaced by the tree.
      const wait=()=>new Promise(r=>setTimeout(r,300));await fs.writeFile(path.join(root,'long.c'),Array.from({length:300},(_,i)=>`int line_${i};`).join('\n'));
      const far=await select('long.c','int line_205;');far.editor.revealRange(new vscode.Range(200,0,200,0),vscode.TextEditorRevealType.AtTop);await vscode.commands.executeCommand('workbench.view.search');await wait();
      const top=far.editor.visibleRanges[0].start.line;assert.ok(top>150,'scrolled before saving');assert.equal(app.view!.visible,false);
      app.setPromptsForTests({input:async()=>'화면 유지 확인',snippet:async()=>undefined,confirm:async()=>true});await command('addSelection');await wait();const kept=service.document.currentStepId!;assert.notEqual(kept,writer);
      assert.equal(vscode.window.activeTextEditor!.visibleRanges[0].start.line,top,'saving must not scroll the code');assert.equal(app.view!.visible,false,'saving must not switch the sidebar tab');
      assert.equal(vscode.window.activeTextEditor!.document.getText(vscode.window.activeTextEditor!.selection),'int line_205;');
      await command('deleteStep',{kind:'step',id:kept});await command('openStep',writer);assert.equal(service.document.currentStepId,writer);
      console.log('PASS Host: saving a step keeps the code scroll position and the open sidebar tab');}
    if(process.env.BRANCH_HOST_PYTHON){
      // The real engine process on the virtual workspace. Candidates are only offered; a pick plus a reason records a step.
      app.setAnalysisSettingsForTests(()=>({python:process.env.BRANCH_HOST_PYTHON!,paths:['.']}));await select('consumer.c','Rte_Read_Struct_State(&b)');
      let offered:string[]=[];app.setPromptsForTests({input:async()=>'엔진 후보의 Writer 조사',snippet:async()=>undefined,pick:async items=>{offered=items.map(i=>i.label);return undefined;}});
      const quiet=service.document.revision;await command('traceRelated');assert.equal(service.document.revision,quiet);assert.ok(offered.some(l=>l.startsWith('RTE 데이터')),'RTE candidate offered');
      app.setPromptsForTests({input:async()=>'엔진 후보의 Writer 조사',snippet:async()=>undefined,pick:async items=>items.find(i=>i.label.startsWith('RTE 데이터'))});await command('traceRelated');
      const linked=service.document.steps.find(s=>s.id===service.document.currentStepId)!,edge=service.document.relations.find(r=>r.toStepId===linked.id)!;
      assert.equal(linked.parentStepId,writer);assert.equal(edge.type,'data_dependency');assert.ok(edge.uncertainty.includes('name_only_connection'));assert.match(linked.snippet,/^Rte_Write_Struct_State\(/);
      assert.equal(vscode.window.activeTextEditor!.document.uri.fsPath.toLowerCase(),path.join(root,'producer.c').toLowerCase());assert.equal(vscode.window.activeTextEditor!.document.getText(vscode.window.activeTextEditor!.selection),linked.snippet);
      console.log('PASS Host: engine candidates offered / cancel records nothing / picked RTE writer becomes a linked step');
      // Cursor on a traced member: value sources come first; a picked one becomes a data_dependency step under the current step.
      const member=await select('consumer.c','b.a');member.editor.selection=new vscode.Selection(member.range.start,member.range.start);const parent=service.document.currentStepId!;
      let labels:string[]=[],title='';app.setPromptsForTests({input:async()=>'b.a 값의 출처 조사',snippet:async()=>undefined,pick:async(items,options)=>{labels=items.map(i=>i.label);title=options.title??'';return items.find(i=>i.label.startsWith('값 출처'));}});
      await command('traceRelated');assert.ok(title.includes('b.a'),'variable shown in title');assert.ok(labels[0].startsWith('값 출처'),'value sources listed first');assert.ok(labels.some(l=>l.startsWith('호출')));
      const valueStep=service.document.steps.find(s=>s.id===service.document.currentStepId)!,valueEdge=service.document.relations.find(r=>r.toStepId===valueStep.id)!;
      assert.equal(valueStep.parentStepId,parent);assert.equal(valueEdge.type,'data_dependency');assert.ok(valueEdge.uncertainty.includes('value_source_candidate'));
      // Cursor inside a branch body: the condition to reach it is offered with the needed truth value and recorded as a prerequisite, not a data relation.
      const body=await select('unicode.c','return 0;');body.editor.selection=new vscode.Selection(body.range.start,body.range.start);
      app.setPromptsForTests({input:async()=>'이 줄에 도달하려면 조건이 참이어야 함',snippet:async()=>undefined,pick:async items=>{labels=items.map(i=>i.label);return items.find(i=>i.label.startsWith('실행 조건'));}});
      await command('traceRelated');assert.ok(labels.some(l=>l==='실행 조건: 참 필요 · (a < 60)'),labels.join(' | '));
      const conditionStep=service.document.steps.find(s=>s.id===service.document.currentStepId)!,conditionEdge=service.document.relations.find(r=>r.toStepId===conditionStep.id)!;
      assert.equal(conditionStep.snippet,'(a < 60)');assert.equal(conditionEdge.type,'manual');assert.ok(conditionEdge.uncertainty.includes('execution_requirement_true'));assert.ok(conditionEdge.uncertainty.includes('condition_satisfiability_not_proven'));
      console.log('PASS Host: cursor variable value sources first / execution condition with needed truth recorded as prerequisite');
      {// Function search: one engine run serves repeated searches; a changed C file drops the kept result. Picking goes to the signature and records nothing.
        const wait=(ms:number)=>new Promise(r=>setTimeout(r,ms)),quiet=[service.document.steps.length,service.document.revision];let names:string[]=[],title='';
        app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,pick:async(items,options)=>{names=items.map(i=>i.label);title=options.title??'';return undefined;}});
        app.analysisCache.clear();const runs=app.engineRuns;await command('searchFunctions');await command('searchFunctions');assert.equal(app.engineRuns,runs+1,'second search uses the kept list');
        assert.ok(names.includes('Struct_ConsumePointer'),'defined function listed');assert.deepEqual(names,[...names].sort((a,b)=>a.toLowerCase()<b.toLowerCase()?-1:a.toLowerCase()>b.toLowerCase()?1:0));assert.ok(title.includes(`함수 ${names.length}개`));
        app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,pick:async items=>items.find(i=>i.label==='Struct_ConsumePointer')});await command('searchFunctions');
        const at=vscode.window.activeTextEditor!;assert.match(at.document.getText(at.selection),/Struct_ConsumePointer\s*\(/);assert.ok(!at.document.getText(at.selection).includes('{'));assert.deepEqual([service.document.steps.length,service.document.revision],quiet);
        await fs.writeFile(path.join(root,'added.c'),'void Host_AddedFunction(void)\n{\n}\n');for(let i=0;i<50&&app.analysisCache.size;i++){await wait(200);}assert.equal(app.analysisCache.size,0,'a changed source file drops kept results');
        app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,pick:async items=>{names=items.map(i=>i.label);return undefined;}});await command('searchFunctions');assert.equal(app.engineRuns,runs+2);assert.ok(names.includes('Host_AddedFunction'));
        console.log('PASS Host: function search lists scope definitions / kept list reused / source change re-reads / pick only navigates');}
    }else{console.log('SKIP Host: engine link not run (no Python with the engine was found)');}
    // Deleting asks first; declining changes nothing. A deleted subtree is gone after restart as well (expected.json is written below).
    {const before=service.document,target=before.steps.find(s=>s.id===sibling.id)!;let asked='';
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,confirm:async m=>{asked=m;return false;}});await command('deleteStep',{kind:'step',id:target.id});assert.ok(asked.includes(`${target.sequence}번 단계`));assert.equal(service.document.revision,before.revision);
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,confirm:async()=>true});await command('deleteStep',{kind:'step',id:target.id});assert.ok(!service.document.steps.some(s=>s.id===target.id));assert.equal(service.document.steps.length,before.steps.length-1);
      app.setPromptsForTests({input:async()=>'지울 목표의 단계',snippet:async()=>'임시 메모',confirm:async()=>true});await command('createGoal');const extra=service.document.currentGoalId!;assert.notEqual(extra,before.currentGoalId);
      await command('deleteGoal',{kind:'goal',id:extra});assert.ok(!service.document.goals.some(g=>g.id===extra));assert.equal(service.document.currentGoalId,undefined);await command('switchGoal',before.currentGoalId);await command('openStep',writer);
      console.log('PASS Host: delete asks first / declined keeps everything / step subtree and goal removed');}
    const edited=await select('unicode.c','else return 1;');await edited.editor.edit(b=>b.insert(new vscode.Position(0,0),'// unsaved\r\n'));assert.equal(edited.doc.isDirty,true);await command('openStep',first.id);assert.equal(resolutionState(),'needs_review');assert.equal(service.document.steps[0].snippet,original.snippet);
    {// Anchor candidates: the unsaved line above moved the saved text one line down. It is offered, never applied without the confirmation.
      const stepOf=()=>service.document.steps.find(s=>s.id===first.id)!,oldAnchor=stepOf().codeAnchorId,goalBefore=JSON.stringify(stepOf().goalSnapshot);let offered:string[]=[];
      const pick=async<T extends vscode.QuickPickItem>(items:T[])=>{offered=items.map(i=>`${i.label}|${i.description}`);return items[0];};
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,pick,confirm:async()=>false});await command('repairAnchor',first.id);
      assert.deepEqual(offered,['후보 L3:3|앞뒤 문맥 일치 · 저장 위치에서 +1줄','현재 선택 범위로 재연결|L4:3']);assert.equal(stepOf().codeAnchorId,oldAnchor,'declined confirmation relinks nothing');
      app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined,pick,confirm:async()=>true});await command('repairAnchor',first.id);
      const relinked=service.document.anchors.find(a=>a.id===stepOf().codeAnchorId)!;assert.notEqual(relinked.id,oldAnchor);assert.deepEqual(relinked.range,{start:{line:2,character:2},end:{line:3,character:16}});
      assert.equal(resolutionState(),'verified');assert.equal(stepOf().snippet,original.snippet);assert.equal(JSON.stringify(stepOf().goalSnapshot),goalBefore);
      console.log('PASS Host: moved text offered as anchor candidate / declined keeps anchor / confirmed relinks with snippet and goal kept');}
    await fs.unlink(path.join(root,'producer.c'));await command('openStep',writer);assert.equal(resolutionState(),'missing');
    app.setPromptsForTests({input:async()=> '파일 미연결 수동 조사',snippet:async()=> '수동 스니펫\n조건 가설'});await command('addSnippet');const manual=service.document.steps.at(-1)!;assert.equal(manual.snippet,'수동 스니펫\n조건 가설');await command('openStep',manual.id);assert.equal(resolutionState(),'snippet_only');
    assert.throws(()=>decodeDetailMessage({type:'execute',stepId:manual.id,command:'bad'},manual.id));assert.throws(()=>decodeDetailMessage({type:'save',stepId:first.id,edit:{}},manual.id));
    d=service.document;await fs.writeFile(path.join(base,'expected.json'),JSON.stringify({steps:d.steps.length,current:d.currentStepId,revision:d.revision}));
    console.log('PASS Host: changed live buffer / missing file / manual snippet / message allowlist');
  }finally{await app.close();}
}
