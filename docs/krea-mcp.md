# Krea MCP 서버 설정

Krea의 이미지·영상 생성 모델(Flux, Ideogram, Imagen, Runway, Hailuo, Kling 등)을
Claude Code에서 직접 호출하기 위한 MCP 서버 설정이다. 설정은 저장소의
`.mcp.json`(프로젝트 스코프)에 들어 있다.

## 구성

```json
{
  "mcpServers": {
    "krea": {
      "command": "npx",
      "args": ["-y", "@vmosaic/krea-mcp-server"],
      "env": { "KREA_API_KEY": "${KREA_API_KEY}" }
    }
  }
}
```

- 패키지: `@vmosaic/krea-mcp-server` (npm)
- API 키는 `${KREA_API_KEY}` 환경변수로 주입한다. **키 자체는 저장소에 커밋하지 않는다.**

## 주의 (반드시 확인)

- **서드파티 서버다.** Krea 공식이 아닌 커뮤니티 패키지(메인테이너 `keugenek`,
  Apache-2.0)이며 API 키를 받아 외부로 요청을 보낸다. 신뢰 범위를 확인하고 사용한다.
- **네트워크 정책**이 npm 레지스트리와 Krea API 도메인 접근을 허용해야 한다.
  Claude Code on the web의 제한적 네트워크 환경에서는 차단될 수 있다.
- MCP 서버는 **세션 시작 시 로드**된다. 설정 후 현재 진행 중인 세션에는 즉시
  반영되지 않으며, 새 세션에서 활성화된다.

## 활성화 절차

1. **API 키 발급**: https://krea.ai 에서 API 키를 발급받는다.
2. **키 주입(비밀)**: 채팅에 붙여넣지 말고 환경 변수로 설정한다.
   - 로컬: `export KREA_API_KEY=...` 후 Claude Code 실행.
   - Claude Code on the web: 환경(Environment) 설정의 시크릿/환경변수로 등록.
3. **승인**: 프로젝트 MCP 서버는 처음 사용 시 승인이 필요하다.
   `claude` 실행 후 프롬프트에서 `krea` 서버를 승인한다.
   (`claude mcp list`로 상태 확인 가능 — 키가 없으면 경고가 표시된다.)
4. **확인**: 새 세션에서 `mcp__krea__*` 도구가 노출되면 정상이다.

## 대안 (사용자 스코프 설치)

저장소에 `.mcp.json`을 두지 않고 로컬 사용자 설정에만 추가하려면:

```bash
claude mcp add krea -e KREA_API_KEY=your-api-key -- npx -y @vmosaic/krea-mcp-server
```

## 참고

- npm: https://www.npmjs.com/package/@vmosaic/krea-mcp-server
- GitHub: https://github.com/keugenek/krea-mcp
- MCP 문서: https://code.claude.com/docs/en/mcp
