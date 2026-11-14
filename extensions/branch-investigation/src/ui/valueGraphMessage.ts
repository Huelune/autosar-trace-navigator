import { ValueGraphResult } from '../adapters/traceAnalysisPort';
import { requireValue } from '../domain/validation';

export interface GraphAction {type:'open'|'add';nodeId:string;token:string}
export function decodeGraphAction(value:unknown,token:string,graph:ValueGraphResult):GraphAction{
  requireValue(value&&typeof value==='object'&&!Array.isArray(value),'잘못된 미리보기 요청입니다.');
  const m=value as GraphAction;
  requireValue(Object.keys(m).sort().join(',')==='nodeId,token,type'&&m.token===token&&(m.type==='open'||m.type==='add')&&graph.nodes.some(n=>n.id===m.nodeId),'미리보기 요청이 오래됐거나 허용되지 않습니다.');
  return {type:m.type,nodeId:m.nodeId,token};
}

