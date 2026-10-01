# Netlify 배포 준비

구성: 브라우저 → Netlify 정적 화면 → 동일 출처 `/api/*` 프록시 → HTTPS Python 서버 → 영속 SQLite/첨부파일 DB.

Netlify는 현재 Python HTTP 서버와 SQLite 영속 볼륨을 실행하지 않습니다. 별도 서버가 필요합니다. Netlify만 연결하고 운영 가능하다고 판단하지 않습니다.

## Python 서버

1. Dockerfile로 서버를 구축하고 `/data`에 영속 볼륨을 연결합니다. HTTPS 역방향 프록시를 구성합니다. compose의 로컬 포트는 프록시 뒤에서 사용합니다.
2. `SONG_GUARD_DB=/data/songguard.sqlite3`, `SONG_GUARD_SECURE_COOKIE=true`, `SONG_GUARD_ALLOW_REGISTRATION=false`를 유지합니다.
3. `SONG_GUARD_PUBLIC_ORIGIN=https://실제-Netlify-또는-사용자도메인`을 서버 환경변수로 지정하고 서버를 재시작합니다. 경로나 끝 슬래시 없이 사이트 출처만 입력합니다. 임의 출처·미리보기 출처는 자동 허용하지 않습니다.
4. 운영 서버에서 `python manage.py create-user song --allow-short-password`를 실행하고 지정한 비밀번호를 비공개 입력합니다. 기존 개발 DB 계정은 GitHub/Netlify에 전달되지 않습니다. 계정이 이미 있으면 중복 생성하지 않습니다.
5. DB 백업과 복원, HTTPS `/health` 응답을 확인합니다. 사용자명·비밀번호·DB를 GitHub에 커밋하지 않습니다.

## Netlify

1. `NurionHoldings/SongGuard` 저장소와 `main`을 선택합니다.
2. 저장소의 `netlify.toml`을 사용합니다. 빌드 명령 `python3 scripts/build_netlify.py`, 게시 폴더 `dist`.
3. Netlify 빌드 환경변수 `SONG_GUARD_API_ORIGIN=https://실제-Python-서버주소`를 지정합니다. 경로·쿼리·인증정보는 입력하지 않습니다. 값이 없거나 HTTPS가 아니면 빌드가 중단됩니다.
4. 생성되는 `_redirects`는 `/api/*`와 `/health`를 프록시합니다. 브라우저는 항상 Netlify 사이트의 동일 출처 API를 사용합니다. 원장·계정·증빙은 게시 폴더에 포함하지 않습니다.
5. 미리보기 사이트를 검증하려면 백엔드의 허용 출처를 해당 미리보기 출처로 지정한 별도 시험 서버/DB를 사용합니다. 운영 DB의 허용 출처를 무분별하게 확대하지 않습니다.

## 실제 배포 후 검증

- 최초 화면의 로그인 버튼 → 로그인 → 자산관리 메뉴 → 관리자 계기판.
- 다른 기기/브라우저로 로그인해 저장한 사건이 유지되는지 확인.
- `/health`, 로그인 응답의 Secure/HttpOnly/SameSite 쿠키와 이후 `/api/state` 인증 확인.
- 채권/사건 저장, 증빙 업로드·다운로드, A4/PDF 출력, 접수증 등록, 전체 내보내기.
- 로그아웃 후 API 차단, 외부 출처 POST 거절, CSRF 누락 거절.
- 서버 재시작 후 DB·첨부자료 유지와 백업 복원.

이 검증은 실제 도메인·서버 연결 후 필요합니다. 로컬 테스트 통과를 실제 Netlify 프록시 운영 검증으로 간주하지 않습니다. 프록시의 요청 Host/Origin 및 Set-Cookie 전달을 현장에서 확인하세요.
