import { randomBytes } from 'node:crypto';
import { CodeAnchor, Evidence, InvestigationStep, statusLabels } from '../domain/model';
export const escapeHtml = (value: string): string => value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
export const nonce = (): string => randomBytes(24).toString('base64');
/** Location lines the panel colours: anything else is a problem the user should look at. */
export const LOCATION_CHECKING = '위치 확인 중…';
export const LOCATION_VERIFIED = '저장한 범위의 지금 텍스트가 같습니다 (실행 검증 아님)';

// VS Code theme variables only, so dark, light and high-contrast themes all apply. contrastBorder is set only in high-contrast themes.
export const styles = `
:root{color-scheme:light dark}
body{font-family:var(--vscode-font-family);font-size:var(--vscode-font-size,13px);line-height:1.5;color:var(--vscode-foreground);background:var(--vscode-editor-background);margin:0;padding:12px 16px 24px;max-width:72ch}
::selection{background:var(--vscode-editor-selectionBackground)}
:focus-visible{outline:1px solid var(--vscode-focusBorder);outline-offset:2px}
h1{font-size:1.3em;font-weight:600;line-height:1.35;margin:4px 0 6px;overflow-wrap:anywhere}
h2{font-size:1em;font-weight:600;margin:0}
p{margin:0}
.muted{color:var(--vscode-descriptionForeground)}
.head{padding-bottom:10px;border-bottom:1px solid var(--vscode-widget-border,var(--vscode-contrastBorder,transparent))}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;color:var(--vscode-descriptionForeground)}
.badge{display:inline-block;padding:0 7px;border-radius:9px;background:var(--vscode-badge-background);color:var(--vscode-badge-foreground);font-size:max(12px,.92em);line-height:1.6}
.badge.deferred,.badge.excluded{background:transparent;color:var(--vscode-descriptionForeground);border:1px solid var(--vscode-descriptionForeground)}
.goal{margin-top:2px;overflow-wrap:anywhere}
.goal strong{font-weight:600}
.memo{margin-top:6px;white-space:pre-wrap;overflow-wrap:anywhere}
.memo strong{font-weight:600;margin-right:6px}
section{margin-top:18px}
.bar{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px}
.where{color:var(--vscode-descriptionForeground);margin-bottom:4px;overflow-wrap:anywhere}
.code{display:grid;grid-template-columns:auto 1fr;margin:0;padding:8px 0;max-height:24em;overflow:auto;font-family:var(--vscode-editor-font-family,monospace);font-size:var(--vscode-editor-font-size,13px);line-height:1.45;tab-size:4;background:var(--vscode-textCodeBlock-background);border:1px solid var(--vscode-contrastBorder,transparent);border-radius:3px}
.code .ln{padding:0 10px 0 12px;text-align:right;color:var(--vscode-editorLineNumber-foreground);user-select:none}
.code .tx{padding-right:12px;white-space:pre}
.location{margin-top:6px}
.location.warn{color:var(--vscode-editorWarning-foreground)}
.location.pending{color:var(--vscode-descriptionForeground)}
dl{margin:0}
.group{margin-top:12px}
.group h3{font-size:max(12px,.92em);font-weight:600;color:var(--vscode-descriptionForeground);margin:0 0 2px}
dt{font-weight:600;margin-top:6px}
dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}
.empty{color:var(--vscode-descriptionForeground)}
form{margin:0}
fieldset{border:0;margin:14px 0 0;padding:0}
legend{font-weight:600;padding:0;margin-bottom:2px}
label{display:block;margin-top:10px}
.hint{display:block;color:var(--vscode-descriptionForeground);font-size:max(12px,.92em)}
textarea,input:not([type=radio]),select{box-sizing:border-box;width:100%;margin-top:3px;padding:5px 7px;font:inherit;background:var(--vscode-input-background);color:var(--vscode-input-foreground);border:1px solid var(--vscode-input-border,var(--vscode-contrastBorder,var(--vscode-widget-border,transparent)));border-radius:2px}
textarea{min-height:4.5em;resize:vertical}
select{width:auto;min-width:12em}
::placeholder{color:var(--vscode-input-placeholderForeground)}
.choices{display:flex;flex-wrap:wrap;gap:4px 16px;margin-top:3px}
.choices label{display:flex;align-items:center;gap:5px;margin:0}
.choices input{margin:0;accent-color:var(--vscode-focusBorder)}
.row{display:flex;gap:6px}
.row input{flex:1}
.actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:14px}
button{font:inherit;padding:4px 12px;border:1px solid var(--vscode-button-border,transparent);border-radius:2px;background:var(--vscode-button-background);color:var(--vscode-button-foreground);cursor:pointer}
button:hover{background:var(--vscode-button-hoverBackground)}
button.secondary{background:var(--vscode-button-secondaryBackground);color:var(--vscode-button-secondaryForeground)}
button.secondary:hover{background:var(--vscode-button-secondaryHoverBackground)}
button:disabled{opacity:.5;cursor:default}
.ev{list-style:none;margin:0;padding:0}
.ev li{margin-top:8px;padding:7px 10px;border:1px solid var(--vscode-widget-border,var(--vscode-contrastBorder,transparent));border-radius:3px}
.ev li.hypothesis{border-style:dashed}
.ev li.ct_observed{border-color:var(--vscode-testing-iconPassed,var(--vscode-focusBorder))}
.ev .kind{font-weight:600}
.ev .text{white-space:pre-wrap;overflow-wrap:anywhere;margin-top:2px}
details{margin-top:10px}
summary{cursor:pointer;padding:3px 0;color:var(--vscode-textLink-foreground)}
summary:hover{color:var(--vscode-textLink-activeForeground)}
#feedback{min-height:1.5em;margin-top:6px}
#feedback.warn{color:var(--vscode-editorWarning-foreground)}
.foot{margin-top:22px;color:var(--vscode-descriptionForeground);font-size:max(12px,.92em)}
[hidden]{display:none!important}
`;
export function shell(title: string, body: string, script: string, token: string): string { return `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'nonce-${token}';script-src 'nonce-${token}';"><title>${escapeHtml(title)}</title><style nonce="${token}">${styles}</style></head><body>${body}<script nonce="${token}">${script}</script></body></html>`; }
export const fields = {reason:'선택 이유',hypothesis:'가정',requiredConditions:'필요 조건',derivedConditions:'도출 조건',observation:'관찰',result:'결과',nextAction:'다음 할 일'} as const;
type Field = keyof typeof fields;
const hints: Record<Field, string> = {
  reason: '이 코드를 왜 보는지. 필수입니다.', hypothesis: '아직 확인하지 않은 추측.',
  requiredConditions: '목표 분기에 닿으려면 성립해야 하는 조건.', derivedConditions: '코드를 읽고 이끌어 낸 조건(예: 입력 범위).',
  observation: '코드나 실행에서 직접 본 것.', result: '이 단계의 결론.', nextAction: '이어서 할 일. 미해결 목록에 나옵니다.'
};
/** Thinking, what was found, and what comes next: the same three groups in the view and in the form. */
const groups: [string, Field[]][] = [['생각', ['reason', 'hypothesis']], ['확인한 것', ['requiredConditions', 'derivedConditions', 'observation', 'result']], ['다음', ['nextAction']]];
const evidenceKinds: Record<Evidence['kind'], [string, string]> = {
  source_fact: ['소스 근거', '사람이 소스에서 읽은 사실'], hypothesis: ['가설', '확인되지 않음'], ct_observed: ['CT 실측', 'CT 실행에서 사람이 확인']
};
const h = escapeHtml;
const lines = (a: CodeAnchor): string => !a.range ? '' : a.range.start.line === a.range.end.line ? `${a.range.start.line + 1}행` : `${a.range.start.line + 1}–${a.range.end.line + 1}행`;
const place = (a: CodeAnchor): string => [a.relativePath ?? '파일 없는 메모', lines(a)].filter(Boolean).join(' · ');
const utcLabel = (iso?: string): string => iso ? iso.replace('T', ' ').replace(/:\d\d(\.\d+)?Z$/, ' UTC') : '';

