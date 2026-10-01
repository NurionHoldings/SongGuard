"""Deterministic calculations. Money uses Decimal; legal facts require verification."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import date

def money(value):
    try: n = Decimal(str(value))
    except InvalidOperation: raise ValueError('금액 입력을 확인하세요.')
    if not n.is_finite() or n < 0:
        raise ValueError('금액은 0 이상의 유한한 값이어야 합니다.')
    return n

def won(n):
    return int(n.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def ledger(c):
    principal = money(c['principal'])
    start, end = date.fromisoformat(c['start']), date.fromisoformat(c['as_of'])
    if end < start: raise ValueError('기준일은 대여일 이후여야 합니다.')
    rate = money(c.get('rate', 0)) / 100
    if rate > 1: raise ValueError('이율 입력을 확인하세요.')
    payments=c.get('payments', [])
    if not isinstance(payments,list) or any(not isinstance(p,dict) for p in payments): raise ValueError('변제내역은 JSON 배열이어야 합니다.')
    events = sorted(payments, key=lambda p: p['date'])
    interest, costs = Decimal(0), money(c.get('costs', 0))
    cursor = start
    rows = []
    for p in events:
        day = date.fromisoformat(p['date'])
        if day < start or day > end: raise ValueError('변제일이 계산기간 밖입니다.')
        interest += principal * rate * Decimal((day-cursor).days) / 365
        amount = money(p['amount'])
        original = amount
        for target in ('costs', 'interest', 'principal'):
            balance = {'costs': costs, 'interest': interest, 'principal': principal}[target]
            used = min(amount, balance)
            if target == 'costs': costs -= used
            elif target == 'interest': interest -= used
            else: principal -= used
            amount -= used
        if amount > 0: raise ValueError('변제액이 계산된 채무액을 초과합니다. 별도 정산이 필요합니다.')
        rows.append({'date': day.isoformat(), 'payment': won(original), 'principal': won(principal), 'interest': won(interest), 'costs': won(costs)})
        cursor = day
    interest += principal * rate * Decimal((end-cursor).days)/365
    total = principal + interest + costs
    cap = money(c.get('cap', total))
    return {'principal': won(principal), 'interest': won(interest), 'costs': won(costs), 'total': won(total), 'secured_estimate': won(min(total, cap)), 'rows': rows, 'assumptions': '단일 연이율·365일 단리·비용→이자→원금 충당. 약정/법률상 이율·충당·담보범위 확인 후 사용.'}

def scenario(c):
    price, priority, execution = (money(c.get(k, 0)) for k in ('price', 'priority', 'execution'))
    claim, cap = money(c.get('claim', 0)), money(c.get('cap', 0))
    available = max(Decimal(0), price-priority-execution)
    dividend = min(available, claim, cap)
    taxes, holding, repair, sale = (money(c.get(k, 0)) for k in ('taxes','holding','repair','sale_cost'))
    value = money(c.get('resale',0))
    deposit = money(c.get('deposit',0))
    if deposit > price: raise ValueError('보증금은 매수가격을 초과할 수 없습니다.')
    extra = taxes+holding+repair+sale
    return {'dividend': won(dividend), 'shortfall': won(max(Decimal(0),claim-dividend)), 'cash_normal': won(price+extra), 'cash_with_special_payment': won(price-dividend+extra), 'remaining_normal': won(price-deposit), 'remaining_special': won(max(Decimal(0),price-dividend-deposit)), 'asset_net_value': won(value-extra), 'economic_recovery': won(value-price-extra+dividend), 'assumptions': '입력한 선순위 금액과 담보한도를 적용한 단일 물건 추정. 실제 배당·세액·인수권리 확정 아님. 특별지급은 자격·기한·이의 확인 필요.'}

def preemption(c):
    if c.get('type') != 'share':
        return {'status':'review', 'message':'전체매각·공유물분할·일괄매각은 우선매수 적용을 별도 검토하세요.'}
    if not c.get('coowner_verified') or not c.get('other_share_verified'):
        return {'status':'review','message':'본인의 공유자 지위와 다른 공유자 지분 매각 여부를 등기로 확인하세요.'}
    return {'status':'candidate','message':'우선매수 검토 대상입니다. 민사집행법 제140조상 매각기일까지 보증 제공 및 최고매수신고가격과 같은 가격의 신고가 필요합니다. 사건 매각조건과 행사 제한을 확인하세요.'}

VARIABLES = {
 '연체·기한이익 상실': ('계약과 독촉·도달 증빙 확인','임의경매 요건 검토'),
 '보정명령': ('명령 원문과 송달일 등록','보정서 작성 및 제출 증빙 등록'),
 '송달불능·사망·해산': ('당사자와 승계 자료 확인','주소보정·상속·승계 검토'),
 '중복경매·병합': ('선행/후행 사건과 종기 연결','담보·기한·청구 중복 검토'),
 '취하·취소·무잉여': ('결정 및 효력 확인','독립 신청·보증 등 대응 검토'),
 '집행정지·회생·파산': ('결정문과 적용 범위 확인','집행 가능성 전문가 검토'),
 '유찰·기일변경': ('새 매각조건 및 기일 등록','배당/입찰 시나리오 재계산'),
 '일괄매각·공유물분할': ('대상과 매각 근거 확인','우선매수 적용 별도 검토'),
 '임차인·조세·우선권': ('증빙·기준일·법정 우선순위 확인','배당과 인수부담 재검토'),
 '유치권·가등기·신탁·지상권': ('권리 원문 및 성립요건 확인','자동 판단 보류·전문가 검토'),
 '매각불허가·항고': ('결정문·송달일·불복기한 확인','진행 상태와 대응기한 수정'),
 '대금미납·재매각': ('기한·보증금·재매각 조건 확인','필요자금 및 입찰 제한 검토'),
 '공유자 우선매수': ('공유지분과 보증·매각조건 확인','신고 준비·자금 상한 확인'),
 '배당액·순위 이의': ('배당표·기일·이의 증빙 확인','이의 및 후속 소송 기한 전문가 검토'),
 '공탁·지급지연': ('공탁 사유·번호·해소 조건 확인','출급 요건·실제 입금 확인'),
 '일부변제·채권양도·시효': ('변제/양도/시효 관련 증빙 확인','원장·자격·잔액 재검토'),
 '인도·명도·취득비용': ('점유 권원 및 취득일 확인','인도 절차·세금·보유비 검토'),
 '미분류 변수': ('원문과 발생일 등록','자동 진행 보류·검토 담당자 지정')
}
