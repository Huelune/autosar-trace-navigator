import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import type {OriginNode,ValueGraphResult} from '../../src/adapters/traceAnalysisPort';
import {createOriginFlow} from '../../src/ui/valueGraphFlow';
import {graphPage,renderOriginFlow} from '../../src/ui/valueGraphView';

const n=(id:string,expression:string,kind='probe',terminal:OriginNode['terminal']='none',functionName='Check'):OriginNode=>({id,expression,kind,terminal,functionName,
  location:{path:'Callers.c',startLine:3,endLine:3,startCharacter:0,endCharacter:5,text:expression},requiredTruth:kind==='condition'?true:null,uncertainty:[],detailsTruncated:false,
  context:{startLine:2,text:'unsigned amount = Raw * 2u;\nCheck(999u, amount);\nreturn 0;'}});
function fixture():ValueGraphResult{
  const nodes=[n('n1','pedal'),n('n2','fast','parameter_input','none','Fast'),n('n3','command','parameter_input','none','Relay'),n('n4','Raw','ct_global_input','ct_input','Input'),n('n5','Gate != 0u','condition'),n('n6','Gate','ct_global_input','ct_input'),n('n7','amount','parameter_input','none','Run')];
  nodes[1].uncertainty=['name_only_caller_candidate'];nodes[2].uncertainty=['name_only_caller_candidate'];
  return {variable:'pedal',rootId:'n1',nodes,edges:[{from:'n1',to:'n2',relation:'value',cycle:false},{from:'n1',to:'n3',relation:'value',cycle:false},{from:'n2',to:'n4',relation:'value',cycle:false},{from:'n3',to:'n7',relation:'value',cycle:false},{from:'n7',to:'n4',relation:'value',cycle:false},{from:'n7',to:'n5',relation:'condition',cycle:false},{from:'n5',to:'n6',relation:'condition',cycle:false}],limitReasons:[],truncated:false};
}

test('default value route excludes guard-only inputs, keeping them available as condition investigations',()=>{
  const model=createOriginFlow(fixture());assert.deepEqual(model.initial().route,['n1','n2','n4']);
  assert.deepEqual(model.endpoints.map(n=>n.id),['n4']);
  const route=model.navigate(model.initial(),'branch','n3',0);assert.deepEqual(route.route,['n1','n3','n7','n4']);
  const condition=model.navigate(route,'condition','n5');assert.deepEqual(condition.route,['n1','n3','n7','n5','n6']);
  assert.equal(model.isConditionRoute(condition.route),true);assert.deepEqual(model.navigate(condition,'return').route,route.route);
  assert.equal(model.role(model.nodes.get('n3')!),'호출부 인수');
});

test('switching a branch retains its caller prefix even when another route reaches the shared input sooner',()=>{
  const model=createOriginFlow(fixture()),s={...model.initial(),route:['n1','n3','n7']};
  const next=model.navigate(s,'branch','n4',2);assert.deepEqual(next.route,['n1','n3','n7','n4']);
  assert.deepEqual(model.routeTo('n4'),['n1','n2','n4']);assert.deepEqual(model.navigate(next,'focus',undefined,1).route,next.route);
});

test('a function-return argument shows the actual calling site instead of mislabelling the helper as caller',()=>{
  const graph=fixture();graph.nodes[1].kind='return_value';graph.nodes[1].expression='GetRaw()';graph.nodes[1].functionName='GetRaw';graph.nodes[1].siteFunctionName='Caller_Run';
  const model=createOriginFlow(graph),s=model.navigate(model.initial(),'focus',undefined,1);
  assert.equal(model.groups(s.route)[1].functionName,'Caller_Run');
  const page=renderOriginFlow(graph,model,s,'목표');assert.ok(page.includes('Caller_Run에서 전달한 GetRaw()'));assert.ok(!page.includes('GetRaw에서 전달한'));
  graph.edges[0].relation='rte_data';assert.ok(renderOriginFlow(graph,createOriginFlow(graph),s,'목표').includes('RTE 공급 후보'));
});

test('an unresolved value source is never replaced with an input found only through a guard',()=>{
  const graph=fixture();graph.nodes[3].terminal='unresolved';graph.nodes[3].kind='unresolved_call';graph.nodes[3].expression='UnknownCast(value)';
  const model=createOriginFlow(graph),s=model.initial();assert.equal(model.endpoints.some(n=>n.terminal==='ct_input'),false);
  assert.equal(model.nodes.get(s.route.at(-1)!)!.terminal,'unresolved');
  assert.ok(renderOriginFlow(graph,model,s,'목표').includes('조건 입력은 별도 경로'));
  const relay=model.navigate(s,'branch','n3',0),guard=model.navigate(relay,'condition','n5');assert.equal(guard.route.at(-1),'n6');
});

test('cycles stop at a reference and a malformed saved route is discarded',()=>{
  const graph=fixture();graph.edges.push({from:'n4',to:'n1',relation:'value',cycle:true});
  const model=createOriginFlow(graph),state=model.navigate(model.initial(),'branch','n1',2);
  assert.deepEqual(state.route,['n1','n2','n4','n1']);assert.ok(model.validRoute(state.route));
  assert.deepEqual(model.restore({...state,route:['n1','n404']}),model.initial());
  assert.deepEqual(model.restore({...state,route:['n1','n2','n1','n2']}),model.initial());
});