/**
 * Who, where and why first (step, status, goal), then the code, then what was recorded.
 * Recorded text is read-only until 편집; empty fields are not shown. Nothing here edits the code.
 */
export function detailBody(step: InvestigationStep, anchor: CodeAnchor, locationState: string, evidence: Evidence[], dirty: boolean): string {
  const goal = step.goalSnapshot, title = step.reason.split(/\r?\n/).find(l => l.trim()) ?? step.reason;
  const target = [({ manual: '수동 분기', if: 'if', else_if: 'else if', else: 'else' })[goal.target.kind], goal.target.condition, goal.target.requiredTruth === undefined ? '' : goal.target.requiredTruth ? '참 필요' : '거짓 필요'].filter(Boolean).join(' · ');
  const tone = locationState === LOCATION_CHECKING ? 'pending' : locationState === LOCATION_VERIFIED ? 'ok' : 'warn';
  const first = anchor.range ? anchor.range.start.line + 1 : undefined;
  const code = step.snippet.split(/\r?\n/).map((line, i) => `<span class="ln" aria-hidden="true">${first === undefined ? '' : first + i}</span><span class="tx">${h(line) || ' '}</span>`).join('');

  const head = `<header class="head"><div class="meta"><span>조사 #${step.sequence}</span><span class="badge ${step.status}">${statusLabels[step.status]}</span>${dirty ? '<span>기록 파일에 쓰는 중</span>' : ''}</div>`
    + `<h1>${h(title)}</h1><p class="goal"><strong>목표</strong> ${h(goal.title)}${target ? ` <span class="muted">— ${h(target)}</span>` : ''}</p>`
    + (step.memo ? `<p class="memo"><strong>메모</strong>${h(step.memo)}</p>` : '') + `</header>`;
  const source = `<section aria-labelledby="h-code"><h2 id="h-code" class="where">${h(place(anchor))}</h2><pre class="code" tabindex="0" aria-label="저장한 코드">${code}</pre>`
    + `<p class="location ${tone}" role="status">${h(locationState)}</p></section>`;

  const more = (k: Field): boolean => k === 'reason' ? step.reason.trim() !== title.trim() : !!step[k].trim(); // a one-line reason is already the title
  const shown = groups.map(([name, keys]) => [name, keys.filter(more)] as const).filter(([, keys]) => keys.length);
  const view = `<div id="record-view">${shown.length ? shown.map(([name, keys]) => `<div class="group"><h3>${name}</h3><dl>${keys.map(k => `<dt>${fields[k]}</dt><dd>${h(step[k])}</dd>`).join('')}</dl></div>`).join('') : ''}`
    + (shown.every(([, keys]) => keys.every(k => k === 'reason')) ? '<p class="empty group">가정·조건·결과·다음 할 일은 아직 없습니다. 편집에서 적습니다.</p>' : '') + `</div>`;
  const form = `<form id="edit" hidden><label>조사 상태 <select name="status" aria-describedby="hint-status">${Object.entries(statusLabels).map(([v, l]) => `<option value="${v}"${v === step.status ? ' selected' : ''}>${l}</option>`).join('')}</select><span class="hint" id="hint-status">확인은 사람의 판단이며 CT 실측 확인이 아닙니다.</span></label>`
    + groups.map(([name, keys]) => `<fieldset><legend>${name}</legend>${keys.map(k => `<label>${fields[k]}${k === 'reason' ? ' (필수)' : ''}<span class="hint" id="hint-${k}">${hints[k]}</span><textarea name="${k}" maxlength="65536" aria-describedby="hint-${k}"${k === 'reason' ? ' required' : ''}>${h(step[k])}</textarea></label>`).join('')}</fieldset>`).join('')
    + `<div class="actions"><button type="submit" id="save">저장</button><button type="button" class="secondary" id="cancel">취소</button><span class="hint">Ctrl+Enter 저장 · Esc 취소</span></div></form>`;
  const record = `<section aria-labelledby="h-record"><div class="bar"><h2 id="h-record">조사 기록</h2><button type="button" class="secondary" id="edit-open">편집</button></div>${view}${form}<p id="feedback" role="status" aria-live="polite"></p></section>`;

  const items = evidence.map(e => `<li class="${e.kind}"><span class="kind">${evidenceKinds[e.kind][0]}</span> <span class="muted">${e.kind === 'ct_observed' ? h(`${e.executionLabel ?? ''} · ${utcLabel(e.observedAt)}`) : evidenceKinds[e.kind][1]}</span><p class="text">${h(e.text)}</p>${e.memo ? `<p class="text muted">${h(e.memo)}</p>` : ''}</li>`).join('');
  const add = `<details id="section-add-evidence"><summary>근거 추가</summary><form id="evidence"><fieldset><legend>종류</legend><div class="choices">${(Object.keys(evidenceKinds) as Evidence['kind'][]).map((k, i) => `<label><input type="radio" name="kind" value="${k}"${i === 0 ? ' checked' : ''}>${evidenceKinds[k][0]}</label>`).join('')}</div></fieldset>`
    + `<label>내용 (필수)<textarea name="text" maxlength="65536" required></textarea></label>`
    + `<fieldset id="ct-fields" hidden disabled><legend>CT 실측 정보</legend><label>CT 실행 이름 (필수)<input name="executionLabel" maxlength="200" required></label>`
    + `<label>관찰 시각 (UTC, 필수)<span class="row"><input name="observedAt" maxlength="40" required pattern="\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}(:\\d{2}(\\.\\d{1,3})?)?Z" placeholder="예: 2026-11-10T01:00:00Z" aria-describedby="hint-time"><button type="button" class="secondary" id="now">지금</button></span><span class="hint" id="hint-time">UTC 기준입니다. "지금"은 이 PC의 현재 시각을 UTC로 넣습니다.</span></label>`
    + `<label>확인 메모 (필수)<textarea name="memo" maxlength="65536" required></textarea></label></fieldset><div class="actions"><button type="submit" id="add">근거 추가</button></div></form></details>`;
  const proof = `<section aria-labelledby="h-evidence"><h2 id="h-evidence">근거 ${evidence.length}개</h2>${items ? `<ul class="ev" data-count="${evidence.length}">${items}</ul>` : `<p class="empty" data-count="0">아직 근거가 없습니다. 소스에서 읽은 사실, 가설, CT 실측을 구분해 남깁니다.</p>`}${add}</section>`;

  const about = `<details id="section-goal"><summary>당시 목표 자세히</summary><p>${h(goal.description) || '<span class="muted">설명 없음</span>'}</p><p class="muted">${h(place(goal.anchor))}</p></details>`;
  return `${head}${source}${record}${proof}${about}<p class="foot">조사 순서는 실제 실행 순서가 아닙니다.</p>`;
}

