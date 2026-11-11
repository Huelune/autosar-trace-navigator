import * as vscode from 'vscode';
import { CodeAnchor, Evidence, InvestigationStep } from '../domain/model';
import { StepEdit } from '../domain/investigationService';
import { nonempty, requireValue, text, utc, validId, validStatus } from '../domain/validation';
import { detailBody, detailScript, fields, nonce, shell } from './html';
export type DetailAction = {type:'save';stepId:string;edit:StepEdit} | {type:'evidence';stepId:string;evidence:Omit<Evidence,'id'|'stepId'>};
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
    if(!this.panel){this.panel=vscode.window.createWebviewPanel('branchInvestigation.details','조사 코드와 상세',vscode.ViewColumn.Beside,{enableScripts:true,localResourceRoots:[],retainContextWhenHidden:true});this.panel.onDidDispose(()=>{this.panel=undefined;this.stepId=undefined;});this.panel.webview.onDidReceiveMessage((m:unknown)=>{try{requireValue(this.stepId,'선택된 단계가 없습니다.');const action=decodeDetailMessage(m,this.stepId);void this.action(action).catch(this.failed);}catch(e){this.failed(e);}});}
    this.stepId=step.id; const token=nonce();
    this.panel.webview.html=shell('조사 상세',detailBody(step,anchor,locationState,evidence,dirty),detailScript(step.id),token);this.panel.reveal(vscode.ViewColumn.Two,true);
  }
  dispose():void{this.panel?.dispose();}
}
