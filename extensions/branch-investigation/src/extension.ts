import * as vscode from 'vscode';
import * as path from 'node:path';
import * as fs from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { CapturedCode, clone, CodeAnchor, InvestigationStep, reasonFromCode, statusLabels, Status } from './domain/model';
import { InvestigationService, GoalInput, StepLink } from './domain/investigationService';
import { BULK_LIMIT, bulkKindLabel, splitBulk } from './domain/bulkPaste';
import { requireValue, validId } from './domain/validation';
import { JsonStore } from './storage/jsonStore';
import { sourcePath } from './storage/paths';
import { AnchorCandidate, anchorCandidates, resolveAnchor, AnchorResolution } from './navigation/anchorResolver';
import { InvestigationTree, TreeEntry } from './ui/investigationTree';
import { DetailsPanel } from './ui/detailsPanel';
import { snippetInput } from './ui/snippetInput';
import { stepSearchItems } from './ui/stepSearch';
import { AnalysisError, AnalysisLimits, EngineLocation, PythonTraceAnalysisPort, RelatedResult } from './adapters/traceAnalysisPort';

export interface PromptPort { input(options:vscode.InputBoxOptions):Thenable<string|undefined>; snippet():Promise<string|undefined>; pick?<T extends vscode.QuickPickItem>(items:T[],options:vscode.QuickPickOptions):Thenable<T|undefined>; pickMany?<T extends vscode.QuickPickItem>(items:T[],options:vscode.QuickPickOptions):Thenable<T[]|undefined>; confirm?(message:string):Thenable<boolean>; analysisFailure?(message:string):Thenable<boolean>; }
export interface AnalysisSettings { python:string; paths:string[]; excludePaths?:string[]; limits?:AnalysisLimits; timeoutSeconds?:number }
const defaultPrompts:PromptPort={input:o=>vscode.window.showInputBox(o),snippet:snippetInput};
const manual = (snippet=''):CapturedCode=>({snippet,contextBefore:'',contextAfter:''});
interface SelectionSnapshot { uri:string; version:number; range:vscode.Range; snippet:string; before:string; after:string; }
let active:InvestigationController|undefined;
export class InvestigationController {
  service?:InvestigationService; store?:JsonStore; tree?:InvestigationTree; view?:vscode.TreeView<TreeEntry>;
  readonly status=vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left,20);
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
  async failed(error:unknown):Promise<void>{
    this.updateStatus();
    if(error instanceof AnalysisError && (error.code==='analysis_limit'||error.code==='timeout')){
      const open=this.prompts.analysisFailure?await this.prompts.analysisFailure(error.message):await vscode.window.showErrorMessage(error.message,'분석 설정 열기')==='분석 설정 열기';
      if(open){await vscode.commands.executeCommand('workbench.action.openSettings','@ext:huelune.branch-investigation analysis');}return;
    }
    const action=await vscode.window.showErrorMessage(`분기 조사 작업 실패: ${error instanceof Error?error.message:'알 수 없는 오류'}`,this.service?.dirty?'저장 재시도':'복구 명령 확인');if(action==='저장 재시도'){void vscode.commands.executeCommand('branchInvestigation.retrySave');}
  }
  private snapshot():SelectionSnapshot|undefined{
    const editor=vscode.window.activeTextEditor;if(!editor||editor.selection.isEmpty){return undefined;}
    return this.snapshotOf(editor.document,new vscode.Range(editor.selection.start,editor.selection.end));
  }
  private snapshotOf(d:vscode.TextDocument,r:vscode.Range):SelectionSnapshot{
    const all=d.getText(),start=d.offsetAt(r.start),end=d.offsetAt(r.end);
    return {uri:d.uri.toString(),version:d.version,range:r,snippet:d.getText(r),before:all.slice(Math.max(0,start-200),start),after:all.slice(end,end+200)};
  }
  private async capture(snapshot:SelectionSnapshot):Promise<CapturedCode>{
    requireValue(this.root,'로컬 작업 폴더가 없습니다.');const real=await sourcePath(this.root,snapshot.uri);
    return {snippet:snapshot.snippet,fileUri:pathToFileURL(real).href,relativePath:path.relative(await import('node:fs/promises').then(f=>f.realpath(this.root!)),real).replaceAll('\\','/'),range:{start:{line:snapshot.range.start.line,character:snapshot.range.start.character},end:{line:snapshot.range.end.line,character:snapshot.range.end.character}},documentVersion:snapshot.version,contextBefore:snapshot.before,contextAfter:snapshot.after};
  }
  private async goalInput():Promise<GoalInput|undefined>{const title=await this.prompts.input({title:'새 조사 목표',prompt:'목표 이름 (필수)',validateInput:v=>v.trim()&&v.length<=200?undefined:'목표 이름을 200자 이내로 입력하세요.'});if(!title?.trim()){return;}const description=await this.prompts.input({title:'목표 설명',prompt:'어떤 분기를 왜 통과하려고 하나요? (선택)',validateInput:v=>v.length<=65536?undefined:'설명이 너무 깁니다.'});return description===undefined?undefined:{title,description};}
  private async add(capture:CapturedCode,link?:StepLink):Promise<void>{const service=this.ready(),before=service.document;let goal:GoalInput|undefined;if(!before.currentGoalId){goal=await this.goalInput();if(!goal){return;}}
    // Start from the selected code: the tree labels a step by its reason, so the code itself is what makes the step findable. The user may rewrite it.
    const reason=await this.prompts.input({title:'현재 조사에 추가',prompt:'이 코드를 선택한 이유 (필수) — 선택한 코드를 채웠습니다. Enter로 그대로 저장하거나 고쳐 쓰세요.',value:reasonFromCode(capture.snippet),validateInput:v=>v.trim()&&v.length<=65536?undefined:'이유를 입력하세요.'});if(!reason?.trim()){return;}
    const current=service.document;requireValue(current.currentGoalId===before.currentGoalId&&current.currentStepId===before.currentStepId,'입력 중 현재 조사가 바뀌었습니다. 다시 선택하세요.');
    const stepId=await service.add(capture,reason,goal,link);await this.display(stepId,true,false);if(this.view?.visible){await this.view.reveal({kind:'step',id:stepId},{select:true,expand:true,focus:false});} // leave another sidebar tab (e.g. Search) in place
  }
  /**
   * Relink a step to the editor selection or to a same-file place where the saved snippet text occurs now.
   * Candidates are text matches, so nothing is relinked without the confirmation, even when there is exactly one.
   */
  private async repair(stepId:string,snapshot?:SelectionSnapshot):Promise<void>{
    const service=this.ready(),d=service.document,step=d.steps.find(s=>s.id===stepId);requireValue(step,'조사단계가 없습니다.');const anchor=d.anchors.find(a=>a.id===step.codeAnchorId)!;
    let doc:vscode.TextDocument|undefined,found:ReturnType<typeof anchorCandidates>={candidates:[],truncated:false};
    if(anchor.fileUri){try{await sourcePath(this.root!,anchor.fileUri);doc=await vscode.workspace.openTextDocument(vscode.Uri.parse(anchor.fileUri));found=anchorCandidates(doc.getText(),step.snippet,anchor);}catch{/* Missing or out-of-workspace file: only the manual selection remains. */}}
    const candidates=found.candidates.filter(c=>JSON.stringify(c.range)!==JSON.stringify(anchor.range));
    if(!candidates.length){requireValue(snapshot,doc?'같은 파일에서 저장한 코드와 같은 텍스트를 찾지 못했습니다. 소스에서 범위를 직접 선택한 뒤 다시 실행하세요.':'후보를 찾을 파일이 없습니다. 재연결할 코드 범위를 선택한 뒤 다시 실행하세요.');}
    else{
      const context={both:'앞뒤 문맥 일치',partial:'문맥 일부 일치',none:'문맥 불일치'},at=(p:{line:number;character:number})=>`L${p.line+1}:${p.character+1}`;
      const items:(vscode.QuickPickItem&{range?:AnchorCandidate['range']})[]=candidates.map(c=>({label:`후보 ${at(c.range.start)}`,description:`${context[c.context]}${c.lineDelta===undefined?'':c.lineDelta?` · 저장 위치에서 ${c.lineDelta>0?'+':''}${c.lineDelta}줄`:' · 같은 줄'}`,detail:doc!.lineAt(c.range.start.line).text.trim().slice(0,120),range:c.range}));
      if(snapshot){items.push({label:'현재 선택 범위로 재연결',description:at(snapshot.range.start)});}
      const options={title:`위치 후보 ${candidates.length}개${found.truncated?' (일부만 표시)':''} — 저장한 코드와 텍스트가 같은 곳이며 같은 코드라는 증명이 아닙니다.`,placeHolder:'고른 뒤 한 번 더 확인합니다. 저장 당시 스니펫과 목표는 유지합니다.',matchOnDescription:true,matchOnDetail:true};
      const picked=await (this.prompts.pick?this.prompts.pick(items,options):vscode.window.showQuickPick(items,options));if(!picked){return;}
      if(picked.range){const r=new vscode.Range(picked.range.start.line,picked.range.start.character,picked.range.end.line,picked.range.end.character);
        const editor=await vscode.window.showTextDocument(doc!,{viewColumn:vscode.ViewColumn.One,selection:r,preserveFocus:false});editor.revealRange(r,vscode.TextEditorRevealType.InCenterIfOutsideViewport);snapshot=this.snapshotOf(doc!,r);}
    }
    const capture=await this.capture(snapshot!),message='이 범위로 위치만 재연결할까요? 저장 당시 스니펫과 목표는 유지합니다.';
    if(this.prompts.confirm?await this.prompts.confirm(message):await vscode.window.showWarningMessage(message,{modal:true},'재연결')==='재연결'){await service.repair(stepId,capture);await this.display(stepId,false);}
  }
  /** panel=true only for the explicit 자세히 보기 command; every other path, including a click on a step, leaves a closed detail panel closed. */
  private async display(stepId:string,openSource:boolean,record=false,panel=false):Promise<void>{const service=this.ready(),d=service.document,step=d.steps.find(s=>s.id===stepId);requireValue(step,'조사단계가 없습니다.');const anchor=d.anchors.find(a=>a.id===step.codeAnchorId)!;
    this.details.show(step,anchor,'위치 확인 중…',d.evidence.filter(e=>e.stepId===step.id),service.dirty,panel);
    const resolved=await resolveAnchor(this.root!,anchor,async uri=>(await vscode.workspace.openTextDocument(vscode.Uri.parse(uri))).getText());this.lastResolution=resolved;
    this.details.show(step,anchor,resolved.state==='verified'?'저장 범위의 현재 텍스트 일치 (실행 검증 아님)':resolved.message,d.evidence.filter(e=>e.stepId===step.id),service.dirty,panel);
    if(openSource&&resolved.state==='verified'){
      // Recheck the live buffer immediately before selecting; an unsaved edit must not be ignored.
      const checked=await resolveAnchor(this.root!,anchor,async uri=>(await vscode.workspace.openTextDocument(vscode.Uri.parse(uri))).getText());if(checked.state!=='verified'){this.lastResolution=checked;this.details.show(step,anchor,checked.message,d.evidence.filter(e=>e.stepId===step.id),service.dirty,panel);return;}
      const r=new vscode.Range(checked.range.start.line,checked.range.start.character,checked.range.end.line,checked.range.end.character);
      const editor=await vscode.window.showTextDocument(vscode.Uri.parse(checked.fileUri),{viewColumn:vscode.ViewColumn.One,preserveFocus:false});editor.selection=new vscode.Selection(r.start,r.end);editor.setDecorations(this.decoration,[r]); // a selection passed as an open option re-centres the view even when the range is already visible
      editor.revealRange(r,vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    }
    if(record){await service.select(stepId,openSource&&resolved.state==='verified');}
  }
  /** Machine-scoped: a workspace file cannot choose which executable runs. Empty means the engine link is off. */
  private analysisSettings=():AnalysisSettings=>{const c=vscode.workspace.getConfiguration('branchInvestigation');return {python:(c.get<string>('pythonPath')??'').trim(),paths:c.get<string[]>('analysisPaths')??[],excludePaths:c.get<string[]>('analysisExcludePaths')??[],limits:{maxFiles:c.get<number>('analysisMaxFiles')??500,maxSourceBytes:(c.get<number>('analysisMaxSourceMiB')??32)*1024*1024,maxFileBytes:(c.get<number>('analysisMaxFileMiB')??4)*1024*1024},timeoutSeconds:c.get<number>('analysisTimeoutSeconds')??60};};
  setAnalysisSettingsForTests(read:()=>AnalysisSettings):void{requireValue(this.context.extensionMode===vscode.ExtensionMode.Test,'분석 설정 교체는 Host 테스트에서만 허용합니다.');this.analysisSettings=read;}
  /** Engine candidates are only offered. Nothing is recorded until the user picks one and gives a reason. */
  private async related():Promise<void>{
    this.ready();const editor=vscode.window.activeTextEditor;
    requireValue(editor&&editor.document.uri.scheme==='file','C 파일의 함수 안에 커서를 두고 실행하세요.');
    requireValue(!editor.document.isDirty,'저장하지 않은 변경이 있습니다. 엔진은 디스크의 파일을 읽으므로 저장한 뒤 다시 조회하세요.');
    const {python,paths,root,excludePaths,limits,timeoutSeconds}=await this.engine();
    const file=path.relative(root,await sourcePath(this.root!,editor.document.uri.toString())).replaceAll('\\','/');
    const request={root,file,line:editor.selection.start.line,character:editor.selection.start.character,includePaths:paths,excludePaths,limits};
    const result=await this.analysed('관련 후보 조회 중',['related',python,request],signal=>new PythonTraceAnalysisPort(python,undefined,timeoutSeconds*1000).related(request,signal));
    return this.offerRelated(root,result);
  }
  /** Settings of the engine link, or an error that says which setting to fill in. */
  private async engine():Promise<AnalysisSettings & {root:string;timeoutSeconds:number}>{
    const {python,paths,excludePaths,limits,timeoutSeconds=60}=this.analysisSettings();
    requireValue(Number.isInteger(timeoutSeconds)&&timeoutSeconds>=1&&timeoutSeconds<=300,'분석 제한 시간은 1~300초의 정수로 설정하세요.');
    requireValue(python,'Python 분석 연결이 꺼져 있습니다. 사용자 설정 branchInvestigation.pythonPath에 분석 엔진이 설치된 Python 실행 파일을 지정하세요.');
    requireValue(Array.isArray(paths)&&paths.length>0&&paths.every(p=>typeof p==='string'&&p.trim()),'분석 범위가 없습니다. 설정 branchInvestigation.analysisPaths에 작업 폴더 기준 경로를 지정하세요. 폴더 전체는 "." 입니다.');
    return {python,paths,excludePaths,limits,timeoutSeconds,root:await fs.realpath(this.root!)};
  }
  /**
   * Engine results are kept until a C/H file of the workspace changes on disk, so repeating a lookup or a search does not re-parse the scope.
   * The key carries the interpreter and the whole request. A failed or cancelled run is not kept.
   */
  readonly analysisCache=new Map<string,Promise<unknown>>();engineRuns=0;
  private analysed<T>(title:string,key:unknown,run:(signal:AbortSignal)=>Promise<T>):Promise<T>{
    const k=JSON.stringify(key),hit=this.analysisCache.get(k) as Promise<T>|undefined;if(hit){return hit;}
    const made=Promise.resolve(vscode.window.withProgress({location:vscode.ProgressLocation.Notification,title:`분기 조사: ${title}`,cancellable:true},(_progress,token)=>{
      const abort=new AbortController();token.onCancellationRequested(()=>abort.abort());this.engineRuns++;return run(abort.signal);}));
    this.analysisCache.set(k,made);made.catch(()=>{if(this.analysisCache.get(k)===made){this.analysisCache.delete(k);}});return made;
  }
  /** Open an engine location only when the editor text still equals what the engine read. */
  private async openEngine(root:string,target:EngineLocation):Promise<{doc:vscode.TextDocument;range:vscode.Range}>{
    const {text,startCharacter,endCharacter}=target;
    requireValue(text!==null&&startCharacter!==null&&endCharacter!==null,'위치 확인 필요: 파일 인코딩을 확인할 수 없어 이동하지 않습니다. 소스를 직접 열어 범위를 선택한 뒤 추가하세요.');
    // Error text from the file system may contain a path; report the kind only.
    const real=await sourcePath(this.root!,pathToFileURL(path.join(root,target.path)).href).catch(()=>{throw new Error('위치 확인 필요: 후보 파일을 열 수 없습니다. 분석 범위와 파일을 확인하세요.');});
    const doc=await vscode.workspace.openTextDocument(vscode.Uri.file(real)),range=new vscode.Range(target.startLine,startCharacter,target.endLine,endCharacter),same=(s:string)=>s.replaceAll('\r\n','\n');
    requireValue(doc.validateRange(range).isEqual(range)&&same(doc.getText(range))===same(text),'위치 확인 필요: 편집기 내용이 분석한 내용과 다릅니다. 파일을 저장하거나 인코딩을 확인한 뒤 다시 조회하세요.');
    const shown=await vscode.window.showTextDocument(doc,{viewColumn:vscode.ViewColumn.One,selection:range});shown.setDecorations(this.decoration,[range]);return {doc,range};
  }
  /** Function search: the list comes from the engine once and the quick pick filters it. Picking one only goes there and selects the signature. */
  private async searchFunctions():Promise<void>{
    this.ready();const {python,paths,root,excludePaths,limits,timeoutSeconds}=await this.engine(),request={op:'functions' as const,root,includePaths:paths,excludePaths,limits};
    const result=await this.analysed('함수 목록 읽는 중',['functions',python,request],signal=>new PythonTraceAnalysisPort(python,undefined,timeoutSeconds*1000).functions(request,signal));
    if(!result.functions.length){void vscode.window.showInformationMessage('분석 범위 안에서 함수 정의를 찾지 못했습니다. 범위 밖에 없다는 뜻은 아닙니다.');return;}
    const items=result.functions.map(f=>({label:f.name,description:`${f.signature.path}:${f.signature.startLine+1}`,entry:f}));
    const options={title:`함수 ${items.length}개${result.truncated?' (이름순 앞부분만, 분석 범위를 줄이세요)':''} — 분석 범위 안의 정의만 보여 줍니다. 범위 밖에 없다는 뜻은 아닙니다.`,placeHolder:'함수 이름이나 경로의 일부를 입력하세요.',matchOnDescription:true};
    const picked=await (this.prompts.pick?this.prompts.pick(items,options):vscode.window.showQuickPick(items,options));if(picked){await this.openEngine(root,picked.entry.signature);}
  }
  private async offerRelated(root:string,result:RelatedResult):Promise<void>{
    if(!result.functionName){void vscode.window.showInformationMessage('커서가 분석된 함수 안에 있지 않습니다.');return;}
    // Reason codes for what the engine could not do at the cursor. Unknown codes are not shown as text.
    const reasons:Record<string,string>={cursor_position_not_resolved:'커서 위치를 확정할 수 없어 값·조건 후보는 조회하지 못했습니다(파일 인코딩 확인).',access_path_not_supported:'커서의 배열·복합 경로는 값 추적을 지원하지 않습니다.',value_sources_not_available:'커서의 식은 값 출처를 조회할 수 없습니다.'};
    const limits=result.notes.map(n=>reasons[n]).filter(Boolean).join(' ');
    if(!result.candidates.length){void vscode.window.showInformationMessage(`분석 범위 안에서 후보를 찾지 못했습니다. 범위 밖에 없다는 뜻은 아닙니다. ${limits}`.trim());return;}
    const kinds={value:'값 출처',execution_condition:'실행 조건',call:'호출',rte_data:'RTE 데이터'};
    const items=result.candidates.map(c=>({label:`${kinds[c.relation]}: ${c.requiredTruth===null?'':c.requiredTruth?'참 필요 · ':'거짓 필요 · '}${c.label}`,description:c.target?`${c.functionName??''} · ${c.target.path}:${c.target.startLine+1}`:'분석 범위 안에서 정의를 찾지 못함',detail:c.uncertainty.join(', '),candidate:c}));
    const options={title:`${result.functionName}${result.variable?` · ${result.variable}`:''}의 관련 후보${result.truncated?' (일부만 표시)':''} — 구문·이름 기반 후보이며 실제 연결·실행 순서·조건 충족의 증명이 아닙니다.`,placeHolder:limits||(result.variable?undefined:'변수 위에 커서를 두면 그 값의 출처 후보도 조회합니다.'),matchOnDescription:true,matchOnDetail:true};
    const picked=await (this.prompts.pick?this.prompts.pick(items,options):vscode.window.showQuickPick(items,options));
    if(!picked){return;}
    const target=picked.candidate.target;
    requireValue(target,'분석 범위 안에서 정의를 찾지 못한 후보입니다. 분석 범위를 넓혀 다시 조회하세요.');
    const {doc,range}=await this.openEngine(root,target);
    // A condition is a prerequisite, not a call or data relation: keep it 'manual' and record the needed truth value with the engine's reasons.
    const {relation,requiredTruth,uncertainty}=picked.candidate;
    await this.add(await this.capture(this.snapshotOf(doc,range)),relation==='execution_condition'?{type:'manual',uncertainty:[...uncertainty,`execution_requirement_${requiredTruth}`]}:{type:relation==='call'?'call':'data_dependency',uncertainty});
  }
  private stepId(arg:unknown):string{const candidate=typeof arg==='string'?arg:arg&&typeof arg==='object'?(arg as {id?:unknown}).id:undefined;const value=candidate??this.ready().document.currentStepId;requireValue(validId(value),'조사단계를 선택하세요.');return value;}
  register():void{
    const command=(name:string,action:(arg:unknown,snapshot?:SelectionSnapshot)=>Promise<unknown>,capture=false)=>this.context.subscriptions.push(vscode.commands.registerCommand('branchInvestigation.'+name,(arg:unknown)=>{
      const snapshot=capture?this.snapshot():undefined;const p=this.operations.then(()=>{this.trusted();return action(arg,snapshot);});this.operations=p.catch(()=>{});return p.catch(e=>this.failed(e));
    }));
    command('addSelection',async(_arg,snapshot)=>{this.ready();requireValue(snapshot,'선택한 코드가 없습니다. C/H 코드 범위를 선택하거나 수동 스니펫을 붙여넣으세요.');await this.add(await this.capture(snapshot));},true);
    command('createGoal',async(_arg,snapshot)=>{const service=this.ready(),capture=snapshot?await this.capture(snapshot):manual();const input=await this.goalInput();if(input){await service.createGoal(input,capture);}},true);
    // Bulk paste: split and label by text shape, show every piece ticked, and create steps only for what the user leaves ticked.
    command('addBulk',async()=>{const service=this.ready(),before=service.document,text=await this.prompts.snippet();if(!text?.trim()){return;}
      const {items,truncated}=splitBulk(text);if(!items.length){return;}
      const rows=items.map(i=>({label:`${bulkKindLabel[i.kind]}: ${reasonFromCode(i.text)}`,description:i.text.includes('\n')?`${i.text.split('\n').length}줄`:undefined,picked:true,item:i}));
      const options={title:`${rows.length}개로 나눔${truncated?` (앞 ${BULK_LIMIT}개만)`:''} — 단계로 만들 항목만 남기고 확인`,placeHolder:'분류는 글자 모양으로만 붙인 이름표입니다. 파일·함수와 연결하지 않습니다.',matchOnDescription:true};
      const picked=await (this.prompts.pickMany?this.prompts.pickMany(rows,options):vscode.window.showQuickPick(rows,{...options,canPickMany:true}));if(!picked?.length){return;}
      let goal:GoalInput|undefined;if(!before.currentGoalId){goal=await this.goalInput();if(!goal){return;}}
      const current=service.document;requireValue(current.currentGoalId===before.currentGoalId&&current.currentStepId===before.currentStepId,'입력 중 현재 조사가 바뀌었습니다. 다시 붙여넣으세요.');
      await service.addMany(picked.map(r=>({capture:manual(r.item.text),reason:r.label})),goal);vscode.window.setStatusBarMessage(`분기 조사: ${picked.length}개 단계를 추가했습니다.`,4000);});
    command('addSnippet',async()=>{this.ready();const snippet=await this.prompts.snippet();if(snippet?.trim()){await this.add(manual(snippet));}});
    command('traceRelated',async()=>this.related());command('searchFunctions',async()=>this.searchFunctions());
    const sources=vscode.workspace.createFileSystemWatcher('**/*.{c,h,C,H}'),stale=()=>this.analysisCache.clear();sources.onDidChange(stale);sources.onDidCreate(stale);sources.onDidDelete(stale);this.context.subscriptions.push(sources);
    // Finding a step is navigation only: it visits the picked step like a click in the tree and records nothing else.
    command('searchSteps',async()=>{const items=stepSearchItems(this.ready().document);requireValue(items.length,'검색할 조사 단계가 없습니다.');
      const options={title:'조사 단계 검색 — 이유·목표·상태·위치·조건·코드',placeHolder:'입력한 글자가 든 단계만 남습니다. 상태 이름(조사 중·확인·보류·제외)으로도 거를 수 있습니다.',matchOnDescription:true,matchOnDetail:true};
      const picked=await (this.prompts.pick?this.prompts.pick(items,options):vscode.window.showQuickPick(items,options));
      if(picked){await this.display(picked.stepId,true,true);await this.view?.reveal({kind:'step',id:picked.stepId},{select:true,expand:true,focus:false});}});
    command('openStep',async arg=>this.display(this.stepId(arg),true,true));
    command('editStep',async arg=>this.display(this.stepId(arg),false,false,true));
    command('switchGoal',async arg=>{const service=this.ready();let target=typeof arg==='string'?arg:undefined;if(!target){target=(await vscode.window.showQuickPick(service.document.goals.map(g=>({label:g.title,id:g.id})),{title:'조사 목표 전환'}))?.id;}if(target){await service.switchGoal(target);}});
    command('setStatus',async arg=>{const stepId=this.stepId(arg),choice=await vscode.window.showQuickPick(Object.entries(statusLabels).map(([status,label])=>({label,status:status as Status})),{title:'조사 상태 — 확인은 CT 실측 확인과 다릅니다.'});if(choice){await this.ready().status(stepId,choice.status);await this.display(stepId,false);}});
    command('goParent',async()=>{const service=this.ready(),d=service.document,parent=d.steps.find(s=>s.id===d.currentStepId)?.parentStepId;requireValue(parent,'현재 단계의 상위 조사가 없습니다.');await this.display(parent,true,true);});
    for(const [name,delta] of [['navigateBack',-1],['navigateForward',1]] as const){command(name,async()=>{const stepId=await this.ready().navigate(delta);if(stepId){await this.display(stepId,true,false);}});}
    command('repairAnchor',async(arg,snapshot)=>this.repair(this.stepId(arg),snapshot),true);
    // Deleting is the only command that discards records, so it always asks first and says how far it reaches.
    const confirm=async(message:string)=>this.prompts.confirm?this.prompts.confirm(message):await vscode.window.showWarningMessage(message,{modal:true,detail:'근거와 방문 이력도 함께 지웁니다. 지운 직후에는 "마지막 정상 백업 복구"로 되돌릴 수 있습니다.'},'지우기')==='지우기';
    const afterDelete=async()=>{const current=this.ready().document.currentStepId;if(current){await this.display(current,false);}else{this.details.dispose();}};
    command('deleteStep',async arg=>{const stepId=this.stepId(arg),d=this.ready().document,step=d.steps.find(s=>s.id===stepId);requireValue(step,'조사단계가 없습니다.');
      let below=0,layer=[stepId];while(layer.length){layer=d.steps.filter(s=>s.parentStepId&&layer.includes(s.parentStepId)).map(s=>s.id);below+=layer.length;}
      if(await confirm(`${step.sequence}번 단계${below?`와 하위 단계 ${below}개`:''}를 지울까요?`)){await this.ready().removeStep(stepId);await afterDelete();}});
    command('deleteGoal',async arg=>{const d=this.ready().document,goalId=(arg&&typeof arg==='object'?(arg as {id?:unknown}).id:arg)??d.currentGoalId,goal=d.goals.find(g=>g.id===goalId);requireValue(goal,'지울 목표를 트리에서 선택하세요.');
      if(await confirm(`목표 "${goal.title}"과 단계 ${d.steps.filter(s=>s.goalId===goal.id).length}개를 지울까요?`)){await this.ready().removeGoal(goal.id);await afterDelete();}});
    command('retrySave',async()=>{await this.ready().retrySave();const current=this.ready().document.currentStepId;if(current){await this.display(current,false);}});
    command('recoverBackup',async()=>{requireValue(this.store,'저장 폴더가 없습니다.');if(await vscode.window.showWarningMessage('현재 파일은 보존하고 마지막 정상 백업을 복구할까요?',{modal:true},'백업 복구')==='백업 복구'){const d=await this.store.recoverBackup();this.view?.dispose();this.tree?.dispose();this.attach(new InvestigationService(d,this.store));if(d.currentStepId){await this.display(d.currentStepId,false);}}});
    command('recoverLock',async()=>{requireValue(this.store,'저장 폴더가 없습니다.');if(await vscode.window.showWarningMessage('소유 프로세스의 종료를 확인한 잠금만 복구합니다. 진행할까요?',{modal:true},'종료 확인 후 복구')==='종료 확인 후 복구'){await this.store.recoverStaleLock();await this.initialize();}});
  }
  async close():Promise<void>{await this.service?.whenIdle();await this.store?.close();}
}
export async function activate(context:vscode.ExtensionContext):Promise<InvestigationController>{const controller=new InvestigationController(context);active=controller;controller.register();try{await controller.initialize();}catch(e){void controller.failed(e);}return controller;}
export async function deactivate():Promise<void>{await active?.close();active=undefined;}
