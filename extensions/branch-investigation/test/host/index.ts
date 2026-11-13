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
    console.log('PASS Host: RTE manual investigation / deferred sibling / CT provenance / back-forward');
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
