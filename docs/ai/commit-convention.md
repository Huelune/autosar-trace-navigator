# 커밋 규칙

사용자가 지정한 [참고 저장소 규칙](https://github.com/Huelune/Simulink-Test-Automation-Toolkit/blob/main/docs/ai/commit-convention.md)을 이 프로젝트에 적용한다.

- 하나의 커밋은 하나의 논리적인 변경만 포함한다. 독립적으로 되돌릴 변경은 분리한다.
- Conventional Commits: `<type>: <summary>` 또는 필요한 경우 `<type>(<scope>): <summary>`.
- type: feat, fix, refactor, test, docs, chore, perf, style, revert.
- 제목은 무엇을 왜 바꾸었는지 드러내며, scope는 이해에 도움이 될 때만 사용한다.
- 관련 없는 리팩터링·수정·문서를 섞지 않는다. 기능과 필수 테스트·문서는 함께 둘 수 있다.
- CHANGELOG 항목은 해당 변경 커밋에 포함한다. 커밋 수를 억지로 늘리지 않는다.
- 필요할 때만 본문으로 이유, 설계 결정, 영향 범위를 설명한다.
- 호환성을 깨면 `!` 또는 `BREAKING CHANGE:`로 명시한다.
- 커밋 전에 diff와 미추적 파일을 검토하고, 목적별 포함 파일을 결정하고 검증한다.
- 여러 커밋이면 먼저 계획을 알린다. 실패·미완성 사항은 커밋 전에 알린다.
- 사용자 요청 없이 이력을 rewrite, squash하거나 force push하지 않는다.
- 이 프로젝트에서는 검증한 작업 범위의 변경을 단계 완료 시 자동 커밋한다.
  관련 없는 사용자 변경은 포함하지 않으며, 푸시는 별도 요청이 있을 때 수행한다.
