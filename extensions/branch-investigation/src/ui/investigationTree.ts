import { branchSize, onBranch, startsBranch } from './treeLayout';
import * as vscode from 'vscode';
import { InvestigationService } from '../domain/investigationService';
import { statusLabels } from '../domain/model';
import { codeLabel, shortText, sourceLabel, TraceEntry, TracePresentation, TraceViewMode } from './tracePresentation';
export type TreeEntry = TraceEntry;
export class InvestigationTree implements vscode.TreeDataProvider<TreeEntry>, vscode.Disposable {
  private presentation: TracePresentation;
  private event = new vscode.EventEmitter<TreeEntry | undefined>(); readonly onDidChangeTreeData = this.event.event;
  constructor(private readonly service: InvestigationService, private mode: TraceViewMode = 'path') { this.presentation = new TracePresentation(service.document, mode); }
  get viewMode(): TraceViewMode { return this.mode; }
  get message(): string { return this.presentation.message; }
  setMode(mode: TraceViewMode): void { this.mode = mode; this.refresh(); }
  refresh(): void { this.presentation = new TracePresentation(this.service.document, this.mode); this.event.fire(undefined); }
  getChildren(parent?: TreeEntry): TreeEntry[] { return this.presentation.getChildren(parent); }
  getParent(entry: TreeEntry): TreeEntry | undefined { return this.presentation.getParent(entry); }
  getTreeItem(entry: TreeEntry): vscode.TreeItem {
    const d = this.presentation.document;
    if (entry.kind === 'goal') {
      const g = d.goals.find(goal => goal.id === entry.id)!, count = d.steps.filter(step => step.goalId === g.id).length;
      const item = new vscode.TreeItem(shortText(g.title, 55), g.id === d.currentGoalId ? vscode.TreeItemCollapsibleState.Expanded : vscode.TreeItemCollapsibleState.Collapsed);
      item.id = g.id; item.contextValue = 'goal'; item.description = `${count}단계${d.currentGoalId === g.id ? ' · 현재 목표' : ''}`;
      item.tooltip = g.title + '\n' + g.description; item.command = { command: 'branchInvestigation.switchGoal', title: '목표 전환', arguments: [g.id] }; return item;
    }
    if (entry.kind === 'group') {
      const steps = entry.stepIds.map(id => d.steps.find(step => step.id === id)!);
      const item = new vscode.TreeItem(`조사 #${steps[0].sequence}–#${steps.at(-1)!.sequence}`, vscode.TreeItemCollapsibleState.Collapsed);
      item.id = entry.id; item.contextValue = 'historyGroup'; item.description = `${steps.length}개 · 펼쳐 보기`;
      item.tooltip = steps.map(step => `#${step.sequence} ${codeLabel(step)}`).join('\n'); item.iconPath = new vscode.ThemeIcon('history'); return item;
    }
    const step = d.steps.find(step => step.id === entry.id)!, anchor = d.anchors.find(a => a.id === step.codeAnchorId);
    const current = step.id === d.currentStepId, parent = d.steps.find(s => s.id === step.parentStepId);
    const children = d.steps.filter(s => s.parentStepId === step.id), after = d.currentStepId !== undefined && d.currentStepId === step.parentStepId;
    const branch=this.mode==='branches'&&startsBranch(d.steps,step);
    const item = new vscode.TreeItem(`${branch||after ? '↳ ' : ''}${step.sequence}. ${codeLabel(step)}`, this.getChildren(entry).length?vscode.TreeItemCollapsibleState.Expanded:vscode.TreeItemCollapsibleState.None);
    item.id = step.id; item.contextValue = 'step';
    item.description = `${sourceLabel(anchor)} · ${after ? '이어갈 경로' : statusLabels[step.status]}${children.length > 1 ? ' · 갈림길 ' + children.length : ''}`;
    if(this.mode==='branches'){item.description=`${current?'▶ ':''}${statusLabels[step.status]}${branch?` · 갈래 ${branchSize(d.steps,step.id)}단계${!current&&onBranch(d.steps,step.id,d.currentStepId)?' · ▶ 진행 중':''}`:''}`;}
    item.tooltip = `목표: ${step.goalSnapshot.title}\n이유: ${shortText(step.reason, 350)}\n코드: ${shortText(step.snippet, 350)}\n${anchor?.relativePath ?? '연결된 파일 없음'}\n${parent ? '#' + parent.sequence + '에서 이어짐' : '목표의 첫 단계'} · ${statusLabels[step.status]}\n조사 경로이며 실제 실행 순서가 아닙니다.`;
    item.iconPath = new vscode.ThemeIcon(current ? 'debug-stackframe' : step.status === 'deferred' ? 'clock' : step.status === 'excluded' ? 'circle-slash' : step.status === 'confirmed' ? 'check' : 'circle-outline');
    item.command = { command: 'branchInvestigation.openStep', title: '코드로 이동', arguments: [step.id] }; return item;
  }
  dispose(): void { this.event.dispose(); }
}
