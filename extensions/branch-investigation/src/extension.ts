import * as vscode from 'vscode';
import * as path from 'node:path';
import { pathToFileURL } from 'node:url';
import { CapturedCode, clone, CodeAnchor, InvestigationStep, statusLabels, Status } from './domain/model';
import { InvestigationService, GoalInput } from './domain/investigationService';
import { requireValue, validId } from './domain/validation';
import { JsonStore } from './storage/jsonStore';
import { sourcePath } from './storage/paths';
import { resolveAnchor, AnchorResolution } from './navigation/anchorResolver';
import { InvestigationTree, TreeEntry } from './ui/investigationTree';
import { DetailsPanel } from './ui/detailsPanel';
import { snippetInput } from './ui/snippetInput';
import { DisabledTraceAnalysisPort } from './adapters/traceAnalysisPort';

export interface PromptPort { input(options:vscode.InputBoxOptions):Thenable<string|undefined>; snippet():Promise<string|undefined>; }
const defaultPrompts:PromptPort={input:o=>vscode.window.showInputBox(o),snippet:snippetInput};
const manual = (snippet=''):CapturedCode=>({snippet,contextBefore:'',contextAfter:''});
interface SelectionSnapshot { uri:string; version:number; range:vscode.Range; snippet:string; before:string; after:string; }
let active:InvestigationController|undefined;
export class InvestigationController {
  service?:InvestigationService; store?:JsonStore; tree?:InvestigationTree; view?:vscode.TreeView<TreeEntry>;
  readonly analysis=new DisabledTraceAnalysisPort(); readonly status=vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left,20);
  readonly details:DetailsPanel; lastResolution?:AnchorResolution; private root?:string; private prompts=defaultPrompts; private operations:Promise<unknown>=Promise.resolve();
  private decoration=vscode.window.createTextEditorDecorationType({backgroundColor:new vscode.ThemeColor('editor.findMatchHighlightBackground'),border:'1px solid',borderColor:new vscode.ThemeColor('editor.findMatchBorder')});
  constructor(private readonly context:vscode.ExtensionContext){
    this.details=new DetailsPanel(async action=>{const service=this.ready();if(action.type==='save'){await service.edit(action.stepId,action.edit);}else{await service.evidence(action.stepId,action.evidence);}await this.display(action.stepId,false);},e=>void this.failed(e));
    this.status.command='branchInvestigation.retrySave';this.status.show();context.subscriptions.push(this.status,this.details,this.decoration);
  }
  setPromptsForTests(prompts:PromptPort):void{requireValue(this.context.extensionMode===vscode.ExtensionMode.Test,'입력 포트 교체는 Host 테스트에서만 허용합니다.');this.prompts=prompts;}
  private trusted():void{requireValue(vscode.workspace.isTrusted,'신뢰하지 않은 작업 공간에서는 조사 기록을 만들거나 파일을 열지 않습니다.');requireValue(vscode.workspace.workspaceFolders?.length===1&&vscode.workspace.workspaceFolders[0].uri.scheme==='file','단일 로컬 작업 폴더만 지원합니다. 다중 루트·원격 문서는 수동 붙여넣기로만 준비하세요.');}
  ready():InvestigationService{this.trusted();requireValue(this.service,'조사 저장소를 열지 못했습니다. 잠금 또는 백업 복구 명령을 확인하세요.');return this.service;}
  private attach(service:InvestigationService):void{this.service=service;this.tree=new InvestigationTree(service);this.view=vscode.window.createTreeView('branchInvestigation.tree',{treeDataProvider:this.tree,showCollapseAll:true});this.context.subscriptions.push(this.tree,this.view);service.onChange=()=>{this.tree?.refresh();this.updateStatus();};this.updateStatus();}
  private updateStatus():void{this.status.text=this.service?.dirty?(this.service.error?'$(warning) 분기 조사: 저장 실패 · 재시도':'$(sync~spin) 분기 조사: 저장 중'):this.service?'$(list-tree) 분기 조사: 자동 저장':'$(warning) 분기 조사: 저장소 확인 필요';this.status.tooltip=this.service?.error??'조사 순번은 실제 실행 순서가 아닙니다.';}
  async initialize():Promise<void>{this.trusted();this.root=vscode.workspace.workspaceFolders![0].uri.fsPath;this.store??=new JsonStore(this.root);const document=await this.store.open();this.attach(new InvestigationService(document,this.store));if(document.currentStepId){await this.display(document.currentStepId,false);}}
  async failed(error:unknown):Promise<void>{this.updateStatus();const action=await vscode.window.showErrorMessage(`분기 조사 작업 실패: ${error instanceof Error?error.message:'알 수 없는 오류'}`,this.service?.dirty?'저장 재시도':'복구 명령 확인');if(action==='저장 재시도'){void vscode.commands.executeCommand('branchInvestigation.retrySave');}}
  private snapshot():SelectionSnapshot|undefined{
    const editor=vscode.window.activeTextEditor;if(!editor||editor.selection.isEmpty){return undefined;}
    const d=editor.document,r=new vscode.Range(editor.selection.start,editor.selection.end),all=d.getText(),start=d.offsetAt(r.start),end=d.offsetAt(r.end);
    return {uri:d.uri.toString(),version:d.version,range:r,snippet:d.getText(r),before:all.slice(Math.max(0,start-200),start),after:all.slice(end,end+200)};
  }
  private async capture(snapshot:SelectionSnapshot):Promise<CapturedCode>{
    requireValue(this.root,'로컬 작업 폴더가 없습니다.');const real=await sourcePath(this.root,snapshot.uri);
    return {snippet:snapshot.snippet,fileUri:pathToFileURL(real).href,relativePath:path.relative(await import('node:fs/promises').then(f=>f.realpath(this.root!)),real).replaceAll('\\','/'),range:{start:{line:snapshot.range.start.line,character:snapshot.range.start.character},end:{line:snapshot.range.end.line,character:snapshot.range.end.character}},documentVersion:snapshot.version,contextBefore:snapshot.before,contextAfter:snapshot.after};
  }
  private async goalInput():Promise<GoalInput|undefined>{const title=await this.prompts.input({title:'새 조사 목표',prompt:'목표 이름 (필수)',validateInput:v=>v.trim()&&v.length<=200?undefined:'목표 이름을 200자 이내로 입력하세요.'});if(!title?.trim()){return;}const description=await this.prompts.input({title:'목표 설명',prompt:'어떤 분기를 왜 통과하려고 하나요? (선택)',validateInput:v=>v.length<=65536?undefined:'설명이 너무 깁니다.'});return description===undefined?undefined:{title,description};}
  private async add(capture:CapturedCode):Promise<void>{const service=this.ready(),before=service.document;let goal:GoalInput|undefined;if(!before.currentGoalId){goal=await this.goalInput();if(!goal){return;}}
    const reason=await this.prompts.input({title:'현재 조사에 추가',prompt:'이 코드를 선택한 이유 (필수)',validateInput:v=>v.trim()&&v.length<=65536?undefined:'이유를 입력하세요.'});if(!reason?.trim()){return;}
    const current=service.document;requireValue(current.currentGoalId===before.currentGoalId&&current.currentStepId===before.currentStepId,'입력 중 현재 조사가 바뀌었습니다. 다시 선택하세요.');
    const stepId=await service.add(capture,reason,goal);await this.display(stepId,true,false);await this.view?.reveal({kind:'step',id:stepId},{select:true,expand:true,focus:false});
  }
  private async display(stepId:string,openSource:boolean,record=false):Promise<void>{const service=this.ready(),d=service.document,step=d.steps.find(s=>s.id===stepId);requireValue(step,'조사단계가 없습니다.');const anchor=d.anchors.find(a=>a.id===step.codeAnchorId)!;
    this.details.show(step,anchor,'위치 확인 중…',d.evidence.filter(e=>e.stepId===step.id),service.dirty);
    const resolved=await resolveAnchor(this.root!,anchor,async uri=>(await vscode.workspace.openTextDocument(vscode.Uri.parse(uri))).getText());this.lastResolution=resolved;
    this.details.show(step,anchor,resolved.state==='verified'?'저장 범위의 현재 텍스트 일치 (실행 검증 아님)':resolved.message,d.evidence.filter(e=>e.stepId===step.id),service.dirty);
    if(openSource&&resolved.state==='verified'){
      // Recheck the live buffer immediately before selecting; an unsaved edit must not be ignored.
      const checked=await resolveAnchor(this.root!,anchor,async uri=>(await vscode.workspace.openTextDocument(vscode.Uri.parse(uri))).getText());if(checked.state!=='verified'){this.lastResolution=checked;this.details.show(step,anchor,checked.message,d.evidence.filter(e=>e.stepId===step.id),service.dirty);return;}
      const r=new vscode.Range(checked.range.start.line,checked.range.start.character,checked.range.end.line,checked.range.end.character);
      const editor=await vscode.window.showTextDocument(vscode.Uri.parse(checked.fileUri),{viewColumn:vscode.ViewColumn.One,selection:r,preserveFocus:false});editor.setDecorations(this.decoration,[r]);editor.revealRange(r,vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    }
    if(record){await service.select(stepId,openSource&&resolved.state==='verified');}
  }
  private stepId(arg:unknown):string{const candidate=typeof arg==='string'?arg:arg&&typeof arg==='object'?(arg as {id?:unknown}).id:undefined;const value=candidate??this.ready().document.currentStepId;requireValue(validId(value),'조사단계를 선택하세요.');return value;}
  register():void{
    const command=(name:string,action:(arg:unknown,snapshot?:SelectionSnapshot)=>Promise<unknown>,capture=false)=>this.context.subscriptions.push(vscode.commands.registerCommand('branchInvestigation.'+name,(arg:unknown)=>{
      const snapshot=capture?this.snapshot():undefined;const p=this.operations.then(()=>{this.trusted();return action(arg,snapshot);});this.operations=p.catch(()=>{});return p.catch(e=>this.failed(e));
    }));
    command('addSelection',async(_arg,snapshot)=>{this.ready();requireValue(snapshot,'선택한 코드가 없습니다. C/H 코드 범위를 선택하거나 수동 스니펫을 붙여넣으세요.');await this.add(await this.capture(snapshot));},true);
    command('createGoal',async(_arg,snapshot)=>{const service=this.ready(),capture=snapshot?await this.capture(snapshot):manual();const input=await this.goalInput();if(input){await service.createGoal(input,capture);}},true);
    command('addSnippet',async()=>{this.ready();const snippet=await this.prompts.snippet();if(snippet?.trim()){await this.add(manual(snippet));}});
    command('openStep',async arg=>this.display(this.stepId(arg),true,true));
    command('editStep',async arg=>this.display(this.stepId(arg),false));
    command('switchGoal',async arg=>{const service=this.ready();let target=typeof arg==='string'?arg:undefined;if(!target){target=(await vscode.window.showQuickPick(service.document.goals.map(g=>({label:g.title,id:g.id})),{title:'조사 목표 전환'}))?.id;}if(target){await service.switchGoal(target);}});
    command('setStatus',async arg=>{const stepId=this.stepId(arg),choice=await vscode.window.showQuickPick(Object.entries(statusLabels).map(([status,label])=>({label,status:status as Status})),{title:'조사 상태 — 확인은 CT 실측 확인과 다릅니다.'});if(choice){await this.ready().status(stepId,choice.status);await this.display(stepId,false);}});
    command('goParent',async()=>{const service=this.ready(),d=service.document,parent=d.steps.find(s=>s.id===d.currentStepId)?.parentStepId;requireValue(parent,'현재 단계의 상위 조사가 없습니다.');await this.display(parent,true,true);});
    for(const [name,delta] of [['navigateBack',-1],['navigateForward',1]] as const){command(name,async()=>{const stepId=await this.ready().navigate(delta);if(stepId){await this.display(stepId,true,false);}});}
    command('repairAnchor',async(arg,snapshot)=>{const stepId=this.stepId(arg);requireValue(snapshot,'재연결할 파일의 코드 범위를 선택하세요.');const capture=await this.capture(snapshot);if(await vscode.window.showWarningMessage('이 범위로 위치만 재연결할까요? 저장 당시 스니펫과 목표는 유지합니다.',{modal:true},'재연결')==='재연결'){await this.ready().repair(stepId,capture);await this.display(stepId,false);}},true);
    command('retrySave',async()=>{await this.ready().retrySave();const current=this.ready().document.currentStepId;if(current){await this.display(current,false);}});
    command('recoverBackup',async()=>{requireValue(this.store,'저장 폴더가 없습니다.');if(await vscode.window.showWarningMessage('현재 파일은 보존하고 마지막 정상 백업을 복구할까요?',{modal:true},'백업 복구')==='백업 복구'){const d=await this.store.recoverBackup();this.view?.dispose();this.tree?.dispose();this.attach(new InvestigationService(d,this.store));if(d.currentStepId){await this.display(d.currentStepId,false);}}});
    command('recoverLock',async()=>{requireValue(this.store,'저장 폴더가 없습니다.');if(await vscode.window.showWarningMessage('소유 프로세스의 종료를 확인한 잠금만 복구합니다. 진행할까요?',{modal:true},'종료 확인 후 복구')==='종료 확인 후 복구'){await this.store.recoverStaleLock();await this.initialize();}});
  }
  async close():Promise<void>{await this.service?.whenIdle();await this.store?.close();}
}
export async function activate(context:vscode.ExtensionContext):Promise<InvestigationController>{const controller=new InvestigationController(context);active=controller;controller.register();try{await controller.initialize();}catch(e){void controller.failed(e);}return controller;}
export async function deactivate():Promise<void>{await active?.close();active=undefined;}
