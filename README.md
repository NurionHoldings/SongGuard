# Song_Guard

부동산 담보·공유지분 기반 채권보전 및 경매회수 관리실. 저장소 실제 이름은 `NurionHoldings/SongGuard`, 제품/템플릿 이름은 `Song_Guard`입니다.

## 실행

Python 3.12 이상. 외부 Python 패키지가 필요하지 않습니다.

```bash
python manage.py create-user my-user
# 로컬 HTTP 개발 환경에서만 Secure 쿠키를 끕니다.
SONG_GUARD_SECURE_COOKIE=false python server.py
```

http://localhost:8000 에서 로그인합니다. 운영 계정 비밀번호는 12자 이상 필요합니다. 공개 가입은 기본 차단입니다. 개발환경에서 가입 화면을 시험할 때만 `SONG_GUARD_ALLOW_REGISTRATION=true`를 설정합니다.

Windows PowerShell:
```powershell
python manage.py create-user my-user
$env:SONG_GUARD_SECURE_COOKIE="false"
python server.py
```

## 운영 배포

```bash
docker compose up -d --build
docker compose exec songguard python manage.py create-user my-user
```

TLS 역방향 프록시를 로컬 8000 포트 앞에 구성하세요. 운영에서는 Secure 쿠키 기본값을 유지합니다. 데이터는 `/data/songguard.sqlite3`에 저장되며 Docker의 `songguard-data` 볼륨으로 유지됩니다. `PORT`와 `SONG_GUARD_DB`로 포트/DB 경로를 변경할 수 있습니다. 정적 호스팅만으로는 SQLite 서버를 실행할 수 없습니다.

상태 확인: `GET /health`. 백업: `python manage.py backup /안전한경로/songguard-backup.sqlite3`. 복구는 서버를 중지하고 백업 DB를 원래 DB 경로에 배치한 뒤 소유권/권한을 확인합니다. 원장, 계정, 감사, 첨부파일이 같은 DB에 포함됩니다. 백업에 민감정보가 있으므로 암호화 저장소에서 보관하고 복구를 시험하세요.

## 사용 순서

1. 채권 원장에 대여일·원금·이율·변제·담보한도를 등록하고 적용 근거를 기록합니다.
2. 담보 및 공유지분을 등록해 채권과 연결합니다. 담보 목적 지분이전과 일반 소유권은 구분합니다.
3. 경매사건을 등록하고 법원·사건번호·진행 단계·관련 기일을 확인합니다.
4. 기일 준비업무가 자동 생성됩니다. 법원 문서의 실제 기한을 확인하고 담당자를 지정합니다.
5. 사건 변수 등록 시 검토 업무가 생성됩니다. 미분류 변수도 기록할 수 있습니다.
6. 입찰·우선매수 화면에서 사건을 선택해 배당/자금 시나리오를 비교합니다.
7. 상세 화면에 증빙을 업로드합니다. 표시된 증빙 ID를 완료 또는 종결 필드에 입력합니다.
8. 실제 회수액은 채권의 변제내역에 반영합니다. 사건 회수액과 원장의 변제는 자동 중복 차감하지 않습니다.
9. 직접취득 부동산은 별도 자산으로 등록하고 인도·세금·운영·매각 업무를 연결합니다.

## 자동화 범위와 제한

이 버전은 **자체 채권관리 및 수동 문서 등록 기반 사건관리 시스템**입니다. 외부 법원 접수/전자서명, 등기 자동조회, 은행 입금확인, OCR/AI 원문분석, 외부 알림은 미연동입니다. 법원 제출용 정식 신청서 자동 작성과 제출도 완료되지 않았으며 내부 검토자료를 제공합니다. 화면에 외부 연동 상태와 계산 가정을 표시합니다.

채권 계산은 단일 연이율·365일 단리·비용→이자→원금 충당입니다. 이율 변경 및 법정 최고이율의 역사적 적용, 약정 충당, 공동담보/경합배당은 자동 판정하지 않습니다. 공유자 우선매수는 자격 후보의 안내이고 법률상 행사 가능성을 확정하지 않습니다. 모든 경매 변수의 완전한 자동 판단을 보장하지 않습니다.

자세한 설계: [ARCHITECTURE](docs/ARCHITECTURE.md), 법률 근거: [LEGAL_RULES](docs/LEGAL_RULES.md).

## 검증

```bash
python -m unittest discover -s tests -v
node --check static/app.js
```

금액 계산·변제충당·담보한도·자금 시나리오·우선매수 검토와 실제 HTTP 서버의 계정분리·CSRF·증빙·기일업무·버전충돌·내보내기를 검사합니다. GitHub Actions에서 같은 검사와 Docker 빌드를 수행합니다.
