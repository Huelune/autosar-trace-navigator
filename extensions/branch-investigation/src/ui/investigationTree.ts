import * as vscode from 'vscode';
import { InvestigationService } from '../domain/investigationService';
import { statusLabels } from '../domain/model';
import { forks, shownChildren, shownParent, startsBranch } from './treeLayout';
export interface TreeEntry { kind: 'goal'|'step'; id: string }
export class InvestigationTree implements vscode.TreeDataProvider<TreeEntry>, vscode.Disposable {
  private document;
  private event = new vscode.EventEmitter<TreeEntry | undefined>(); readonly onDidChangeTreeData = this.event.event;
  constructor(private readonly service: InvestigationService) {this.document=service.document;}
  refresh(): void { this.document=this.service.document;this.event.fire(undefined); }
  getChildren(parent?: TreeEntry): TreeEntry[] { const d = this.document; if (!parent) { return d.goals.map(g => ({kind:'goal', id:g.id})); }
    return shownChildren(d.steps, parent).map(s => ({kind:'step', id:s.id})); }
  getParent(entry: TreeEntry): TreeEntry | undefined { if (entry.kind === 'goal') { return undefined; } const s = this.document.steps.find(s => s.id === entry.id)!; return shownParent(this.document.steps, s); }
  getTreeItem(entry: TreeEntry): vscode.TreeItem {
    const d = this.document;
    if (entry.kind === 'goal') { const g = d.goals.find(g=>g.id===entry.id)!; const item = new vscode.TreeItem(g.title, vscode.TreeItemCollapsibleState.Expanded); item.id=g.id; item.contextValue='goal'; item.description=d.currentGoalId===g.id?'현재 목표':''; item.command={command:'branchInvestigation.switchGoal',title:'목표 전환',arguments:[g.id]}; return item; }
    const s = d.steps.find(s=>s.id===entry.id)!, children = forks(d.steps,s.id), branch = startsBranch(d.steps,s);
    const item = new vscode.TreeItem(`${branch?'↳ ':''}${s.sequence}. ${s.reason.slice(0,70)}`, children?vscode.TreeItemCollapsibleState.Expanded:vscode.TreeItemCollapsibleState.None);
    item.id=s.id; item.contextValue='step'; item.description=`${d.currentStepId===s.id?'▶ ':''}${statusLabels[s.status]}`;
    const above=d.steps.find(x=>x.id===s.parentStepId);
    item.tooltip=`${s.reason}\n${statusLabels[s.status]} · ${above?`${above.sequence}번 단계에서 이어짐${branch?' (갈래 시작)':''}`:'목표의 첫 단계'} · 조사 순번이며 실제 실행 순서가 아닙니다.`;
    item.iconPath=new vscode.ThemeIcon(s.status==='deferred'?'clock':s.status==='excluded'?'circle-slash':s.status==='confirmed'?'check':'search');
    item.command={command:'branchInvestigation.openStep',title:'코드로 이동',arguments:[s.id]}; return item;
  }
  dispose(): void { this.event.dispose(); }
}
