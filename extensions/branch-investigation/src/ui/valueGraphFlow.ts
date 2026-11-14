import type {OriginNode,ValueGraphResult} from '../adapters/traceAnalysisPort';

export interface OriginFlowState {route:string[];focus:number;mode:'flow'|'all';query:string;page:number;returnRoute?:string[]}

/** Pure presentation model. Self-contained so the same code runs in Node tests and the Webview. */
export function createOriginFlow(graph:ValueGraphResult){
  const terminalName=(n:OriginNode)=>({none:'계속 조사',ct_input:'전역 입력 후보',constant:'상수 후보',unresolved:'미해결',review:'계산 검토',cycle:'순환 참조',limit:'탐색 한도'}[n.terminal]);
  const role=(n:OriginNode)=>n.uncertainty.includes('name_only_caller_candidate')?'호출부 인수':n.kind==='probe'?(n.expression==='$return'?'반환값':'변수'):({condition:'필요 조건',return_value:'함수 반환',expression:'계산식',expression_operand:'계산 입력',rte_data:'RTE 공급 후보',ct_global_input:'전역 입력 후보',constant:'상수',object_origin:'객체 출처',parameter_input:'호출부 인수',initializer:'초기값',assignment:'대입',return:'반환 식',possible_output_argument:'출력 인수 검토',unresolved_call:'미해결 호출',input_boundary:'입력 경계',member_write:'멤버 쓰기',member_initializer:'멤버 초기값',output_parameter:'출력 인수'} as Record<string,string>)[n.kind]??'출처 후보';
  const siteName=(n:OriginNode)=>n.siteFunctionName===null?'전역 선언':n.siteFunctionName??n.functionName;
  const nodes=new Map(graph.nodes.map(n=>[n.id,n]));
  const outgoing=new Map<string,typeof graph.edges>();
  for(const edge of graph.edges){outgoing.set(edge.from,[...(outgoing.get(edge.from)??[]),edge]);}
  // Conditions describe a chosen value route; they are not alternative suppliers of its value.
  const next=(id:string)=> (outgoing.get(id)??[]).filter(e=>e.relation!=='condition'||nodes.get(id)?.kind==='condition');
  const walk=(start:string,blocked:Set<string>,all=false)=>{
    const previous=new Map<string,string|null>([[start,null]]),queue=[start];
    for(let i=0;i<queue.length;i++){
      for(const edge of all?outgoing.get(queue[i])??[]:next(queue[i])){
        if(!blocked.has(edge.to)&&!previous.has(edge.to)){previous.set(edge.to,queue[i]);queue.push(edge.to);}
      }
    }
    return previous;
  };
  const path=(previous:Map<string,string|null>,target:string):string[]=>{
    if(!previous.has(target)){return [];}
    const ids:string[]=[];for(let id:string|null=target;id!==null;id=previous.get(id)??null){ids.push(id);}
    return ids.reverse();
  };
  const reachable=walk(graph.rootId,new Set());
  const rank=(node:OriginNode)=>['ct_input','unresolved','limit','cycle','review','constant','none'].indexOf(node.terminal);
  const endpoints=graph.nodes.filter(n=>reachable.has(n.id)&&n.terminal!=='none').sort((a,b)=>rank(a)-rank(b));
  function finish(prefix:string[]):string[]{
    const start=prefix.at(-1)!;
    if(new Set(prefix).size!==prefix.length){return prefix;}
    const previous=walk(start,new Set(prefix.slice(0,-1)));
    const candidates=graph.nodes.filter(n=>previous.has(n.id)&&n.terminal!=='none').sort((a,b)=>rank(a)-rank(b));
    const target=candidates[0]?.id;
    return target?[...prefix.slice(0,-1),...path(previous,target)]:prefix;
  }
  function validRoute(route:unknown):route is string[]{
    if(!Array.isArray(route)||!route.length||route.length>graph.nodes.length+1||route[0]!==graph.rootId){return false;}
    const seen=new Set<string>();
    return route.every((id,i)=>{
      if(typeof id!=='string'||!nodes.has(id)||seen.has(id)&&i!==route.length-1){return false;}
      seen.add(id);return i===0||(outgoing.get(route[i-1])??[]).some(e=>e.to===id);
    });
  }
  function routeTo(id:string):string[]{
    if(!nodes.has(id)){return [];}
    return path(reachable,id).length?path(reachable,id):path(walk(graph.rootId,new Set(),true),id);
  }
  function conditions(route:string[]){
    const found=new Map<string,{node:OriginNode;at:number}>();
    route.forEach((id,at)=>{for(const edge of outgoing.get(id)??[]){const node=nodes.get(edge.to)!;if(edge.relation==='condition'&&node.kind==='condition'){found.set(node.id,{node,at});}}});
    return [...found.values()];
  }
  function groups(route:string[]){
    const result:{functionName:string;indices:number[];primary:number}[]=[];
    route.forEach((id,index)=>{
      const node=nodes.get(id)!;let group=result.at(-1);
      if(!group||group.functionName!==siteName(node)){group={functionName:siteName(node),indices:[],primary:index};result.push(group);}
      group.indices.push(index);if(node.kind!=='probe'){group.primary=index;}
    });
    return result;
  }
  function initial():OriginFlowState{return {route:finish([graph.rootId]),focus:0,mode:'flow',query:'',page:0};}
  function restore(value:unknown):OriginFlowState{
    const s=value as OriginFlowState;
    if(!s||!validRoute(s.route)||!Number.isInteger(s.focus)||s.focus<0||s.focus>=s.route.length||(s.mode!=='flow'&&s.mode!=='all')){return initial();}
    return {route:[...s.route],focus:s.focus,mode:s.mode,query:typeof s.query==='string'?s.query.slice(0,200):'',page:Number.isInteger(s.page)&&s.page>=0?s.page:0,
      ...(validRoute(s.returnRoute)?{returnRoute:[...s.returnRoute]}:{})};
  }
  function navigate(current:OriginFlowState,action:string,id?:string,index?:number):OriginFlowState{
    const s=restore(current);
    if(action==='focus'&&Number.isInteger(index)&&index!>=0&&index!<s.route.length){s.focus=index!;}
    if(action==='branch'&&id&&Number.isInteger(index)&&index!>=0&&index!<s.route.length&&next(s.route[index!]).some(e=>e.to===id)){
      // Preserve the selected caller prefix, even if another route reaches the same input more directly.
      s.route=finish([...s.route.slice(0,index!+1),id]);s.focus=index!+1;s.mode='flow';
    }
    if((action==='target'||action==='inspect')&&id){const route=routeTo(id);if(route.length){s.route=route;s.focus=route.length-1;s.mode='flow';delete s.returnRoute;}}
    if(action==='condition'&&id){
      const selected=conditions(s.route).find(c=>c.node.id===id);
      if(selected){if(!s.returnRoute){s.returnRoute=[...s.route];}s.route=finish([...s.route.slice(0,selected.at+1),id]);s.focus=selected.at+1;s.mode='flow';}
    }
    if(action==='return'&&s.returnRoute){s.route=s.returnRoute;s.focus=0;delete s.returnRoute;}
    if(action==='home'){return initial();}
    if(action==='page'&&Number.isInteger(index)&&index!>=0){s.page=index!;}
    if(action==='all'){s.mode=s.mode==='all'?'flow':'all';}
    return s;
  }
  const search=(query:string)=>{const q=query.trim().toLowerCase();return graph.nodes.filter(n=>`${n.expression} ${n.functionName} ${siteName(n)} ${n.location.path} ${n.kind} ${terminalName(n)} ${role(n)} ${n.terminal} ${n.location.text??''} ${n.context?.text??''}`.toLowerCase().includes(q));};
  const isConditionRoute=(route:string[])=>route.some((id,i)=>i>0&&(outgoing.get(route[i-1])??[]).some(e=>e.to===id&&e.relation==='condition'));
  return {siteName,isConditionRoute,nodes,next,endpoints,finish,validRoute,routeTo,conditions,groups,initial,restore,navigate,search,role,terminalName};
}
