import {test} from 'node:test';
import assert from 'node:assert/strict';
import {AnalysisError,parseValueGraph,PythonTraceAnalysisPort} from '../../src/adapters/traceAnalysisPort';
import {graphPage} from '../../src/ui/valueGraphView';
import {decodeGraphAction} from '../../src/ui/valueGraphMessage';

const location={path:'src/input.c',startLine:3,endLine:3,startCharacter:4,endCharacter:9,text:'pedal'};
const root={id:'n1',kind:'probe',expression:'pedal',functionName:'Goal',location,terminal:'none',requiredTruth:null,uncertainty:[],detailsTruncated:false};
const input={...root,id:'n2',kind:'ct_global_input',expression:'Input',terminal:'ct_input',uncertainty:['ct_accessibility_not_verified']};
const reply={ok:true,variable:'pedal',rootId:'n1',nodes:[root,input],edges:[{from:'n1',to:'n2',relation:'value',cycle:false}],limitReasons:[],truncated:false};
const parse=(v:unknown)=>parseValueGraph(JSON.stringify(v));

test('graph parser retains bounded candidates and rejects unsafe or malformed graphs whole',()=>{
  assert.equal(parse(reply).nodes[1].terminal,'ct_input');
  const malformed=[null,{}, {...reply,nodes:[]},{...reply,nodes:[root,root]},
    {...reply,edges:[{...reply.edges[0],to:'n404'}]}, {...reply,nodes:[root,input,{...input,id:'n3'}]},
    {...reply,edges:[reply.edges[0],reply.edges[0]]}, {...reply,nodes:[root,{...input,location:{...location,path:'../outside.c'}}]},
    {...reply,nodes:[root,{...input,location:{...location,path:'C:/outside.c'}}]},
    {...reply,nodes:[root,{...input,requiredTruth:true}]}, {...reply,nodes:[root,{...input,kind:'condition',requiredTruth:null}]},
    {...reply,truncated:true}, {...reply,limitReasons:['unknown'],truncated:true},
    {...reply,nodes:[root,{...input,terminal:'verified_ct'}]}, {...reply,nodes:[root,{...input,uncertainty:[4]}]},
    {...reply,nodes:Array.from({length:2001},(_,i)=>({...root,id:`n${i+1}`}))}];
  for(const value of malformed){assert.throws(()=>parse(value),(e:AnalysisError)=>e.code==='invalid_response');}
});

test('partial results and cycles remain distinct from input candidates',()=>{
  const limited=parse({...reply,nodes:[{...root,terminal:'limit'}],edges:[],truncated:true,limitReasons:['nodes']});assert.equal(limited.truncated,true);
  const cyclic=parse({...reply,nodes:[root,{...input,terminal:'cycle'}],edges:[reply.edges[0],{from:'n2',to:'n1',relation:'value',cycle:true}]});assert.equal(cyclic.edges[1].cycle,true);
  assert.throws(()=>parse({ok:false,error:'variable_not_supported'}),(e:AnalysisError)=>e.code==='variable_not_supported');
  assert.throws(()=>parse({ok:false,error:'analysis_limit',limitDetails:{metric:'files',observedAtLeast:5125,limit:500}}),(e:AnalysisError)=>e.code==='analysis_limit');
});

test('graph request carries scope and trace limits over the existing isolated process port',async()=>{
  const script=`let data='';process.stdin.on('data',c=>data+=c).on('end',()=>{const r=JSON.parse(data),reply=${JSON.stringify(reply)};reply.variable=reply.nodes[0].expression=r.op;reply.nodes[1].functionName=r.traceLimits.maxNodes+':'+r.excludePaths.join(',');process.stdout.write(JSON.stringify(reply));});`;
  const port=new PythonTraceAnalysisPort(process.execPath,['-e',script]);
  const result=await port.valueGraph({op:'value_graph',root:'C:/synthetic',file:'a.c',line:1,character:2,includePaths:['app'],excludePaths:['noise'],traceLimits:{maxNodes:500,maxDepth:256,maxSeconds:20}},new AbortController().signal);
  assert.equal(result.variable,'value_graph');assert.equal(result.nodes[1].functionName,'500:noise');
});

test('flat view renders shared references and escapes every source-derived field',()=>{
  const graph=parse(reply);graph.nodes[1].expression='<img src=x onerror=run()>';graph.nodes[1].location.text='</pre><script>run()</script>';
  const page=graphPage(graph,'<script>goal()</script>','fixed-token');
  assert.ok(page.includes('href="#n2"'));assert.ok(page.includes('전역 입력 후보'));assert.ok(page.includes('src/input.c:4'));
  assert.ok(page.includes('&lt;img'));assert.ok(!page.includes('<img'));assert.ok(!page.includes('<script>run()'));
  assert.ok(page.includes('&lt;script&gt;goal()'));assert.ok(page.includes('nonce-fixed-token'));
  assert.ok(graphPage(graph,'목표','fixed-token','소스 변경됨').includes(' disabled'));
});

test('2000-deep candidate chain and cyclic references render as 2000 flat cards',()=>{
  const nodes=Array.from({length:2000},(_,i)=>({...root,id:`n${i+1}`,expression:i?`value_${i}`:'pedal'}));
  const edges=Array.from({length:1999},(_,i)=>({from:`n${i+1}`,to:`n${i+2}`,relation:'value',cycle:false}));
  edges.push({from:'n2000',to:'n1000',relation:'condition',cycle:true});
  const graph=parse({...reply,nodes,edges}),page=graphPage(graph,'목표','fixed-token');
  assert.equal((page.match(/<article /g)??[]).length,2000);assert.ok(page.includes('순환 참조'));
});

test('preview message allowlist rejects stale tokens, foreign node IDs and arbitrary commands',()=>{
  const graph=parse(reply);
  assert.deepEqual(decodeGraphAction({type:'open',nodeId:'n2',token:'token'},'token',graph),{type:'open',nodeId:'n2',token:'token'});
  for(const message of [{type:'execute',nodeId:'n2',token:'token'}, {type:'add',nodeId:'n99',token:'token'},
    {type:'open',nodeId:'n2',token:'old'}, {type:'open',nodeId:'n2',token:'token',uri:'file:///outside.c'}]){
    assert.throws(()=>decodeGraphAction(message,'token',graph));
  }
});
