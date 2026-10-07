# 설치 및 구성

## 설치 / 업데이트

이 디렉터리는 portable-backend와 visual-QA 사용자 정의를 보존하는 `chrisopal/skills` 버전입니다. 해당 기능이 포함된 검토 완료 fork 커밋의 `image-to-editable-ppt/skills/image-to-editable-ppt/` 경로에서 설치하세요.

`<fork-commit>`은 로컬 사용자 정의가 포함된 검토 완료 커밋 SHA로, `<agent-id>`는 현재 agent 식별자(예: `codex`)로, `<skill-root>`는 실제 설치 경로로 바꾸세요. 기본 브랜치에 해당 변경이 있다고 가정하거나 upstream 배포 ZIP으로 덮어쓰지 마세요.

```bash
npx -y skills@latest add "https://github.com/chrisopal/skills/tree/<fork-commit>/image-to-editable-ppt/skills/image-to-editable-ppt" \
  --skill image-to-editable-ppt \
  --agent <agent-id> \
  --global
pipx install --force --editable <skill-root>/cli
editppt doctor
editppt page visual-qa --help
editppt image extract-source --help
editppt run backend --help
```

업데이트 후 skill 컨텍스트를 다시 로드하세요. `run backend --help`에 `agent-image-tool`이 있고 visual-QA 및 추출 명령이 사용 가능한지 확인하세요. API 자격 증명과 OCR Token은 패키지 밖의 `~/.editppt/config.yaml`에 유지됩니다. CLI 기본 모델은 이제 `gpt-image-2.5-sunburst`이며 업데이트해도 명시적으로 설정한 모델은 덮어쓰지 않습니다.

모델 기본값은 `editppt image` CLI에 적용됩니다. 저장된 이전 모델 설정은 `editppt config --model gpt-image-2.5-sunburst`로 변경할 수 있습니다. 개별 요청에서는 `--model gpt-image-2.5-flare`, 지원되는 날짜별 스냅샷 또는 `openai/gpt-image-2.5-sunburst` 같은 공급자 네임스페이스를 선택할 수 있습니다. 명시적 `--model`이 환경 변수보다 우선하고 환경 변수는 설정 파일보다 우선합니다. `gpt-image-2`를 명시적으로 선택하는 방식도 계속 지원합니다. `--quality` 기본값은 `auto`이며 새 값인 `xhigh`와 `max`는 2.5 Sunburst/Flare에만 사용할 수 있습니다. 원생 이미지 도구는 자체 제공 모델을 사용하며 Codex 내장 도구에는 `model`을 전달하지 않습니다. 선택한 모델의 실제 가용성은 계정과 공급자에 따라 달라집니다.

## 로컬 checkout에서 설치

원하는 fork 커밋을 체크아웃하고 검증했다면 로컬 skill 디렉터리에서도 설치할 수 있습니다. 이후 위의 CLI 갱신 및 확인 단계를 실행하세요.

```bash
npx -y skills@latest add /path/to/chrisopal-skills/image-to-editable-ppt/skills/image-to-editable-ppt \
  --skill image-to-editable-ppt --agent <agent-id> --global
```

## 실행 권한 권장 사항

**Codex에서 이 skill을 실행할 때는 “전체 액세스 권한” 사용을 권장합니다.**

이 skill은 실행 시간이 길며 OCR, 이미지 생성/편집, 파일 읽기·쓰기, 하위 agent 분배, 장시간 폴링 등의 단계를 자동으로 수행합니다. “승인 요청” 모드는 실행을 자주 중단해 일부 단계를 막을 수 있으며, 특히 하위 agent 환경에서 문제가 될 수 있습니다. “대신 승인” 모드도 OCR이나 이미지 생성/편집 또는 타사 API 호출 단계에서 요청을 차단하고 수동 승인을 요구할 수 있습니다. 사용자가 컴퓨터 앞에 없으면 변환 흐름이 멈출 수 있습니다.

