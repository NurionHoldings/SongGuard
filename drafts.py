"""Review-only document drafts, never silently assert unverified legal facts."""
from datetime import date
from core import ledger

def draft(kind,case,claim,asset):
    def val(data,key): return str(data.get(key) or '[확인·입력 필요]')
    parties=f"채권자: {val(claim,'creditor')}\n주소: {val(claim,'creditor_address')}\n채무자: {val(claim,'debtor')}\n주소: {val(claim,'debtor_address')}\n"
    prefix='[제출 전 검토용 초안 · 자동 접수되지 않음]\n'
    court=val(case,'court'); number=val(case,'number'); prop=val(asset,'legal_description')
    amount=None
    if claim:
        amount=ledger(claim)
    calculation=(f"계산 기준일: {val(claim,'as_of')}\n원금 잔액: {amount['principal']:,}원\n이자 추정: {amount['interest']:,}원\n비용: {amount['costs']:,}원\n합계: {amount['total']:,}원\n담보한도 적용 추정: {amount['secured_estimate']:,}원\n계산 가정: {amount['assumptions']}\n" if amount else '청구액: [연결 채권 및 계산자료 필요]\n')
    if kind=='petition':
        text=f"부동산 임의경매 신청서 초안\n\n{parties}\n신청취지\n별지 기재 부동산에 관하여 담보권 실행을 위한 경매절차를 개시하여 주시기 바랍니다.\n\n신청이유\n1. 채권의 발생: {val(claim,'notes')}\n2. 담보권 설정: {val(asset,'rank')} / 설정일 {val(asset,'registered')}\n3. 변제기·연체·기한이익 상실의 근거: {val(claim,'default_basis')}\n4. 청구채권: 아래 계산과 계약·담보범위를 확인하여 확정합니다.\n{calculation}\n별지 부동산 표시\n{prop}\n\n첨부 확인 목록\n등기사항증명서, 근저당·채권 계약과 실행 증빙, 변제 내역, 당사자·목적물 및 비용 관련 사건별 필요서류 [검토 후 확정]\n"
    elif kind=='statement':
        text=f"채권계산서 초안\n사건: {number}\n\n{parties}\n채권 발생 및 담보 근거\n{val(claim,'notes')}\n{val(asset,'rank')}\n\n채권 계산\n{calculation}\n변제내역\n"+'\n'.join(f"{p['date']} / {p['amount']}원" for p in claim.get('payments',[]))+'\n\n첨부: 계약·변제·담보 및 계산 근거 [확인 필요]\n배당요구 또는 별도 채권신고 필요 여부는 본 문서 생성과 별도로 확인합니다.\n'
    elif kind=='preemption':
        text=f"공유자 우선매수신고서 초안\n사건: {number}\n\n신고인: {val(claim,'creditor')}\n주소: {val(claim,'creditor_address')}\n본인 공유지분: {val(asset,'share')}\n\n신고 내용\n민사집행법 제140조의 적용 요건이 확인되는 경우, 해당 사건 매각 대상인 다른 공유자의 지분을 최고매수신고가격과 같은 가격으로 우선매수하겠다는 취지로 신고합니다.\n\n매각 대상\n{prop}\n매각 유형: {val(case,'type')}\n매각기일: {val(case,'auction_date')}\n\n제출 전 확인\n본인 공유자 자격, 실제 매각 지분, 사건별 적용 가능성 및 제한, 보증 제공액·방법, 신고 시점, 여러 공유자 행사 시 취득 지분을 확인하세요.\n첨부: 공유지분 등기 및 보증 제공 증빙 [확인 필요]\n"
    elif kind=='special':
        text=f"채권자 매수 특별지급 신고 초안\n사건: {number}\n\n{parties}\n신고 내용\n신고인은 해당 사건의 매수인이자 배당받을 채권자임을 증빙으로 확인한 후, 민사집행법 제143조 제2항에 따른 특별지급을 신고하고자 합니다.\n\n매수가격: [실제 최고매수신고가격 확인]\n배당받아야 할 금액: [확정·검토 필요, 채권총액과 구분]\n차액: [매수가격에서 해당 배당금액을 제외하여 산정]\n\n채권자료\n{calculation}\n제출 전 확인\n매각결정기일 종료까지 신고, 배당기일 지급, 배당액 이의 시 해당 금액 납부, 보증금 처리, 실제 법원 요구서류를 확인하세요.\n"
    else: raise ValueError('지원되지 않는 문서 종류')
    return prefix+text+f"\n{date.today().isoformat()}\n신청·신고인: [서명 또는 날인 확인]\n{court} 귀중\n\n주의: 사실과 법률요건, 이율·충당·청구범위, 최신 법원 서식을 검토한 뒤 확정하세요.\n"
