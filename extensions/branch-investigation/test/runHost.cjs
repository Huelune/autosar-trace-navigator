const fs = require('node:fs/promises');
const path = require('node:path');
const { runTests } = require('@vscode/test-electron');
const { spawn } = require('node:child_process');
const { Writable } = require('node:stream');
(async () => {
  const extension = path.resolve(__dirname, '..'), repo = path.resolve(extension, '../..');
  const base = await fs.mkdtemp(path.join(repo, 'build', 'branch-host-'));
  const workspace = path.join(base, 'workspace'); await fs.mkdir(workspace);
  for (const name of ['consumer.c', 'producer.c', 'struct_paths.h', 'Rte_StructPaths.h']) {
    await fs.copyFile(path.join(repo, 'test/struct_paths', name), path.join(workspace, name));
  }
  await fs.writeFile(path.join(workspace, 'unicode.c'), 'int Demo(int a) {\r\n  /*한글 😀*/ if (a < 60) return 0;\r\n  else return 1;\r\n}\r\n');
  await fs.mkdir(path.join(workspace, '.vscode'));
  await fs.writeFile(path.join(workspace, '.vscode/settings.json'), JSON.stringify({'telemetry.telemetryLevel':'off','update.mode':'none','extensions.autoUpdate':false,'extensions.autoCheckUpdates':false,'workbench.startupEditor':'none','security.workspace.trust.startupPrompt':'never'}));
  const executable = process.env.VSCODE_EXECUTABLE_PATH || path.join(process.env.LOCALAPPDATA || '', 'Programs/Microsoft VS Code/Code.exe');
  console.log('Host fixture:', base);
  const logHandle = await fs.open(path.join(base,'host.log'),'w');
  const log = new Writable({write(chunk, _encoding, callback){logHandle.write(chunk).then(()=>{for(const line of chunk.toString().split(/\r?\n/)){if(line.startsWith('PASS ')||line.startsWith('AssertionError')){console.log(line);}}callback();},callback);}});
  for (const phase of ['record', 'restart', 'untrusted']) {
    const userData = path.join(base, 'profile-' + phase), extensionsDir = path.join(base, 'extensions');
    const args = [workspace,'--new-window','--skip-welcome','--skip-release-notes','--disable-extensions','--user-data-dir',userData,'--extensions-dir',extensionsDir];
    if (phase !== 'untrusted') { args.push('--disable-workspace-trust'); }
    const testsPath=path.join(extension,'dist/test/host/index.js'), testEnv={...process.env,BRANCH_HOST_PHASE:phase,BRANCH_HOST_BASE:base};
    if(phase==='untrusted') {
      // test-electron 3.x always appends --disable-workspace-trust; use the real CLI without that flag.
      await fs.mkdir(path.join(userData,'User'),{recursive:true});
      await fs.writeFile(path.join(userData,'User/settings.json'),JSON.stringify({'security.workspace.trust.enabled':true,'security.workspace.trust.startupPrompt':'never','telemetry.telemetryLevel':'off','update.mode':'none'}));
      await new Promise((resolve,reject)=>{const child=spawn(executable,[...args,'--extensionDevelopmentPath='+extension,'--extensionTestsPath='+testsPath],{env:testEnv});child.stdout.on('data',b=>log.write(b));child.stderr.on('data',b=>log.write(b));child.on('error',reject);child.on('exit',code=>code===0?resolve():reject(Error('Untrusted Host exit '+code)));});
    } else {
      await runTests({vscodeExecutablePath:executable,extensionDevelopmentPath:extension,extensionTestsPath:testsPath,launchArgs:args,extensionTestsEnv:testEnv,stdout:log,stderr:log});
    }
  }
  await new Promise(resolve=>log.end(resolve));await logHandle.close();
  console.log('PASS Extension Host record / restart / untrusted');
})().catch(e => { console.error(e); process.exitCode = 1; });
