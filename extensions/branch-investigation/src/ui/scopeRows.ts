import { ScopeResult } from '../adapters/traceAnalysisPort';

/** Rows of the scope check: the three budgets first, then the largest folders, then the way to the settings. */
export function scopeRows(r:ScopeResult,excluded:readonly string[]):{label:string;description:string;settings?:boolean}[]{
  const mib=(bytes:number)=>`${(bytes/1048576).toFixed(1)} MiB`,n=(v:number)=>v.toLocaleString('ko-KR'),mark=(metric:ScopeResult['over'][number])=>r.over.includes(metric)?['$(error)','한도 초과']:['$(check)','한도 안'];
  const budget=(metric:ScopeResult['over'][number],text:string)=>({label:`${mark(metric)[0]} ${text}`,description:mark(metric)[1]});
  return [budget('files',`C/H 파일 수: ${n(r.files)}개 / 한도 ${n(r.limits.maxFiles)}개`),budget('source_bytes',`소스 합계: ${mib(r.sourceBytes)} / 한도 ${mib(r.limits.maxSourceBytes)}`),
    budget('file_bytes',`가장 큰 파일: ${mib(r.largestFileBytes)} / 한도 ${mib(r.limits.maxFileBytes)}${r.filesOverFileLimit?` (한도를 넘는 파일 ${n(r.filesOverFileLimit)}개)`:''}`),
    ...r.folders.map(f=>({label:`$(folder) ${f.path==='.'?'(작업 폴더 바로 아래)':f.path}`,description:`파일 ${n(f.files)}개 · ${mib(f.bytes)} · 파일 수의 ${r.files?Math.round(f.files*100/r.files):0}%`})),
    ...(r.foldersTruncated?[{label:'$(ellipsis) 크기순 상위 20개 폴더만 표시했습니다.',description:''}]:[]),
    {label:`$(circle-slash) 제외 경로 설정: ${excluded.length?`${n(excluded.length)}개 적용됨`:'없음'}`,description:'제외한 폴더는 위 숫자에 들어 있지 않습니다.'},
    {label:'$(gear) 분석 설정 열기 (범위·제외 경로·한도)',description:'',settings:true}];
}