![Codex 전체 액세스 권한 설정 예시](https://raw.githubusercontent.com/ningzimu/image-to-editable-ppt-skill/main/assets/codex-full-access-permission.png)

## 실행 요구 사항

- 단일 페이지/이미지 입력은 page worker를 만들 필요가 없으며 메인 agent가 동일한 페이지 재구성 흐름을 로컬에서 수행합니다.
- 다중 페이지 입력은 agent가 page worker/subagent를 분배할 수 있어야 합니다. 현재 환경에서 page worker를 만들 수 없다면 지원되는 환경에서 실행해야 합니다.
- 이 skill이 의존하는 `editppt` 명령줄 도구는 AI가 skill 실행 과정에서 자동으로 설치하므로 사용자가 명령을 직접 실행할 필요가 없습니다.
- 모델의 기본 이해 능력과 skill 준수 능력에 따라 gpt-5.5 미만 모델의 사용 결과는 보장하지 않습니다.

## OCR Token(권장 구성)

이 skill은 타사 OCR 서비스(바이두 PaddleOCR-VL)로 텍스트 상자 좌표, 글자 크기, 크기 그룹을 보정해 텍스트 복원 품질을 크게 높입니다. 원리는 [설계 철학](/ko/design.md)을 참고하세요.

**사용자가 할 일은 Token 신청 하나뿐입니다.** 바이두 AI Studio에서 Access Token을 신청하세요: <https://aistudio.baidu.com/account/accessToken>. 개인 사용의 경우 현재 무료 할당량으로 충분하며 추가 비용이 없습니다.

최초 사용 시 Token이 설정되어 있지 않으면 AI가 한 번 요청합니다. Token을 전달하면 AI가 사용자 수준 설정 `~/.editppt/config.yaml`에 민감한 값을 가려 저장하며, 한 번 구성하면 계속 적용되어 다시 묻지 않습니다.

Token 없이도 실행할 수 있습니다. 이 경우 skill은 내장 오프라인 감지기(텍스트 위치와 크기를 알지만 내용을 인식하지 않는 순수 기하 측정)로 폴백하므로 텍스트 복원 품질이 낮아질 수 있습니다.

## 이미지 Backend 및 타사 API 구성

이미지 생성과 편집은 기본적으로 Codex 내장 `image_gen.imagegen`을 우선 사용합니다. WorkBuddy, Claude Code, QoderWork 또는 다른 agent에서는 Tool, Skill, Plugin, MCP/Connector와 구성된 이미지 모델을 탐색합니다. 후보는 프롬프트 이미지 생성, 참조 이미지 편집, 명시적 로컬 출력을 모두 지원해야 하며, 그렇지 않으면 기본 모델 `gpt-image-2.5-sunburst`의 `editppt image` CLI를 사용합니다. CLI는 로컬 Codex OAuth(`~/.codex/auth.json`)를 우선 사용한 뒤 OpenAI-compatible API 설정을 읽습니다.

WorkBuddy ImageGen과 QoderWork `/gen-image`/remix는 설치된 환경에서 참조 편집 계약을 다시 확인해야 합니다. Claude Code 공식 문서는 이미지 이해만 확인하므로 별도 이미지 Skill/Plugin/MCP 도구가 없으면 CLI 폴백을 사용합니다. 이미지를 보기만 하는 시각 모델은 이미지 backend가 아닙니다.

일반적으로 직접 구성할 필요는 없습니다. 다음 경우에만 AI에게 API 폴백 구성을 요청하세요.

- 타사 API 또는 OpenAI 호환 중계 서비스를 사용하도록 명시적으로 요청한 경우
- WorkBuddy, Claude Code, QoderWork 등의 환경에서 기능 검증을 통과한 원생 이미지 도구도 없고 Codex OAuth auth도 사용할 수 없는 경우
- `editppt image`가 Codex OAuth와 `OPENAI_API_KEY`를 모두 사용할 수 없다고 보고한 경우

타사 API 폴백이 필요하면 사용할 서비스, base URL, 모델명, API key를 AI에게 알려 주세요. AI가 실행 중 환경 확인과 설정 기록을 완료하고, 자격 증명을 사용자 수준 설정 `~/.editppt/config.yaml`에 저장하며 출력에서는 민감한 값을 가립니다. API key를 프로젝트 디렉터리, run 디렉터리 또는 skill 디렉터리에 기록하지 마세요.

Codex OAuth 경로는 로컬 Codex auth와 구독 측 이미지 할당량에 의존하고, API 폴백은 선택한 OpenAI-compatible 서비스의 이미지 생성/편집 기능에 의존합니다. 다중 페이지 변환에서는 page worker도 같은 원생 이미지 도구에 접근할 수 있어야 하며, 그렇지 않으면 전체 실행에서 CLI를 사용합니다.
