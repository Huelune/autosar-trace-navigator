import * as vscode from 'vscode';
import { CodeAnchor, Evidence, InvestigationStep, statusLabels } from '../domain/model';
import { StepEdit } from '../domain/investigationService';
import { nonempty, requireValue, text, utc, validId, validStatus } from '../domain/validation';
import { escapeHtml as h, nonce, shell } from './html';
export type DetailAction = {type:'save';stepId:string;edit:StepEdit} | {type:'evidence';stepId:string;evidence:Omit<Evidence,'id'|'stepId'>};
const fields = {reason:'선택 이유 (필수)',hypothesis:'가정',requiredConditions:'필요 조건',derivedConditions:'도출 조건',observation:'관찰',result:'결과',nextAction:'다음 할 일'} as const;
/** Allowlist messages; reject stale panels/unknown properties and never execute user HTML. */
export function decodeDetailMessage(value: unknown, expectedStep: string): DetailAction {
  requireValue(value && typeof value==='object' && !Array.isArray(value), '잘못된 화면 요청입니다.'); const m=value as Record<string,unknown>;
  requireValue(validId(m.stepId) && m.stepId===expectedStep, '화면이 다른 단계로 바뀌었습니다. 다시 확인하세요.');
  if(m.type==='save') {
    requireValue(Object.keys(m).sort().join(',')==='edit,stepId,type' && m.edit && typeof m.edit==='object', '잘못된 편집 요청입니다.'); const e=m.edit as Record<string,unknown>;
    requireValue(Object.keys(e).sort().join(',')===[...Object.keys(fields),'status'].sort().join(','), '허용하지 않은 편집 항목입니다.');
    for(const k of Object.keys(fields)) { text(e[k]); } nonempty(e.reason); requireValue(validStatus(e.status),'상태 오류입니다.');
    return {type:'save',stepId:m.stepId,edit:e as unknown as StepEdit};
  }
  requireValue(m.type==='evidence' && Object.keys(m).sort().join(',')==='evidence,stepId,type' && m.evidence && typeof m.evidence==='object', '허용하지 않은 화면 요청입니다.');
  const e=m.evidence as Record<string,unknown>; requireValue(['source_fact','hypothesis','ct_observed'].includes(e.kind as string),'근거 종류 오류입니다.'); nonempty(e.text);
  const keys=e.kind==='ct_observed'?['kind','text','executionLabel','observedAt','memo']:['kind','text']; requireValue(Object.keys(e).sort().join(',')===keys.sort().join(','),'허용하지 않은 근거 항목입니다.');
  if(e.kind==='ct_observed'){nonempty(e.executionLabel,200);nonempty(e.memo);requireValue(utc(e.observedAt),'UTC 관찰 시각을 입력하세요.');}
  return {type:'evidence',stepId:m.stepId,evidence:e as unknown as Omit<Evidence,'id'|'stepId'>};
}
export class DetailsPanel implements vscode.Disposable {
  private panel?:vscode.WebviewPanel; private stepId?:string;
  constructor(private readonly action:(value:DetailAction)=>Promise<void>,private readonly failed:(error:unknown)=>void){}
  show(step:InvestigationStep, anchor:CodeAnchor, locationState:string, evidence:Evidence[], dirty:boolean):void {
    if(!this.panel){this.panel=vscode.window.createWebviewPanel('branchInvestigation.details','조사 이유와 상세',vscode.ViewColumn.Beside,{enableScripts:true,localResourceRoots:[],retainContextWhenHidden:true});this.panel.onDidDispose(()=>{this.panel=undefined;this.stepId=undefined;});this.panel.webview.onDidReceiveMessage((m:unknown)=>{try{requireValue(this.stepId,'선택된 단계가 없습니다.');const action=decodeDetailMessage(m,this.stepId);void this.action(action).catch(this.failed);}catch(e){this.failed(e);}});}
    this.stepId=step.id; const token=nonce(), goal=step.goalSnapshot;
    const targetKind=({manual:'수동 분기 앵커',if:'if',else_if:'else if',else:'else'})[goal.target.kind]; const targetSummary=targetKind+(goal.target.condition?' · 조건: '+goal.target.condition:' · 조건식 미기록')+(goal.target.requiredTruth===undefined?'':' · '+(goal.target.requiredTruth?'참':'거짓')+' 필요'); const rangeLabel=(a:CodeAnchor)=>a.range?('L'+(a.range.start.line+1)+':'+(a.range.start.character+1)+' → L'+(a.range.end.line+1)+':'+(a.range.end.character+1)+' (끝 미포함)'):''; const body=`<h1>선택 이유</h1><div class="reason">${h(step.reason)}</div><p class="notice">${h(locationState)}${dirty?' · 저장되지 않은 변경 있음':''}</p><small>확인 상태는 CT 실측 확인을 뜻하지 않습니다. 조사 트리는 실행 순서가 아닙니다.</small><h2>당시 목표: ${h(goal.title)}</h2><p>${h(goal.description)}</p><pre>${h(targetSummary)}</pre><p>당시 목표 위치: ${h(goal.anchor.relativePath??'연결된 파일 없음')} ${h(rangeLabel(goal.anchor))}</p><form id="edit">${Object.entries(fields).map(([key,label])=>`<label>${label}<textarea name="${key}" maxlength="65536">${h(step[key as keyof typeof fields])}</textarea></label>`).join('')}<label>조사 상태<select name="status">${Object.entries(statusLabels).map(([v,l])=>`<option value="${v}"${v===step.status?' selected':''}>${l}</option>`).join('')}</select></label><button>조사 정보 저장</button></form><h2>저장 당시 스니펫</h2><pre>${h(step.snippet)}</pre><p>${h(anchor.relativePath??'연결된 파일 없음')} ${h(rangeLabel(anchor))}</p><h2>근거 (원본 사실·가설·CT 실측 구분)</h2>${evidence.map(e=>`<pre>${h(({source_fact:'소스 근거 (사용자 기록)',hypothesis:'가설',ct_observed:'CT 실측'})[e.kind])}\n${h(e.text)}${e.kind==='ct_observed'?'\n'+h(`${e.executionLabel} · ${e.observedAt}\n${e.memo}`):''}</pre>`).join('')}<form id="evidence"><label>종류<select name="kind"><option value="source_fact">소스 근거 (사용자 기록)</option><option value="hypothesis">가설</option><option value="ct_observed">CT에서 사람이 확인한 실측</option></select></label><label>근거 내용<textarea name="text" maxlength="65536" required></textarea></label><label>CT 실행 라벨 (실측 시 필수)<input name="executionLabel" maxlength="200"></label><label>관찰 시각 UTC ISO (실측 시 필수)<input name="observedAt" placeholder="2026-11-10T01:00:00.000Z"></label><label>CT 메모 (실측 시 필수)<textarea name="memo" maxlength="65536"></textarea></label><button>근거 추가</button></form><p id="feedback" aria-live="polite"></p>`;
    const script=`const vscode=acquireVsCodeApi();const stepId=${JSON.stringify(step.id)};document.getElementById('edit').addEventListener('submit',e=>{e.preventDefault();const edit=Object.fromEntries(new FormData(e.target));vscode.postMessage({type:'save',stepId,edit});document.getElementById('feedback').textContent='저장 요청 중…';});document.getElementById('evidence').addEventListener('submit',e=>{e.preventDefault();const all=Object.fromEntries(new FormData(e.target));const evidence={kind:all.kind,text:all.text};if(all.kind==='ct_observed'){Object.assign(evidence,{executionLabel:all.executionLabel,observedAt:all.observedAt,memo:all.memo});}vscode.postMessage({type:'evidence',stepId,evidence});});`;
    this.panel.webview.html=shell('조사 상세',body,script,token);this.panel.reveal(vscode.ViewColumn.Two,true);
  }
  dispose():void{this.panel?.dispose();}
}
