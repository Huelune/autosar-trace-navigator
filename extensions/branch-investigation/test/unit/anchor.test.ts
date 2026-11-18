import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { pathToFileURL } from 'node:url';
import { CodeAnchor, fingerprint, id } from '../../src/domain/model';
import { anchorCandidates, offsets, resolveAnchor } from '../../src/navigation/anchorResolver';
import { detailBody, detailScript, escapeHtml, LOCATION_VERIFIED, nonce, shell } from '../../src/ui/html';
import { InvestigationStep } from '../../src/domain/model';
test('UTF-16 emoji Korean CRLF and end exclusive ranges select exact source text',()=>{const text='/*한글😀*/\r\nif (a) 😀done\r\n';const [s,e]=offsets(text,{start:{line:1,character:7},end:{line:1,character:9}});assert.equal(text.slice(s,e),'😀');assert.throws(()=>offsets(text,{start:{line:4,character:0},end:{line:4,character:1}}));assert.throws(()=>fingerprint('\ud83d'));assert.throws(()=>fingerprint('\ude00'));assert.notEqual(fingerprint('😀'),fingerprint('😁'));});
test('anchor checks live unsaved buffer, missing file, changed text and manual snippet',async()=>{const root=await fs.mkdtemp(path.resolve('../../build/anchor-unit-')),file=path.join(root,'a.c');await fs.writeFile(file,'a >= 60');const a:CodeAnchor={id:id(),codeNodeId:id(),fileUri:pathToFileURL(file).href,relativePath:'a.c',range:{start:{line:0,character:0},end:{line:0,character:7}},textFingerprint:fingerprint('a >= 60'),contextBefore:'',contextAfter:'',state:'linked'};try{assert.equal((await resolveAnchor(root,a,async()=> 'a >= 60')).state,'verified');assert.equal((await resolveAnchor(root,a,async()=> 'a >= 61')).state,'needs_review');assert.equal((await resolveAnchor(root,{...a,fileUri:undefined},async()=>{throw Error('should not read');})).state,'snippet_only');await fs.unlink(file);assert.equal((await resolveAnchor(root,a,async()=> 'a >= 60')).state,'missing');}finally{await fs.rm(root,{recursive:true,force:true});}});
test('source links escaping real workspace never call document loader',async()=>{const root=await fs.mkdtemp(path.resolve('../../build/anchor-unit-')),outside=await fs.mkdtemp(path.resolve('../../build/anchor-out-'));await fs.writeFile(path.join(outside,'secret.c'),'not a fixture to read');const a:CodeAnchor={id:id(),codeNodeId:id(),fileUri:pathToFileURL(path.join(outside,'secret.c')).href,relativePath:'secret.c',range:{start:{line:0,character:0},end:{line:0,character:1}},textFingerprint:fingerprint('x'),contextBefore:'',contextAfter:'',state:'linked'};let read=false;try{assert.equal((await resolveAnchor(root,a,async()=>{read=true;return 'x';})).state,'needs_review');assert.equal(read,false);}finally{await fs.rm(root,{recursive:true,force:true});await fs.rm(outside,{recursive:true,force:true});}});
test('webview text is escaped and CSP contains no network or unsafe-inline permissions',()=>{const token=nonce(),html=shell('test',`<pre>${escapeHtml('</pre><script>alert(1)</script>')}</pre>`,'',token);assert.ok(!html.includes('<script>alert'));assert.match(html,/default-src 'none'/);assert.ok(!html.includes('unsafe-inline'));assert.notEqual(token,nonce());});
test('detail panel: step, status and goal first, then code, then only the recorded fields; edit form starts hidden',()=>{
  const anchor={id:'a',codeNodeId:'n',relativePath:'src/a.c',range:{start:{line:2,character:4},end:{line:3,character:20}},textFingerprint:'f',contextBefore:'',contextAfter:'',state:'linked' as const};
  const step={id:'s',sequence:7,reason:'<b>왜</b> 봤는가\n둘째 줄',snippet:'if (a < b) {\n  x = "</pre>"; }',hypothesis:'가정 내용',requiredConditions:'',derivedConditions:'',observation:'',result:'',nextAction:'',status:'deferred',memo:'메모 <i>',goalSnapshot:{title:'목표 <제목>',description:'설명',target:{anchorId:'a',kind:'if',condition:'a >= 60u',requiredTruth:true},anchor}} as unknown as InvestigationStep;
  const body=detailBody(step,anchor,LOCATION_VERIFIED,[{id:'e',stepId:'s',kind:'hypothesis',text:'근거 내용'},{id:'c',stepId:'s',kind:'ct_observed',text:'값 확인',executionLabel:'CT-1',observedAt:'2026-11-10T01:00:00.000Z',memo:'확인'}],false);
  assert.ok(body.startsWith('<header class="head">'));assert.ok(!body.includes('<b>')&&!body.includes('<i>')&&!body.includes('<제목>'),'everything is escaped');
  const at=(t:string)=>{const i=body.indexOf(t);assert.ok(i>=0,t);return i;};
  assert.ok(at('조사 #7')<at('<h1>&lt;b&gt;왜&lt;/b&gt; 봤는가</h1>'));assert.ok(at('<span class="badge deferred">보류</span>')<at('<h1>'));
  assert.ok(at('목표 &lt;제목&gt;')<at('a &gt;= 60u · 참 필요')&&at('참 필요')<at('class="code"'),'goal and needed truth are above the code');
  assert.ok(at('메모 &lt;i&gt;')<at('class="code"'));assert.ok(at('src/a.c · 3–4행')<at('class="code"'));
  assert.ok(body.includes('<span class="ln" aria-hidden="true">3</span><span class="tx">if (a &lt; b) {</span><span class="ln" aria-hidden="true">4</span>'),'line numbers start at the saved line');
  assert.ok(body.includes('<p class="location ok" role="status">'));assert.ok(detailBody(step,anchor,'코드가 바뀌었습니다',[],true).includes('class="location warn"'));
  const view=body.slice(at('id="record-view"'),at('<form id="edit" hidden>'));
  assert.ok(view.includes('<dt>가정</dt><dd>가정 내용</dd>')&&view.includes('둘째 줄'));assert.ok(!view.includes('<dt>관찰</dt>'),'empty fields are not shown');
  assert.equal(body.match(/<textarea name="(reason|hypothesis|requiredConditions|derivedConditions|observation|result|nextAction)"/g)?.length,7,'the form still carries every field the host expects');
  assert.ok(body.includes('<li class="hypothesis"><span class="kind">가설</span> <span class="muted">확인되지 않음</span>'));assert.ok(body.includes('<li class="ct_observed"><span class="kind">CT 실측</span> <span class="muted">CT-1 · 2026-11-10 01:00 UTC</span>'));
  assert.ok(body.includes('<fieldset id="ct-fields" hidden disabled>'),'CT-only fields are off until CT 실측 is chosen');
  assert.ok(!/<details[^>]*\sopen/.test(body));const script=detailScript('s',7);assert.ok(script.includes('getState')&&script.includes('drafts'));
});
test('anchor candidates find moved text, rank by saved context and never pick one themselves',()=>{
  const saved='if (a < 60) return 0;',before='  /*한글 😀*/ ',after='\r\n  else return 1;';
  const anchor={range:{start:{line:1,character:12},end:{line:1,character:33}},contextBefore:before,contextAfter:after};
  // Two lines inserted above: the only occurrence is offered at its new UTF-16 position with the full context still matching.
  const moved=`// 추가 😀\r\n// 둘째\r\nint Demo(int a) {\r\n${before}${saved}${after}\r\n}\r\n`,one=anchorCandidates(moved,saved,anchor);
  assert.deepEqual(one,{candidates:[{range:{start:{line:3,character:12},end:{line:3,character:33}},context:'both',lineDelta:2}],truncated:false});
  const [s,e]=offsets(moved,one.candidates[0].range);assert.equal(moved.slice(s,e),saved);
  // The same text twice: both are returned, the one whose surroundings match the saved context first.
  const twice=`${saved}\n${moved}`,two=anchorCandidates(twice,saved,anchor).candidates;
  assert.deepEqual(two.map(c=>[c.range.start.line,c.context]),[[4,'both'],[0,'none']]);
  assert.deepEqual(anchorCandidates('int other;\n',saved,anchor),{candidates:[],truncated:false});assert.equal(anchorCandidates(moved,'',anchor).candidates.length,0);
  // A multi-line snippet saved with LF is still found after the file became CRLF, at offsets of the current text.
  const crlf=anchorCandidates('x;\r\nif (a)\r\n  b();\r\n','if (a)\n  b();',{contextBefore:'',contextAfter:''}).candidates;
  assert.deepEqual(crlf.map(c=>c.range),[{start:{line:1,character:0},end:{line:2,character:6}}]);assert.equal(crlf[0].lineDelta,undefined);
  const many=anchorCandidates('x;'.repeat(300),'x;',anchor,5);assert.equal(many.candidates.length,5);assert.equal(many.truncated,true);
});
