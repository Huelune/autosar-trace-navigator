import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { pathToFileURL } from 'node:url';
import { CodeAnchor, fingerprint, id } from '../../src/domain/model';
import { anchorCandidates, offsets, resolveAnchor } from '../../src/navigation/anchorResolver';
import { detailBody, detailScript, escapeHtml, nonce, shell } from '../../src/ui/html';
import { InvestigationStep } from '../../src/domain/model';
test('UTF-16 emoji Korean CRLF and end exclusive ranges select exact source text',()=>{const text='/*한글😀*/\r\nif (a) 😀done\r\n';const [s,e]=offsets(text,{start:{line:1,character:7},end:{line:1,character:9}});assert.equal(text.slice(s,e),'😀');assert.throws(()=>offsets(text,{start:{line:4,character:0},end:{line:4,character:1}}));assert.throws(()=>fingerprint('\ud83d'));assert.throws(()=>fingerprint('\ude00'));assert.notEqual(fingerprint('😀'),fingerprint('😁'));});
test('anchor checks live unsaved buffer, missing file, changed text and manual snippet',async()=>{const root=await fs.mkdtemp(path.resolve('../../build/anchor-unit-')),file=path.join(root,'a.c');await fs.writeFile(file,'a >= 60');const a:CodeAnchor={id:id(),codeNodeId:id(),fileUri:pathToFileURL(file).href,relativePath:'a.c',range:{start:{line:0,character:0},end:{line:0,character:7}},textFingerprint:fingerprint('a >= 60'),contextBefore:'',contextAfter:'',state:'linked'};try{assert.equal((await resolveAnchor(root,a,async()=> 'a >= 60')).state,'verified');assert.equal((await resolveAnchor(root,a,async()=> 'a >= 61')).state,'needs_review');assert.equal((await resolveAnchor(root,{...a,fileUri:undefined},async()=>{throw Error('should not read');})).state,'snippet_only');await fs.unlink(file);assert.equal((await resolveAnchor(root,a,async()=> 'a >= 60')).state,'missing');}finally{await fs.rm(root,{recursive:true,force:true});}});
test('source links escaping real workspace never call document loader',async()=>{const root=await fs.mkdtemp(path.resolve('../../build/anchor-unit-')),outside=await fs.mkdtemp(path.resolve('../../build/anchor-out-'));await fs.writeFile(path.join(outside,'secret.c'),'not a fixture to read');const a:CodeAnchor={id:id(),codeNodeId:id(),fileUri:pathToFileURL(path.join(outside,'secret.c')).href,relativePath:'secret.c',range:{start:{line:0,character:0},end:{line:0,character:1}},textFingerprint:fingerprint('x'),contextBefore:'',contextAfter:'',state:'linked'};let read=false;try{assert.equal((await resolveAnchor(root,a,async()=>{read=true;return 'x';})).state,'needs_review');assert.equal(read,false);}finally{await fs.rm(root,{recursive:true,force:true});await fs.rm(outside,{recursive:true,force:true});}});
test('webview text is escaped and CSP contains no network or unsafe-inline permissions',()=>{const token=nonce(),html=shell('test',`<pre>${escapeHtml('</pre><script>alert(1)</script>')}</pre>`,'',token);assert.ok(!html.includes('<script>alert'));assert.match(html,/default-src 'none'/);assert.ok(!html.includes('unsafe-inline'));assert.notEqual(token,nonce());});
test('detail panel shows the code first and keeps everything the user wrote in closed sections',()=>{
  const anchor={id:'a',codeNodeId:'n',relativePath:'src/a.c',range:{start:{line:2,character:4},end:{line:2,character:20}},textFingerprint:'f',contextBefore:'',contextAfter:'',state:'linked' as const};
  const step={id:'s',reason:'<b>왜</b> 봤는가\n둘째 줄',snippet:'if (a < b) { x = "</pre>"; }',hypothesis:'가정 내용',requiredConditions:'',derivedConditions:'',observation:'',result:'',nextAction:'',status:'investigating',goalSnapshot:{title:'목표',description:'설명',target:{anchorId:'a',kind:'manual'},anchor}} as unknown as InvestigationStep;
  const body=detailBody(step,anchor,'위치 일치',[{id:'e',stepId:'s',kind:'hypothesis',text:'근거 내용'}],false);
  assert.ok(body.startsWith('<pre class="code">if (a &lt; b) { x = &quot;&lt;/pre&gt;&quot;; }</pre>'));
  assert.ok(body.indexOf('src/a.c L3:5')<body.indexOf('<details'));
  assert.equal(body.match(/<details id="section-(edit|goal|evidence)">/g)?.length,3);assert.ok(!/<details[^>]*\sopen/.test(body));
  // Written text lives only inside the closed sections; the summary shows one escaped line of the reason.
  assert.ok(body.includes('<summary>선택 이유 · 조사 정보 — &lt;b&gt;왜&lt;/b&gt; 봤는가</summary>'));assert.ok(!body.includes('<b>'));
  for(const written of ['가정 내용','근거 내용','설명','둘째 줄']){assert.ok(body.indexOf(written)>body.indexOf('<details'),written);}
  assert.ok(body.includes('<summary>근거 1개'));assert.ok(detailScript('s').includes('getState'));
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
