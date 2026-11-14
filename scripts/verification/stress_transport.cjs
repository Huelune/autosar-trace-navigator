// Exercise the released analysis adapter without VS Code or UI automation.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {setTimeout: delay} = require('node:timers/promises');
const [python, adapter, project, output] = process.argv.slice(2);
const {PythonTraceAnalysisPort} = require(adapter);
const request = {op:'functions',root:project,includePaths:['.'],limits:{maxFiles:6000}};
const alive = pid => {try{process.kill(pid,0);return true;}catch(e){if(e.code==='ESRCH'){return false;}throw e;}};
const owned=[];

(async()=>{
  const checks=[];let recoveryPort;
  for(const mode of ['timeout','cancelled']){
    const marker=path.join(output,`${mode}-pid.json`);
    const code=`import os,pathlib,runpy;pathlib.Path(${JSON.stringify(marker)}).write_text(str(os.getpid()));runpy.run_module('autosar_trace_navigator.bridge',run_name='__main__')`;
    const abort=new AbortController(),port=new PythonTraceAnalysisPort(python,['-I','-c',code],mode==='timeout'?1000:5000);
    const start=Date.now(),pending=port.functions(request,abort.signal).then(()=>({code:'unexpected_success'}),e=>e);
    let pid;
    for(let i=0;i<80;i++){try{pid=Number(await fs.readFile(marker,'utf8'));if(Number.isSafeInteger(pid)&&pid>0){break;}}catch(e){if(e.code!=='ENOENT'){throw e;}}await delay(25);}
    assert.ok(Number.isSafeInteger(pid)&&pid>0,'real engine worker must start');
    owned.push(pid);if(mode==='cancelled'){recoveryPort=port;}
    if(mode==='cancelled'){await delay(100);abort.abort();}
    const error=await pending;assert.equal(error.code,mode);
    for(let i=0;i<40&&alive(pid);i++){await delay(25);}
    assert.equal(alive(pid),false,'engine child remains after cancellation/timeout');
    checks.push({name:mode,passed:true,seconds:(Date.now()-start)/1000,child_terminated:true});
  }
  // Synthetic output flood isolates the default 8MiB transport guard from parser cost.
  const flood="import sys;sys.stdout.buffer.write(b'x'*(9*1024*1024));sys.stdout.flush()";
  const flooded=await new PythonTraceAnalysisPort(python,['-I','-c',flood],5000).functions(request,new AbortController().signal).then(()=>({code:'unexpected_success'}),e=>e);
  assert.equal(flooded.code,'output_limit');checks.push({name:'default-8MiB-output-limit',passed:true});
  // A failed request must not prevent the same port from handling a normal subsequent one.
  const recovered=await recoveryPort.functions({...request,includePaths:['app','include','components/Mega_000','support']},new AbortController().signal);
  assert.equal(recovered.functions.length,170);assert.equal(recovered.truncated,false);
  checks.push({name:'subsequent-scoped-request',passed:true,functions:170});
  process.stdout.write(JSON.stringify(checks));
})().catch(e=>{for(const pid of owned){if(alive(pid)){process.kill(pid);}}console.error(e.code||e.message);process.exitCode=1;});