test('one function groups its internal transfers without losing focusable source nodes',()=>{
  const graph=fixture();graph.nodes[1].functionName='Check';const model=createOriginFlow(graph),groups=model.groups(model.initial().route);
  assert.equal(groups.length,2);assert.deepEqual(groups[0].indices,[0,1]);
  const page=renderOriginFlow(graph,model,model.initial(),'원래 목표');
  assert.equal((page.match(/id="focus-code"/g)??[]).length,1);assert.ok(page.includes('이 함수 안의 전달 2개'));
  assert.ok(page.replace(/<[^>]+>/g,'').includes('Check(999u, amount)'));assert.ok(page.includes('line-number'));
  assert.ok(page.includes('원래 목표'));assert.ok(!page.includes('<article'));
});

test('code context highlights exactly the selected UTF-16 span, not every variable on the line',()=>{
  const graph=fixture();const text='/*한글 😀*/ if (pedal >= 60u && enabled) return 1;',at=text.indexOf('pedal');
  graph.nodes[0].context={startLine:3,text};
  graph.nodes[0].location={...graph.nodes[0].location,startCharacter:at,endCharacter:at+5,text:'pedal'};
  const model=createOriginFlow(graph),page=renderOriginFlow(graph,model,model.initial(),'목표');
  assert.ok(page.includes('<mark>pedal</mark>'));assert.ok(!page.includes('<mark>enabled</mark>'));
});

test('large all-results view is paged; ordinary view does not render thousands of code cards',()=>{
  const graph=fixture();graph.nodes=Array.from({length:2000},(_,i)=>n(`n${i+1}`,i?'Raw':'pedal','probe',i===1999?'ct_input':'none',`Function_${Math.floor(i/4)}`));
  graph.edges=Array.from({length:1999},(_,i)=>({from:`n${i+1}`,to:`n${i+2}`,relation:'value',cycle:false}));
  const model=createOriginFlow(graph),s=model.initial();assert.equal(model.groups(s.route).length,500);
  const all=renderOriginFlow(graph,model,{...s,mode:'all'},'목표');assert.equal((all.match(/data-nav="inspect"/g)??[]).length,50);
  const flow=renderOriginFlow(graph,model,s,'목표');assert.equal((flow.match(/id="focus-code"/g)??[]).length,1);
});

/** Small DOM harness: executes the shipped inline Webview script, without browser/Computer Use. */
function runtime(graph:ValueGraphResult,standalone=false,saved?:unknown,invalid?:string){
  const page=graphPage(graph,'원래 목표','test-token',invalid,standalone),callbacks:Record<string,(e:any)=>void>={};
  const messages:unknown[]=[];let state:any=saved;
  const app={innerHTML:'',contains:()=>true,querySelector:()=>undefined,addEventListener:(name:string,fn:(e:any)=>void)=>{callbacks[name]=fn;}};
  const input={id:'all-search',selectionStart:2,focus:()=>{},setSelectionRange:()=>{}};
  const feedback={textContent:''},document={activeElement:null,getElementById:(id:string)=>id==='origin-app'?app:id==='all-search'?input:feedback};
  const source=page.match(/<script nonce="test-token">([\s\S]*)<\/script>/)![1];
  vm.runInNewContext(source,{document,acquireVsCodeApi:()=>({getState:()=>state,setState:(v:unknown)=>{state=v;},postMessage:(v:unknown)=>messages.push(v)})});
  const click=(dataset:Record<string,string>)=>callbacks.click({target:{closest:()=>({dataset,disabled:false})}});
  return {app,messages,click,state:()=>state,change:(id:string,value:string)=>callbacks.change({target:{id,value}}),jump:(value:string)=>callbacks.change({target:{dataset:{focus:'true'},value}}),search:(value:string)=>callbacks.input({target:{id:'all-search',value}})};
}

test('actual inline script switches callers and condition routes locally; only explicit source actions send messages',()=>{
  const ui=runtime(fixture());assert.equal(ui.messages.length,0);
  ui.click({nav:'branch',id:'n3',index:'0'});assert.equal(ui.state().route.join(','),'n1,n3,n7,n4');
  assert.ok(ui.app.innerHTML.includes('호출자 역추적 후보'));assert.ok(ui.app.innerHTML.includes('Check의 pedal ← Relay에서 전달한 command'));
  ui.click({nav:'condition',id:'n5'});assert.equal(ui.state().route.at(-1),'n6');assert.ok(ui.app.innerHTML.includes('조건 입력을 거슬러'));
  ui.click({nav:'return'});assert.equal(ui.state().route.join(','),'n1,n3,n7,n4');
  ui.click({nav:'focus',index:'2'});ui.click({action:'open',id:'n7'});
  assert.deepEqual(JSON.parse(JSON.stringify(ui.messages)),[{type:'open',nodeId:'n7',token:'test-token'}]);
  ui.jump('0');assert.equal(ui.state().focus,0);
  ui.click({nav:'all'});ui.search('Gate');assert.ok(ui.app.innerHTML.includes('전체 후보에서 찾기'));assert.ok(ui.app.innerHTML.includes('2개 일치'));
  ui.click({nav:'inspect',id:'n5'});assert.ok(ui.app.innerHTML.includes('조건 입력을 거슬러'));
  assert.equal(ui.messages.length,1);
});

test('view state survives redraw but never another graph; offline and stale panels cannot send source actions',()=>{
  const first=runtime(fixture());first.click({nav:'branch',id:'n3',index:'0'});
  const restored=runtime(fixture(),false,first.state(),'소스 변경됨');assert.equal(restored.state().route.join(','),'n1,n3,n7,n4');
  restored.click({action:'add',id:'n3'});assert.equal(restored.messages.length,0);
  const offline=runtime(fixture(),true);offline.click({action:'open',id:'n1'});assert.equal(offline.messages.length,0);offline.click({nav:'all'});assert.equal(offline.state().mode,'all');
  const changed=fixture();changed.nodes[0].context!.text='changed code';const fresh=runtime(changed,false,first.state());assert.equal(fresh.state().route.join(','),'n1,n2,n4');
});
