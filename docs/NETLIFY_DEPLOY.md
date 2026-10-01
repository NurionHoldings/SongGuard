# GitHub → Netlify 전체 서비스 배포

GitHub의 `main` 변경을 Netlify가 빌드하여 화면과 Node.js Functions를 함께 배포합니다. 별도 Python 서버나 `SONG_GUARD_API_ORIGIN` 설정은 필요하지 않습니다.

## 구현 구조

- 화면: `static` → `npm run build` → `dist`.
- API: `netlify/functions/api.mts`, `/api/*` 및 `/health`.
- 원장·사건·접수·감사·세션: Netlify Database(PostgreSQL), `@netlify/database` SDK.
- 첨부 원문: Netlify Blobs. 파일당 4MB. 업로드 후 DB 메타데이터를 저장하며 실패 시 미등록 Blob을 정리합니다.
- 원장 계산: Decimal.js. Python Decimal 계산과 비교 검증합니다.
- 동시 변경: 사용자 행 잠금 + 버전 확인 + 트랜잭션. 사건/접수에 따른 자동 업무와 감사 기록은 같은 트랜잭션으로 처리합니다.
- 데이터 내보내기: 원장·감사·증빙 ZIP. 첨부 합계 16MB까지 제공하며 초과 시 개별 증빙 다운로드를 안내합니다.

## Netlify 설정

1. 저장소 `NurionHoldings/SongGuard`, 브랜치 `main`, 루트 `netlify.toml`을 사용합니다.
2. 빌드 명령 `npm run build`, 게시 폴더 `dist`, Node 24. 의존성은 `package-lock.json`으로 고정합니다.
3. Netlify Database는 SDK를 설치한 프로젝트의 배포/개발 흐름에 연결됩니다. 계정 플랜과 프로젝트의 Database 상태를 확인합니다. 스키마는 `netlify/database/migrations/202610010001_songguard/migration.sql`에서 생성됩니다.
4. 기존 Neon 확장이 제공하는 `NETLIFY_DATABASE_URL`도 호환 경로로 지원합니다. 새 Netlify Database는 `NETLIFY_DB_URL`을 우선합니다. 연결 문자열은 공개 파일에 넣지 않습니다.
5. `SONG_GUARD_ADMIN_PASSWORD_HASH`를 Functions 전용 비밀 환경변수로 설정합니다. 형식은 `salt$hash`, salt는 16바이트 hex, hash는 PBKDF2-HMAC-SHA256(600,000회, 32바이트) hex입니다. 기본 관리자 아이디는 `song`; 다른 아이디는 `SONG_GUARD_ADMIN_USERNAME`으로 설정합니다. 첫 로그인 시 이 해시를 DB에 등록합니다. 실제 비밀번호/해시는 저장소에 포함하지 않습니다.
6. 공개 회원가입은 비활성화되어 있습니다. 로그인은 HttpOnly/Secure/SameSite 세션, 같은 출처 검사(`@netlify/identity`), CSRF 토큰, DB 기반 IP 로그인 제한으로 보호됩니다.
7. 선택적으로 Netlify Identity 관리자 인증 API(`/api/identity/login`)를 활성화할 수 있습니다. Identity를 설정한 후 `SONG_GUARD_IDENTITY_ENABLED=true`를 지정하며 관리자 역할을 가진 사용자만 허용됩니다. 기존 `song` 로그인은 운영자 발급 계정 방식으로 유지합니다.

## 운영 확인

최초 화면은 로그인 버튼 하나만 표시합니다. 로그인 후 자산관리 메뉴를 클릭하면 관리자 계기판이 열립니다.

- `/health`: Functions와 DB 연결이 정상일 때 `status:ok`.
- 지정한 계정 로그인, 세션 유지, 로그아웃 후 API 차단.
- 채권/사건 저장 → 새 브라우저/재배포 후 저장된 자료 유지.
- 증빙 업로드/다운로드, 7종 A4/PDF 문서, 검토→확정→출력확인→접수증 등록.
- 사건 기일/변수/접수 후 자동 업무, 버전 충돌, 다른 사용자 자료 접근 차단.
- 전체 ZIP 내보내기와 DB 백업/복구는 함께 운영합니다. ZIP은 계정·세션을 포함한 전체 DB 백업이 아닙니다.

배포 미리보기는 별도 DB 브랜치를 사용합니다. Blob 신규 업로드는 배포 ID별 경로로 분리합니다. 이전 SQLite의 실제 원장 자료가 있다면 PostgreSQL 이전 작업을 별도로 수행해야 합니다. 로컬 개발 계정 DB가 자동으로 공개 서비스에 복제되지 않습니다.

법원 전자신청은 공식 포털 연결 경로만 제공하며, 자동 접수·등기 조회·입금 확인은 별도 연동입니다.
