# 직접 실행할 것

Claude가 실행할 수 없는 환경(다른 PC 등)에서 돌릴 것을 적는다. **결과를 붙여 주면 해당 절은 지운다.**
화면에는 단계별 성공/실패와 할 일만 나오고 경로·오류 원문은 나오지 않는다.

## 1. 다른 PC에 확장과 분석 엔진 설치

**왜**: 다른 PC에서 Branch Investigation 확장과 관련 후보 조회(값·조건·호출·RTE)를 직접 써 보기 위해서다.

**필요한 것**: Git, VS Code 1.95 이상(`code` 명령), Python 3.11~3.14, 그리고 설치 때 한 번의 인터넷 연결(GitHub, PyPI).
PowerShell과 Node/npm은 필요 없다. 회사 PC라면 VSIX 설치와 Python 실행이 허용되는지 먼저 확인한다.

**실행**: 명령 프롬프트(cmd) 창에 아래 네 줄을 붙여 넣고 Enter를 누른다.
사용자 홈 폴더 아래 `autosar-trace-navigator`에 `main` 기준으로 설치한다. 다시 붙여 넣으면 최신 커밋으로 갱신하고 다시 설치한다
(이때 첫 줄은 "이미 있다"는 오류를 내지만 정상이며, 결과 화면은 마지막에 새로 그려진다).
예전에 기능 브랜치로 설치한 폴더도 둘째 줄이 `main`으로 바꾼다.

```bat
git clone https://github.com/Huelune/autosar-trace-navigator.git "%USERPROFILE%\autosar-trace-navigator"
git -C "%USERPROFILE%\autosar-trace-navigator" switch main
git -C "%USERPROFILE%\autosar-trace-navigator" pull --ff-only
python "%USERPROFILE%\autosar-trace-navigator\scripts\install.py"
```

설치가 끝나면 메모장에 설정 두 줄이 열린다. 화면 안내대로 VS Code 사용자 설정(JSON)에 붙여 넣는다.
메모장에는 설치 경로가 들어 있으므로 **메모장 창은 캡처하지 않는다.**

**확인할 것**

- 여섯 단계가 모두 `완료`인지.
- 설정 후 설치 폴더의 `test\struct_paths`를 열고, `consumer.c`의 `a = b.a;` 줄에서 `b.a`에 커서를 두고
  우클릭 **관련 후보 조회 (값·조건·호출·RTE)**를 실행했을 때 후보 목록이 뜨는지.
- 후보를 고르고 이유를 입력하면 왼쪽 **Branch Investigation** 트리에 단계가 생기는지.

**돌려줄 것**

- cmd 결과 화면 캡처 한 장(단계별 완료/실패만 나온다).
- 후보 목록이 떴는지, 단계가 저장됐는지 예/아니오.
- 써 보면서 이상했던 동작이나 불편했던 점. 실제 업무 코드로 써 봤다면 코드·이름·경로 없이 말로만 적는다.
