import * as vscode from 'vscode';
import { ValueGraphResult } from '../adapters/traceAnalysisPort';
import { requireValue } from '../domain/validation';
import { nonce } from './html';
import { graphPage } from './valueGraphView';
import { decodeGraphAction, GraphAction } from './valueGraphMessage';

/** Preview-only panel; the controller owns source validation and explicit history changes. */
export class ValueGraphPanel implements vscode.Disposable{
  private panel?:vscode.WebviewPanel;
  private current?:{graph:ValueGraphResult;goal:string;token:string;invalid?:string};
  constructor(private readonly action:(action:GraphAction,result:ValueGraphResult)=>Promise<void>,private readonly failed:(error:unknown)=>void){}
  get result():ValueGraphResult|undefined{return this.current?.graph;}
  get valid():boolean{return !!this.current&&!this.current.invalid;}
  get isOpen():boolean{return this.panel!==undefined;}
  show(graph:ValueGraphResult,goal:string):void{
    if(!this.panel){
      this.panel=vscode.window.createWebviewPanel('branchInvestigation.origins','변수 전체 출처',vscode.ViewColumn.Beside,{enableScripts:true,localResourceRoots:[],retainContextWhenHidden:true});
      this.panel.onDidDispose(()=>{this.panel=undefined;this.current=undefined;});
      this.panel.webview.onDidReceiveMessage((value:unknown)=>{try{requireValue(this.current&&!this.current.invalid,'소스 또는 현재 조사가 바뀌었습니다. 변수에서 다시 조회하세요.');const m=decodeGraphAction(value,this.current.token,this.current.graph);void this.action(m,this.current.graph).catch(this.failed);}catch(e){this.failed(e);}});
    }
    this.current={graph,goal,token:nonce()};this.redraw();this.panel.reveal(vscode.ViewColumn.Beside,true);
  }
  invalidate(message='소스가 변경되어 이 미리보기가 오래됐습니다.'):void{if(this.current){this.current.invalid=message;this.current.token=nonce();this.redraw();}}
  private redraw():void{if(this.panel&&this.current){const c=this.current;this.panel.webview.html=graphPage(c.graph,c.goal,c.token,c.invalid);}}
  dispose():void{this.panel?.dispose();this.panel=undefined;this.current=undefined;}
}