/**
 * Typed text survives a redraw: drafts are kept per step in the webview state and come back when the step is shown again.
 * A draft equal to what the host rendered has been saved, so it is dropped; that is also how "저장됨" is known.
 */
export function detailScript(stepId: string, sequence = 0): string {
  return `(()=>{const vscode=acquireVsCodeApi(),stepId=${JSON.stringify(stepId)},seq=${JSON.stringify(sequence)};
const st=Object.assign({open:[],drafts:{},editing:{}},vscode.getState()||{});const save=()=>vscode.setState(st);
const $=id=>document.getElementById(id),feedback=(text,warn)=>{$('feedback').textContent=text;$('feedback').classList.toggle('warn',!!warn);};
const edit=$('edit'),view=$('record-view'),ev=$('evidence'),ct=$('ct-fields');
const values=f=>Object.fromEntries([...f.elements].filter(e=>e.name&&(e.type!=='radio'||e.checked)).map(e=>[e.name,e.value]));
const defaults=f=>Object.fromEntries([...f.elements].filter(e=>e.name&&(e.type!=='radio'||e.defaultChecked)).map(e=>[e.name,e.type==='radio'?e.value:e.tagName==='SELECT'?[...e.options].find(o=>o.defaultSelected)?.value:e.defaultValue]));
const same=(a,b)=>Object.keys(b).every(k=>(a[k]??'')===(b[k]??''));
const fill=(f,v)=>{for(const e of f.elements){if(!e.name||!(e.name in v))continue;if(e.type==='radio'){e.checked=e.value===v[e.name];}else{e.value=v[e.name];}}};
const draft=()=>st.drafts[stepId]??={seq};
const editing=(on,focus)=>{edit.hidden=!on;view.hidden=on;$('edit-open').hidden=on;st.editing[stepId]=on;save();if(on&&focus){edit.querySelector('textarea').focus();}};
const kind=()=>{const isCt=ev.elements.kind.value==='ct_observed';ct.hidden=!isCt;ct.disabled=!isCt;};
for(const d of document.querySelectorAll('details')){d.open=st.open.includes(d.id);d.addEventListener('toggle',()=>{st.open=st.open.filter(x=>x!==d.id).concat(d.open?[d.id]:[]);save();});}
const mine=st.drafts[stepId],at=new Date().toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit',hour12:false});
if(mine?.edit){if(same(mine.edit,defaults(edit))){delete mine.edit;if(st.pending?.stepId===stepId&&st.pending.kind==='save'){feedback('저장됨 '+at);}st.editing[stepId]=false;}else{fill(edit,mine.edit);st.editing[stepId]=true;feedback('저장하지 않은 입력을 되살렸습니다. 취소하면 버립니다.');}}
else if(st.pending?.stepId===stepId&&st.pending.kind==='save'){feedback('저장됨 '+at);}
const count=Number(document.querySelector('[data-count]').dataset.count);
if(st.pending?.stepId===stepId&&st.pending.kind==='evidence'&&count>st.pending.count){if(mine){delete mine.evidence;}feedback('근거를 추가했습니다 '+at);}
else if(mine?.evidence){fill(ev,mine.evidence);if(!st.open.includes('section-add-evidence')){st.open.push('section-add-evidence');}document.getElementById('section-add-evidence').open=true;}
if(st.pending?.stepId===stepId){delete st.pending;}
if(mine&&!mine.edit&&!mine.evidence){delete st.drafts[stepId];}
const others=Object.entries(st.drafts).filter(([id])=>id!==stepId).map(([,d])=>'#'+d.seq);
if(others.length&&!$('feedback').textContent){feedback('다른 단계('+others.join(', ')+')에 저장하지 않은 입력이 있습니다. 그 단계를 열면 되살아납니다.');}
editing(!!st.editing[stepId]);kind();save();
edit.addEventListener('input',()=>{draft().edit=values(edit);save();});
ev.addEventListener('input',()=>{const v=values(ev);if(v.text||v.executionLabel||v.observedAt||v.memo){draft().evidence=v;}else if(st.drafts[stepId]){delete st.drafts[stepId].evidence;}save();});
ev.addEventListener('change',kind);
$('edit-open').addEventListener('click',()=>editing(true,true));
const cancel=()=>{if(st.drafts[stepId]){delete st.drafts[stepId].edit;}fill(edit,defaults(edit));editing(false);feedback('');$('edit-open').focus();};
$('cancel').addEventListener('click',cancel);
edit.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();cancel();}});
for(const f of [edit,ev]){f.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();f.requestSubmit();}});}
$('now').addEventListener('click',()=>{ev.elements.observedAt.value=new Date().toISOString().replace(/\\.\\d+Z$/,'Z');ev.elements.observedAt.dispatchEvent(new Event('input',{bubbles:true}));});
const busy=on=>{for(const b of document.querySelectorAll('button[type=submit]')){b.disabled=on;}};
edit.addEventListener('submit',e=>{e.preventDefault();draft().edit=values(edit);st.pending={stepId,kind:'save'};save();busy(true);feedback('저장 중…');vscode.postMessage({type:'save',stepId,edit:values(edit)});});
ev.addEventListener('submit',e=>{e.preventDefault();const all=values(ev),evidence={kind:all.kind,text:all.text};if(all.kind==='ct_observed'){Object.assign(evidence,{executionLabel:all.executionLabel,observedAt:all.observedAt,memo:all.memo});}
  draft().evidence=all;st.pending={stepId,kind:'evidence',count};save();busy(true);feedback('근거 추가 중…');vscode.postMessage({type:'evidence',stepId,evidence});});
window.addEventListener('message',e=>{if(e.data?.type==='failed'){delete st.pending;save();busy(false);feedback('저장하지 못했습니다. 입력은 그대로 있습니다. 알림의 이유를 확인하세요.',true);}});
})();`;
}
