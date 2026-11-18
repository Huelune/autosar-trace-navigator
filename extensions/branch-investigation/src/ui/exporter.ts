import { InvestigationStep, RelationEdge, statusLabels, WorkspaceDocument } from '../domain/model';
import { escapeHtml, fields } from './html';

/** Text exports of one goal. Pure: the caller chooses the file. Everything written here is what the user recorded, never engine output. */
export const exportFormats = {
  handover: { label: '전달용 문서 (Markdown, 코드 포함)', detail: '경로 요약과 단계별 이유·조건·근거·코드. 저장한 코드와 파일 경로가 들어갑니다.', extension: 'md' },
  handoverNoCode: { label: '전달용 문서 (Markdown, 코드 제외)', detail: '위와 같되 저장한 코드 본문을 뺍니다. 이유와 파일 경로는 들어갑니다.', extension: 'md' },
  diagram: { label: '시각화용 그림 (HTML)', detail: '브라우저로 여는 조사 트리 그림. 인터넷 없이 열리고 인쇄할 수 있습니다. 단계를 누르면 메모와 코드가 펼쳐집니다.', extension: 'html' },
  mermaid: { label: '시각화용 그래프 (Mermaid)', detail: 'Mermaid를 지원하는 문서 도구에 붙여넣는 흐름도 글. 코드 본문은 들어가지 않습니다.', extension: 'md' },
} as const;
export type ExportFormat = keyof typeof exportFormats;

const NOTICE = '조사 순번은 실제 실행 순서가 아닙니다. 후보와 경로는 사람이 기록한 조사 내용이며 실제 연결·조건 충족의 증명이 아닙니다.';
const relationLabels: Record<RelationEdge['type'], string> = { call: '호출', read: '읽기', write: '쓰기', data_dependency: '데이터 의존', manual: '' };
const evidenceLabels = { source_fact: '소스 근거 (사용자 기록)', hypothesis: '가설', ct_observed: 'CT 실측' } as const;
const noteKeys = ['hypothesis', 'requiredConditions', 'derivedConditions', 'observation', 'result', 'nextAction'] as const;
const oneLine = (s: string, max = 80): string => { const t = s.replace(/\s+/g, ' ').trim(); return t.length > max ? t.slice(0, max) + '…' : t; };

