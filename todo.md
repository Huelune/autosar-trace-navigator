# 직접 실행할 것

Claude가 실행할 수 없는 환경(다른 PC 등)에서 돌릴 것을 적는다. **결과를 붙여 주면 해당 절은 지운다.**
화면에는 단계별 성공/실패와 할 일만 나오고 경로·오류 원문은 나오지 않는다.

## 1. 다른 PC에 확장과 분석 엔진 설치

**왜**: 다른 PC에서 Branch Investigation 확장과 관련 후보 조회(값·조건·호출·RTE)를 직접 써 보기 위해서다.

**필요한 것**: Git, VS Code 1.95 이상(`code` 명령), Python 3.11~3.14, 그리고 설치 때 한 번의 인터넷 연결(GitHub, PyPI).
Node/npm은 필요 없다. 회사 PC라면 VSIX 설치와 Python 실행이 허용되는지 먼저 확인한다.

**실행**: PowerShell 창에 아래 블록 전체를 붙여 넣는다. 설치 위치는 첫 줄의 `$dest`에서 바꿀 수 있다.
다시 붙여 넣으면 최신 커밋으로 갱신하고 다시 설치한다.

```powershell
$dest   = Join-Path $HOME 'autosar-trace-navigator'
$branch = 'feat/repo-analysis-aa2e6b'
$url    = 'https://github.com/Huelune/autosar-trace-navigator.git'
$log    = Join-Path $env:TEMP 'atn-install.log'
$py     = Join-Path $dest '.venv\Scripts\python.exe'
$vsix   = Join-Path $dest 'release\branch-investigation-0.1.0.vsix'
$old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
Set-Content -Path $log -Value "install $(Get-Date -Format s)" -Encoding utf8
$rows = @(); $failed = $false
function Step($name, $todo, [scriptblock]$run) {
  if ($script:failed) { $script:rows += "  건너뜀  $name"; return }
  $global:LASTEXITCODE = 0; $ok = $true
  try { & $run *>> $script:log; if ($LASTEXITCODE -ne 0) { $ok = $false } } catch { $ok = $false; "$_" >> $script:log }
  if ($ok) { $script:rows += "  완료    $name" } else { $script:failed = $true; $script:rows += "  실패    $name -> $todo" }
}
Step '도구 확인 (git, python, code)' 'Git, Python 3.11~3.14, VS Code의 code 명령을 설치하고 새 창에서 다시 실행' {
  foreach ($tool in 'git', 'python', 'code') { if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "missing $tool" } }
  python -c "import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 14) else 1)" }
Step '저장소 받기' '인터넷 연결과 설치 위치의 쓰기 권한 확인. 그 위치에 다른 폴더가 있으면 $dest 변경' {
  if (Test-Path (Join-Path $dest '.git')) { git -C $dest fetch origin $branch; if ($LASTEXITCODE -eq 0) { git -C $dest checkout $branch }; if ($LASTEXITCODE -eq 0) { git -C $dest merge --ff-only "origin/$branch" } }
  else { git clone --branch $branch $url $dest } }
Step 'Python 가상환경' 'Python 설치에 venv가 포함됐는지 확인' { python -m venv (Join-Path $dest '.venv') }
Step '분석 엔진 설치' 'PyPI 접속(사내 프록시·미러 설정) 확인' { & $py -m pip install --disable-pip-version-check --quiet $dest }
Step '분석 엔진 동작 확인' '위 단계를 다시 실행' { & $py -I -c "import autosar_trace_navigator.bridge" }
Step 'VS Code 확장 설치' 'VSIX 설치가 정책으로 막혀 있는지 확인' { code --install-extension $vsix --force }
Step '설정 두 줄을 클립보드에 복사' '직접 입력: pythonPath에 설치 위치의 .venv\Scripts\python.exe' {
  Set-Clipboard -Value ('"branchInvestigation.pythonPath": "' + $py.Replace('\', '\\') + '",' + "`r`n" + '"branchInvestigation.analysisPaths": ["."]') }
$ErrorActionPreference = $old
Clear-Host
'Branch Investigation 설치 결과'
$rows
''
if ($failed) { '실패한 단계의 할 일을 처리한 뒤 블록을 다시 붙여 넣으세요.'; '자세한 기록(이 PC에서만 확인): %TEMP%\atn-install.log' }
else {
  '다음 순서로 설정하세요.'
  '  1. VS Code에서 Ctrl+Shift+P -> Preferences: Open User Settings (JSON)'
  '  2. 중괄호 안에서 Ctrl+V (설정 두 줄이 클립보드에 들어 있음). 기존 항목과는 쉼표로 구분'
  '  3. 저장한 뒤 설치 위치의 test\struct_paths 폴더를 열고 폴더를 신뢰'
}
```

**확인할 것**

- 일곱 단계가 모두 `완료`인지.
- 설정 후 `test\struct_paths`의 `consumer.c`에서 `a = b.a;` 줄의 `b.a`에 커서를 두고
  우클릭 **관련 후보 조회 (값·조건·호출·RTE)**를 실행했을 때 후보 목록이 뜨는지.
- 후보를 고르고 이유를 입력하면 왼쪽 **Branch Investigation** 트리에 단계가 생기는지.

**돌려줄 것**

- 결과 화면 캡처 한 장(단계별 완료/실패만 나온다).
- 후보 목록이 떴는지, 단계가 저장됐는지 예/아니오.
- 써 보면서 이상했던 동작이나 불편했던 점. 실제 업무 코드로 써 봤다면 코드·이름·경로 없이 말로만 적는다.
