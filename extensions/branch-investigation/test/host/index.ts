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
      assert.equal(d.steps.length,expected.steps);assert.equal(d.currentStepId,expected.current);assert.equal(d.evidence[0].executionLabel,'CT-가상-01');assert.ok(d.steps.some(s=>s.status==='deferred'&&s.nextAction.includes('갱신 순서')));assert.ok(d.steps.some(s=>s.snippet.includes('수동')));assert.equal(d.revision,expected.revision);assert.equal(app.analysis.available,false);console.log('PASS Host: restart restores goal / current step / alternatives / evidence');return;
    }
    // Real command captures selection before the first prompt. Only prompt answers are deterministic.
    const original=await select('unicode.c','/*한글 😀*/ if (a < 60) return 0;\r\n  else return 1;');
    app.setPromptsForTests({input:async()=>undefined,snippet:async()=>undefined});await command('addSelection');assert.equal(service.document.steps.length,0);assert.equal(service.document.goals.length,0);
    let answers=['정상 경로 통과','else 앞선 조건이 거짓이어야 함을 수동 조사','선택 당시 분기와 입력 조건을 보존'];let switched=false;
    app.setPromptsForTests({input:async()=>{if(!switched){switched=true;await select('producer.c','Rte_Write_Struct_State(&built)');}return answers.shift();},snippet:async()=>undefined});
    await command('addSelection');let d=service.document;assert.equal(d.steps.length,1);const first=d.steps[0],anchor=d.anchors.find(a=>a.id===first.codeAnchorId)!;
    assert.equal(first.snippet,original.snippet);assert.equal(anchor.documentVersion,original.doc.version);assert.equal(vscode.Uri.parse(anchor.fileUri!).fsPath.toLowerCase(),vscode.Uri.file(path.join(root,'unicode.c')).fsPath.toLowerCase());assert.equal(anchor.range!.start.character,2);assert.equal(anchor.range!.end.character,16);assert.equal(resolutionState(),'verified');assert.equal(first.goalSnapshot.target.kind,'manual');
    const rootItems=app.tree!.getChildren();assert.equal(rootItems.length,1);assert.equal(app.tree!.getChildren(rootItems[0]).length,1);assert.ok(app.tree!.getTreeItem({kind:'step',id:first.id}).command);
    console.log('PASS Host: selection / prompt editor switch / Unicode CRLF / tree / source navigation');
    const before=d.revision;app.setPromptsForTests({input:async()=>'',snippet:async()=>undefined});await command('addSelection');assert.equal(service.document.revision,before);
    app.setPromptsForTests({input:async()=> '분기에 쓰이는 입력 출처 확인',snippet:async()=>undefined});await select('consumer.c','Rte_Read_Struct_State(&b)');await command('addSelection');const reader=service.document.currentStepId!;
    app.setPromptsForTests({input:async()=> '이 값이 읽힐 가능성 — 연결/초기값/Runnable 순서 미확인',snippet:async()=>undefined});await select('producer.c','Rte_Write_Struct_State(&built)');await command('addSelection');const writer=service.document.currentStepId!;
    const step=service.document.steps.find(s=>s.id===writer)!;await service.edit(writer,{...step,status:'deferred',hypothesis:'이 값이 읽힐 가능성',requiredConditions:'앞선 조건 거짓 필요',nextAction:'초기화와 갱신 순서 확인'});
    await command('goParent');assert.equal(service.document.currentStepId,reader);app.setPromptsForTests({input:async()=> '다른 입력 반환값 조사',snippet:async()=>undefined});await select('consumer.c','Struct_ConsumePointer(&local)');await command('addSelection');const sibling=service.document.steps.find(s=>s.id===service.document.currentStepId)!;assert.equal(sibling.parentStepId,step.parentStepId);assert.equal(service.document.steps.find(s=>s.id===writer)!.status,'deferred');
    await service.evidence(writer,{kind:'ct_observed',text:'사람이 가상 결과 확인',executionLabel:'CT-가상-01',observedAt:'2026-11-10T01:00:00.000Z',memo:'실제 CT 자동 실행 없음'});
    const count=[service.document.steps.length,service.document.relations.length];await command('navigateBack');await command('navigateForward');await command('openStep',writer);assert.deepEqual([service.document.steps.length,service.document.relations.length],count);
    assert.equal(resolutionState(),'verified');assert.equal(vscode.window.activeTextEditor!.document.uri.fsPath.toLowerCase(),path.join(root,'producer.c').toLowerCase());assert.equal(vscode.window.activeTextEditor!.document.getText(vscode.window.activeTextEditor!.selection),'Rte_Write_Struct_State(&built)');
    console.log('PASS Host: RTE manual investigation / deferred sibling / CT provenance / back-forward');
    const edited=await select('unicode.c','else return 1;');await edited.editor.edit(b=>b.insert(new vscode.Position(0,0),'// unsaved\r\n'));assert.equal(edited.doc.isDirty,true);await command('openStep',first.id);assert.equal(resolutionState(),'needs_review');assert.equal(service.document.steps[0].snippet,original.snippet);
    await fs.unlink(path.join(root,'producer.c'));await command('openStep',writer);assert.equal(resolutionState(),'missing');
    app.setPromptsForTests({input:async()=> '파일 미연결 수동 조사',snippet:async()=> '수동 스니펫\n조건 가설'});await command('addSnippet');const manual=service.document.steps.at(-1)!;assert.equal(manual.snippet,'수동 스니펫\n조건 가설');await command('openStep',manual.id);assert.equal(resolutionState(),'snippet_only');
    assert.throws(()=>decodeDetailMessage({type:'execute',stepId:manual.id,command:'bad'},manual.id));assert.throws(()=>decodeDetailMessage({type:'save',stepId:first.id,edit:{}},manual.id));
    d=service.document;await fs.writeFile(path.join(base,'expected.json'),JSON.stringify({steps:d.steps.length,current:d.currentStepId,revision:d.revision}));
    console.log('PASS Host: changed live buffer / missing file / manual snippet / message allowlist');
  }finally{await app.close();}
}