interface View { title: string; description: string; steps: InvestigationStep[]; children(id?: string): InvestigationStep[]; place(s: InvestigationStep): string; relation(s: InvestigationStep): string; current?: string; counts: string }
function view(d: WorkspaceDocument, goalId: string): View {
  const goal = d.goals.find(g => g.id === goalId); if (!goal) { throw new Error('내보낼 목표가 없습니다.'); }
  const steps = d.steps.filter(s => s.goalId === goalId).sort((a, b) => a.sequence - b.sequence);
  const counts = (Object.keys(statusLabels) as (keyof typeof statusLabels)[]).map(k => `${statusLabels[k]} ${steps.filter(s => s.status === k).length}`).join(', ');
  return { title: goal.title, description: goal.description, steps, current: d.currentStepId, counts,
    children: id => steps.filter(s => s.parentStepId === id),
    place: s => { const a = d.anchors.find(x => x.id === s.codeAnchorId); return a?.relativePath ? `${a.relativePath}${a.range ? `:${a.range.start.line + 1}` : ''}` : '파일 미연결'; },
    relation: s => relationLabels[d.relations.find(r => r.toStepId === s.id)?.type ?? 'manual'] };
}
/** A fence longer than any backtick run inside, so recorded code cannot close it early. */
const fence = (code: string): string => { const ticks = '`'.repeat(Math.max(3, ...(code.match(/`+/g) ?? []).map(t => t.length + 1))); return `${ticks}c\n${code}\n${ticks}`; };
/** Recorded text is shown as written, not as Markdown structure. */
const quote = (text: string): string => text.split(/\r?\n/).map(l => `  > ${l}`).join('\n');

export function exportMarkdown(d: WorkspaceDocument, goalId: string, withCode: boolean, at: string): string {
  const v = view(d, goalId), out: string[] = [`# 조사 기록: ${oneLine(v.title, 200)}`, '', `- 내보낸 시각: ${at}`, `- 단계 ${v.steps.length}개 (${v.counts})`, `- ${NOTICE}`];
  if (v.description.trim()) { out.push('', '## 목표 설명', '', quote(v.description)); }
  out.push('', '## 경로 요약', '');
  // Like the tree view: one path stays on one level, a fork lists the first step of each alternative one level deeper, and the rest of an alternative sits under its first step.
  const line = (s: InvestigationStep, depth: number): void => { out.push(`${'  '.repeat(depth)}- ${s.sequence}. ${oneLine(s.reason)} — ${statusLabels[s.status]}${s.id === v.current ? ' ◀ 현재' : ''}`); };
  const outline = (start: InvestigationStep, depth: number, head: boolean): void => {
    line(start, depth); const rest = head ? depth + 1 : depth; let last = start, next = v.children(last.id);
    for (; next.length === 1; next = v.children(last.id)) { last = next[0]; line(last, rest); }
    for (const c of next) { outline(c, rest + 1, true); }
  };
  const roots = v.children(undefined); for (const r of roots) { outline(r, 0, roots.length > 1); }
  if (!v.steps.length) { out.push('(단계 없음)'); }
  out.push('', '## 단계 상세');
  for (const s of v.steps) {
    const parent = v.steps.find(x => x.id === s.parentStepId), relation = v.relation(s);
    out.push('', `### ${s.sequence}. ${oneLine(s.reason)}`, '', `- 상태: ${statusLabels[s.status]}`, `- 위치: ${v.place(s)}`,
      `- 이어진 곳: ${parent ? `${parent.sequence}번 단계${relation ? ` (${relation})` : ''}` : '목표의 첫 단계'}`, '- 이유:', quote(s.reason));
    for (const k of noteKeys) { if (s[k].trim()) { out.push(`- ${fields[k]}:`, quote(s[k])); } }
    for (const e of d.evidence.filter(x => x.stepId === s.id)) {
      out.push(`- 근거 — ${evidenceLabels[e.kind]}${e.kind === 'ct_observed' ? ` · ${e.executionLabel ?? ''} · ${e.observedAt ?? ''}` : ''}:`, quote(e.text + (e.memo ? `\n${e.memo}` : '')));
    }
    if (withCode) { out.push('', fence(s.snippet)); }
  }
  return out.join('\n') + '\n';
}

export function exportMermaid(d: WorkspaceDocument, goalId: string, at: string): string {
  const v = view(d, goalId), text = (s: string) => oneLine(s, 60).replace(/["`\\]/g, "'").replace(/[<>&#;]/g, ' ');
  const n = (s: InvestigationStep) => `s${s.sequence}`, out = ['flowchart TD', `  goal(["목표: ${text(v.title)}"])`];
  for (const s of v.steps) {
    const parent = v.steps.find(x => x.id === s.parentStepId), relation = v.relation(s);
    out.push(`  ${n(s)}["${s.sequence}. ${text(s.reason)}<br/>${statusLabels[s.status]} · ${text(v.place(s))}"]:::${s.status}`, `  ${parent ? n(parent) : 'goal'} -->${relation ? `|${relation}|` : ''} ${n(s)}`);
  }
  out.push('  classDef investigating stroke:#0969da,stroke-width:2px', '  classDef confirmed stroke:#1a7f37,stroke-width:2px', '  classDef deferred stroke:#9a6700,stroke-width:2px,stroke-dasharray:6 3', '  classDef excluded stroke:#8c959f,stroke-dasharray:2 3,color:#8c959f');
  return [`# 조사 그래프: ${oneLine(v.title, 200)}`, '', `- 내보낸 시각: ${at}`, `- 단계 ${v.steps.length}개 (${v.counts})`, `- 실선 파랑: 조사 중, 초록: 확인, 긴 점선: 보류, 짧은 점선: 제외`, `- ${NOTICE}`, '', '```mermaid', ...out, '```', ''].join('\n');
}

const css = `body{font-family:system-ui,"Malgun Gothic",sans-serif;margin:24px;color:#1f2328;background:#fff}h1{font-size:20px}p.meta{color:#57606a;font-size:13px;margin:4px 0}
.tree,.tree ul{list-style:none;margin:0;padding:0}.tree ul{display:flex;justify-content:center;padding-top:22px;position:relative}
.tree li{display:flex;flex-direction:column;align-items:center;position:relative;padding:22px 8px 0}
.tree li::before,.tree li::after{content:"";position:absolute;top:0;right:50%;width:50%;height:22px;border-top:2px solid #afb8c1}
.tree li::after{right:auto;left:50%;border-left:2px solid #afb8c1}.tree li:only-child::before,.tree li:only-child::after{border-top:0}
.tree li:first-child::before,.tree li:last-child::after{border-top:0}.tree li:last-child::before{border-right:2px solid #afb8c1}.tree li:last-child::after{border-left:0}
.tree li:only-child::before{border-right:2px solid #afb8c1}.tree>li{padding-top:0}.tree>li::before,.tree>li::after{display:none}
.tree ul::before{content:"";position:absolute;top:0;left:50%;height:22px;border-left:2px solid #afb8c1}
.node{border:2px solid #0969da;border-radius:8px;padding:8px 10px;width:230px;background:#fff;font-size:13px;text-align:left}
.node.goal{border-color:#1f2328;background:#f6f8fa;font-weight:600}.node.confirmed{border-color:#1a7f37}.node.deferred{border-color:#9a6700;border-style:dashed}.node.excluded{border-color:#8c959f;border-style:dotted;color:#6e7781}
.node.current{box-shadow:0 0 0 4px #ffd33d}.node b{display:block}.node small{color:#57606a;display:block;word-break:break-all}.badge{font-size:11px;border-radius:10px;padding:1px 7px;background:#eaeef2;margin-right:4px}
.node summary{cursor:pointer;color:#57606a;font-size:12px;margin-top:4px}.node dl{margin:6px 0 0}.node dt{font-weight:600;font-size:12px;margin-top:4px}.node dd{margin:0;white-space:pre-wrap;word-break:break-word}
.node pre{background:#f6f8fa;padding:6px;overflow:auto;max-height:240px;font-size:12px;white-space:pre-wrap;word-break:break-all}
.legend span{display:inline-block;border:2px solid;border-radius:6px;padding:1px 8px;margin-right:6px;font-size:12px}@media print{.node{break-inside:avoid}}`;

/** One self-contained page: no script, no network, no external file. */
export function exportHtml(d: WorkspaceDocument, goalId: string, at: string): string {
  const v = view(d, goalId), h = escapeHtml;
  const node = (s: InvestigationStep): string => {
    const notes = [['이유', s.reason] as const, ...noteKeys.map(k => [fields[k], s[k]] as const)].filter(([, value]) => value.trim()).map(([label, value]) => `<dt>${h(label)}</dt><dd>${h(value)}</dd>`).join('');
    const proof = d.evidence.filter(e => e.stepId === s.id).map(e => `<dt>근거 — ${h(evidenceLabels[e.kind])}</dt><dd>${h(e.text + (e.kind === 'ct_observed' ? `\n${e.executionLabel ?? ''} · ${e.observedAt ?? ''}` : '') + (e.memo ? `\n${e.memo}` : ''))}</dd>`).join('');
    const relation = v.relation(s), below = v.children(s.id);
    return `<li><div class="node ${s.status}${s.id === v.current ? ' current' : ''}"><b>${s.sequence}. ${h(oneLine(s.reason))}</b><span class="badge">${h(statusLabels[s.status])}</span>${relation ? `<span class="badge">${h(relation)}</span>` : ''}${s.id === v.current ? '<span class="badge">현재</span>' : ''}<small>${h(v.place(s))}</small>`
      + `<details><summary>메모와 코드</summary><dl>${notes}${proof}</dl><pre>${h(s.snippet)}</pre></details></div>${below.length ? `<ul>${below.map(node).join('')}</ul>` : ''}</li>`;
  };
  const roots = v.children(undefined);
  return `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline'"><title>${h(oneLine(v.title, 200))}</title><style>${css}</style></head><body>`
    + `<h1>조사 그림: ${h(oneLine(v.title, 200))}</h1><p class="meta">내보낸 시각: ${h(at)} · 단계 ${v.steps.length}개 (${h(v.counts)})</p><p class="meta">${h(NOTICE)}</p>`
    + `<p class="meta legend"><span style="border-color:#0969da">조사 중</span><span style="border-color:#1a7f37">확인</span><span style="border-color:#9a6700;border-style:dashed">보류</span><span style="border-color:#8c959f;border-style:dotted">제외</span><span style="border-color:#ffd33d;background:#fff8c5">현재 단계</span></p>`
    + `<ul class="tree"><li><div class="node goal">목표: ${h(oneLine(v.title, 200))}${v.description.trim() ? `<small>${h(oneLine(v.description, 300))}</small>` : ''}</div>${roots.length ? `<ul>${roots.map(node).join('')}</ul>` : ''}</li></ul></body></html>\n`;
}

export function exportGoal(d: WorkspaceDocument, goalId: string, format: ExportFormat, at: string): string {
  return format === 'diagram' ? exportHtml(d, goalId, at) : format === 'mermaid' ? exportMermaid(d, goalId, at) : exportMarkdown(d, goalId, format === 'handover', at);
}
/** A file name from the goal title: characters that file systems refuse are replaced, never taken from recorded code. */
export const exportFileName = (title: string, format: ExportFormat, day: string): string => `조사-${oneLine(title, 40).replace(/[\\/:*?"<>|.\s]+/g, '_').replace(/^_+|_+$/g, '') || '목표'}-${day}${format === 'mermaid' ? '-graph' : ''}.${exportFormats[format].extension}`;
