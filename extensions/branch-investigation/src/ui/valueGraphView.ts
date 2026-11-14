import { ValueGraphResult, OriginTerminal } from '../adapters/traceAnalysisPort';
import { escapeHtml as h, shell } from './html';

export const terminalNames:Record<OriginTerminal,string>={none:'계속 조사',ct_input:'전역 입력 후보',constant:'상수 후보',unresolved:'미해결',review:'계산·수동 검토',cycle:'순환 참조',limit:'탐색 한도'};
const relationNames={value:'값 출처',call:'호출·반환',rte_data:'RTE 데이터',condition:'필요 조건'};
const kindNames:Record<string,string>={probe:'변수·반환값',condition:'실행 조건',return_value:'함수 반환값',expression:'계산식',expression_operand:'계산 입력',ct_global_input:'전역 입력 후보',constant:'상수',rte_data:'RTE 공급 후보',initializer:'초기값',assignment:'대입',return:'반환 식',parameter_input:'호출 인수',global_write:'전역 쓰기',object_origin:'객체 출처',member_initializer:'멤버 초기값',member_write:'멤버 쓰기',output_parameter:'출력 인수',possible_output_argument:'출력 인수 검토',input_boundary:'입력 경계',unresolved_call:'미해결 호출',missing_rte_producer:'범위 내 RTE 공급자 미발견',call_argument:'호출 인수 검토'};

/** Flat cards retain every edge; shared/cyclic references never grow the DOM recursively. */
export function graphPage(graph:ValueGraphResult,goal:string,token:string,invalid?:string):string{
  const nodes=new Map(graph.nodes.map(n=>[n.id,n])),out=new Map<string,typeof graph.edges>(),incoming=new Map<string,typeof graph.edges>();
  for(const edge of graph.edges){out.set(edge.from,[...(out.get(edge.from)??[]),edge]);incoming.set(edge.to,[...(incoming.get(edge.to)??[]),edge]);}
  const where=(id:string)=>{const n=nodes.get(id)!;return `${n.location.path}:${n.location.startLine+1}`;};
  const link=(id:string,label:string)=>`<a href="#${id}">${h(label)}</a>`;
  const groups=(['ct_input','unresolved','cycle','limit','review','constant'] as OriginTerminal[]).map(state=>{
    const ends=graph.nodes.filter(n=>n.terminal===state);if(!ends.length){return '';}
    return `<details${state==='ct_input'?' open':''}><summary>${h(terminalNames[state])} ${ends.length}개 지점</summary><ul>${ends.map(n=>`<li>${link(n.id,`${n.expression} · ${where(n.id)} · #${n.id.slice(1)}`)}</li>`).join('')}</ul></details>`;
  }).join('');
  const cards=graph.nodes.map(n=>{
    const label=n.kind==='probe'&&n.expression==='$return'?`반환값: ${n.functionName}`:`${kindNames[n.kind]??n.kind}: ${n.requiredTruth===null?'':n.requiredTruth?'참 필요 · ':'거짓 필요 · '}${n.expression}`;
    const next=(out.get(n.id)??[]).map(e=>link(e.to,`${relationNames[e.relation]} → #${e.to.slice(1)}${e.cycle?' (순환 참조)':''}`)).join(' · ');
    const previous=(incoming.get(n.id)??[]).map(e=>link(e.from,`#${e.from.slice(1)}`)).join(' · ');
    const search=h(`${label} ${n.functionName} ${where(n.id)} ${terminalNames[n.terminal]}`.toLowerCase());
    return `<article id="${n.id}" data-search="${search}"><details${n.id===graph.rootId?' open':''}><summary>#${n.id.slice(1)} ${h(label)} — ${h(terminalNames[n.terminal])} · ${h(where(n.id))}</summary><p>${h(n.functionName)} · ${h(n.kind)}</p><pre>${h(n.location.text??'코드 범위가 길거나 인코딩이 미확정입니다. 위치를 수동 검토하세요.')}</pre><p>이전: ${previous||'선택 변수'}<br>다음: ${next||h(terminalNames[n.terminal])}</p><button data-action="open" data-id="${n.id}"${invalid?' disabled':''}>소스 열기</button><button data-action="add" data-id="${n.id}"${invalid?' disabled':''}>이 코드 조사에 추가</button><details><summary>불확실성 ${n.uncertainty.length}개${n.detailsTruncated?' · 세부 일부 생략':''}</summary><pre>${h(n.uncertainty.join('\n'))}</pre></details></details></article>`;
  }).join('');
  const limits=graph.limitReasons.join(', ');
  const body=`<header><h1>${h(graph.variable)} · 전체 출처 후보</h1><p>시작: ${h(where(graph.rootId))}</p><p>목표: ${h(goal||'현재 선택 변수의 출처 조사')}</p><p>${graph.nodes.length}개 지점 · ${graph.edges.length}개 연결 · ${graph.truncated?`일부 탐색 — 한도: ${h(limits)}`:'지원 범위 내 탐색 완료 (미해결 후보 포함 가능)'}</p>${invalid?`<p class="notice">${h(invalid)} 변수에서 다시 조회하세요.</p>`:''}<p class="notice">구문·이름 기반 후보입니다. CT 접근·값 제어·조건 충족·RTE wiring·실제 실행 순서의 증명이 아닙니다. 공통 경로는 지점 번호로 연결하며 순환은 재귀적으로 펼치지 않습니다.</p><label>변수·함수·파일·종료 상태 찾기<input id="filter" maxlength="200" placeholder="예: g_Stimulus, 전역 입력 후보"></label></header><section><p>전역 입력은 외부 연결 이름 기반 후보입니다. 구조체 객체의 출처와 멤버 값 제어·포인터 대상 동일성은 별도로 검토하세요.</p>${groups}</section><h2>전체 연결과 코드</h2>${cards}<p id="feedback" aria-live="polite"></p>`;
  const script=`const vscode=acquireVsCodeApi();const token=${JSON.stringify(token)};const input=document.getElementById('filter');const filter=()=>{const q=input.value.trim().toLowerCase();for(const a of document.querySelectorAll('article')){a.hidden=!a.dataset.search.includes(q);}};input.addEventListener('input',filter);for(const a of document.querySelectorAll('a[href^="#"]')){a.addEventListener('click',e=>{e.preventDefault();input.value='';filter();const card=document.getElementById(a.getAttribute('href').slice(1));if(card){card.querySelector('details').open=true;card.scrollIntoView({block:'center'});}});}for(const b of document.querySelectorAll('button[data-action]')){b.addEventListener('click',()=>{vscode.postMessage({type:b.dataset.action,nodeId:b.dataset.id,token});document.getElementById('feedback').textContent='소스 위치를 확인합니다. 조사 추가는 이유 입력을 완료해야 기록됩니다.';});}`;
  // Keep the context visible while the user scrolls, with no depth-based indentation.
  return shell('변수 전체 출처',body,script,token).replace('</style>',`header{position:sticky;top:0;background:var(--vscode-editor-background);z-index:1;padding:4px 0}header h1{margin:4px 0}header p{margin:5px 0}article{scroll-margin-top:210px;border-bottom:1px solid var(--vscode-widget-border,gray)}a{color:var(--vscode-textLink-foreground)}summary{white-space:normal}button:disabled{opacity:.5;cursor:default}@media(max-height:500px){header{position:static}article{scroll-margin-top:8px}}</style>`);
}
