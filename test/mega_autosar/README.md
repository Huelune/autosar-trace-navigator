# 5,125파일 독립 가상 AUTOSAR 프로젝트

직접 작성한 합성 코드다. 기존 실행 샘플·파서 오류 사례와 섞지 않는다.
AUTOSAR Classic 스타일 SWC와 RTE 메모리를 흉내 내며 실제 스택·ARXML·고객 코드는 포함하지 않는다.

## 구성과 생성

저장소 루트에서 **새 출력 폴더**를 지정한다. 기존 폴더가 있으면 실패하고 원본을 덮어쓰지 않는다.

```powershell
python test/mega_autosar/generate.py build/mega-autosar-5125
```

| 구성 | C | H | 역할 |
|---|---:|---:|---|
| `components/Mega_000` ~ `Mega_063` | 2560 | 2560 | SWC마다 40개 함수 파일·헤더 쌍, 독립 입력/채널/Publisher |
| `include/` | 0 | 2 | 가상 타입·구조체와 Rte_Read/Write 선언 |
| `app/Mega_Goal.c` | 1 | 0 | `pedal >= 60u` 목표 분기 |
| `support/Rte_Memory.c` | 1 | 0 | 채널별 static 버퍼와 RTE 출력 인수 구현, extern 전역 입력 |
| `runtime/Scenarios.c` | 1 | 0 | 생산자·소비자 실행 순서 및 경계값 9시나리오 |
| **합계** | **2563** | **2562** | **C/H 5125개**, 함수 정의 2755개 |

기본 데이터의 소스 합계는 1,020,524바이트다. 파일 수/범위 탐색을 재현하는 샘플이며,
실제 대형 프로젝트의 소스 크기·매크로 밀도·메모리 사용량을 대표하지 않는다.
`manifest.json`에 실제 개수·크기·목표·권장 범위를 저장한다.
생성된 C/H는 `build/`에 두고 Git에는 생성기·테스트·사용법만 공유한다.
다른 PC에서도 위 명령으로 같은 내용의 프로젝트를 만들 수 있다.

## 조사할 예시

`app/Mega_Goal.c`에서 `else if (pedal >= 60u)`를 목표로 고른다.

```text
Mega_Goal
  -> Mega_000_Stage_00 -> ... -> Mega_000_Stage_39  (40개 함수 진입)
  -> Rte_Read_Mega000_Pedal(&pedal)                (출력 인수)

별도 Runnable: Mega_000_Publish
  -> Rte_Write_Mega000_Pedal(converted)            (이름 기반 데이터 관계)
  -> converted = g_Stimulus_000.raw * 2u  또는 raw + 10u
```

Publisher는 `components/Mega_000/Stage_39.c`에 있다. 소비자가 Publisher를 직접 호출하지 않는다.
`g_Stimulus_000`은 `support/Rte_Memory.c`에 정의되고 RTE 헤더에 extern으로 선언된 구조체다.
static `buffer_000`은 CT 직접 입력 후보와 구분한다.

| 경로 | 필요한 입력·조건 | 값 흐름 |
|---|---|---|
| 첫 계산 분기 | enabled != 0, quality == 1, raw == 30 | 30 × 2 → 60 → 목표 분기 |
| 다른 계산 분기 | enabled != 0, quality == 2, raw == 50 | 50 + 10 → 60 → 목표 분기 |
| 비활성 | enabled == 0 | 쓰기를 생략하고 이전 RTE 메모리 유지 |
| 읽기 실패 | g_ReadFailure_000 != 0 | Read는 출력 인수를 쓰지 않고 소비자는 0 반환 |

중간 Stage는 100을 넘는 값을 100으로 제한한다. 목표값 60 리터럴은 Publisher 계산식에 없다.
위 숫자는 가상 하네스에서 확인한 예시이며 실제 CT에서 조정 가능하다는 보장은 아니다.
RTE 이름 일치만으로 wiring·초기값·실행 순서를 확정하지 않는다. 하네스가 Publisher 선행을 직접 지정한다.

## VS Code에서 열기

1. **생성된 `build/mega-autosar-5125` 폴더 자체**를 VS Code로 연다.
2. 최신 확장을 설치하고 사용자 설정 `branchInvestigation.pythonPath`에 엔진이 설치된 Python을 지정한다.
3. 아래 설정을 해당 생성 프로젝트에 적용한 뒤 목표 분기나 변수 위에서 관련 후보/함수 검색을 실행한다.

```json
{
  "branchInvestigation.analysisPaths": ["."],
  "branchInvestigation.analysisMaxFiles": 6000,
  "branchInvestigation.analysisTimeoutSeconds": 120
}
```

기본 한도 500은 5125/500 초과로 중단한다. 6000은 무제한 분석이 아닌 명시적인 유한 한도다.
전체 범위에는 하네스의 RTE Write도 들어가므로 `check`·`main`이 추가 Writer 후보로 보일 수 있다.
`analysisExcludePaths: ["runtime"]`이면 5124개 C/H이며 하네스 후보가 제외된다.

활성 SWC만 조사할 때는 다음처럼 범위를 좁히면 **84개 C/H**여서 기본 한도 500에서도 동작한다.

```json
{
  "branchInvestigation.analysisPaths": ["app", "include", "components/Mega_000", "support"],
  "branchInvestigation.analysisMaxFiles": 500
}
```

이 범위는 다른 SWC의 Stage 함수를 포함하지 않는다. 그 함수를 찾지 못해도 프로젝트 전체에 없다는 뜻은 아니다.
한도 증가는 속도 개선을 보장하지 않는다. 이전 조사 JSON이 있으면 원래 프로젝트 폴더에서 유지한다.

## 자동 검증

```powershell
.venv\Scripts\python -m unittest discover -s tests -p test_mega_autosar.py -v
```

임시 폴더에 5125파일을 생성해 전체 구문 분석, 기본 한도에서 파싱 전 중단, 40단계 호출과 별도 RTE Writer,
84파일 범위 축소, 결정적 생성·덮어쓰기 거부, C/H 바이트·수정 시각 무변경을 검증한다.
전처리 미평가·호출 대상 미확정 진단은 정상적으로 유지하고 C 문법 오류만 실패로 판단한다.

C 실행 검증은 **활성 SWC 40개 C + 목표 + RTE 메모리 + 하네스 = 43개 번역 단위**를
기존 C99 검증 도구로 컴파일해 9시나리오를 실행한다. 전체 2563개 C를 한 번에 링크한 결과가 아니다.
경계값 아래/동일, 두 계산 경로, 잘못된 품질, 상한 제한, 비활성 시 이전 메모리, 읽기 실패,
Publisher보다 소비자를 먼저 실행하는 경우를 확인한다. 고객 프로젝트·수동 GUI·실제 CT는 검증하지 않는다.

생성기의 `--components 1 --stages 2`는 소형 회귀 데이터용이며 기본 5125파일 예시와 구분한다.


2026-11-14 Windows/Python 3.14.3의 실제 브리지 검증에서 전체 함수 2755개가 잘림 없이 반환됐고,
선택 범위의 RTE Read에서 Mega_000_Publish 후보를 확인했다. 단일 관측 시간은 전체 함수 목록 54.526초,
선택 범위 RTE 후보 0.490초였다. C 실행 검사와 일부 겹친 수치이며 성능 보장이나 정식 벤치마크가 아니다.
실행 명령·범위와 미검증 사항은 [SCALE-002 세션](../../docs/work/sessions/20261114T060344Z-codex-97e76cabf0e04c6eb379b2cd57536351.md)에 기록했다.
