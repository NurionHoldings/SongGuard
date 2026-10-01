"""Paper filing workflow: reviewed snapshots, A4 printing, human receipt."""
from html import escape
from datetime import date
from decimal import Decimal

COMMON=[('creditor','채권자·신고인 성명/법인명'),('creditor_address','채권자 주소'),('phone','연락처'),('debtor','채무자 성명/법인명'),('debtor_address','채무자 주소'),('court','제출 법원'),('signed_date','작성일'),('attachments','실제 첨부서류 목록 (한 줄에 한 항목)')]
EXTRA={
 'petition':[('owner','등기상 소유자'),('owner_address','소유자 주소'),('property','등기상 부동산 표시 및 실행 대상 지분'),('security','담보권 표시 (등기일·접수번호·순위·최고액 등)'),('basis','피담보채권 발생 원인·계약·대여 사실'),('default_basis','변제기 도래·연체·기한이익 상실 근거'),('amount','이번 신청 청구금액'),('breakdown','원금·이자·지연손해금의 산출내역과 기간'),('scope','피담보채권 전부/일부 실행의 취지와 범위')],
 'statement':[('number','사건번호'),('amount','신고 채권액 합계'),('breakdown','원금·이자·비용·계산기간·적용이율'),('basis','채권 및 담보의 근거')],
 'demand':[('number','사건번호'),('amount','배당요구 채권액'),('breakdown','청구액의 산출내역'),('basis','집행권원 또는 우선변제권 등 배당요구 자격 근거')],
 'preemption':[('number','사건번호'),('property','매각 대상 부동산과 다른 공유자의 지분'),('share','본인 공유지분과 등기 근거'),('security','제공할 보증 금액·방법 및 증빙'),('basis','우선매수 적용 확인 근거·매각조건')],
 'special':[('number','사건번호'),('price','실제 매수가격'),('dividend','배당받아야 할 금액'),('security','기납부 매수보증금과 처리 방법'),('basis','매수인·배당채권자 자격 및 신고기한 확인 근거')],
 'correction':[('number','사건번호'),('order_date','보정명령일'),('correction','명령별 보정 내용과 첨부자료')],
 'payment':[('number','사건번호'),('amount','지급 청구 배당액'),('payee','수령인'),('bank','은행명·예금주·계좌번호'),('basis','배당표·지급 안내 및 수령자격 근거')]
}
TITLES={'petition':'부동산 임의경매 신청서','statement':'채권계산서','demand':'배당요구신청서','preemption':'공유자 우선매수신고서','special':'채권자 매수 특별지급 신고서','correction':'보정서','payment':'배당금 지급청구서'}
CHECKS={'facts':'당사자·소유자·목적물·사건번호를 원문과 대조했습니다.','amounts':'청구금액·이율·계산기간·담보범위를 확인했습니다.','eligibility':'이 서식의 신청·신고 자격과 기한, 사건별 매각조건을 확인했습니다.','attachments':'실제 첨부서류와 비용 납부·보증 제공 요구사항을 확인했습니다.','local_form':'관할 법원의 최신 서식·제출부수·접수 방법을 확인했습니다.'}
def schemas():
    return {k:{'title':v,'fields':[{'key':a,'label':b} for a,b in COMMON+EXTRA[k]],'checks':CHECKS} for k,v in TITLES.items()}

def missing(kind,data):
    if kind not in TITLES: raise ValueError('지원되지 않는 서식')
    result=[label for key,label in COMMON+EXTRA[kind] if not str(data.get(key,'')).strip()]
    for key in ('amount','price','dividend'):
        if data.get(key):
            try:
                n=Decimal(str(data[key]).replace(',',''))
                if not n.is_finite() or n<0 or n!=n.to_integral_value(): raise ValueError()
            except Exception: result.append(key+' 금액은 0 이상의 정수로 입력하세요.')
    if data.get('signed_date'):
        try: date.fromisoformat(data['signed_date'])
        except ValueError: result.append('작성일 형식')
    if kind=='special' and not result and Decimal(data['dividend'].replace(',',''))>Decimal(data['price'].replace(',','')): result.append('배당금액은 매수가격 이하여야 합니다.')
    return result

def html(filing):
    kind=filing['form_kind']; d=filing['data']; approved=filing['status']!='작성중'; h=lambda x:escape(str(x or ''))
    def value(key): return h(d.get(key,'미입력')).replace('\n','<br>')
    def section(title,key): return f'<section><h2>{h(title)}</h2><p>{value(key)}</p></section>'
    body=f'<h1>{TITLES[kind]}</h1>'
    if kind!='petition': body+=f'<p class="case">사건 {value("number")}</p>'
    body+=f'<div class="parties"><p>채권자(신고인)　{value("creditor")}<br>주소　{value("creditor_address")}<br>연락처　{value("phone")}</p><p>채무자　{value("debtor")}<br>주소　{value("debtor_address")}</p>'
    if kind=='petition': body+=f'<p>소유자　{value("owner")}<br>주소　{value("owner_address")}</p>'
    body+='</div>'
    if kind=='petition':
        body+=f'<section><h2>신청취지</h2><p>별지 기재 부동산에 관하여 담보권 실행을 위한 경매절차를 개시하여 주시기 바랍니다.</p></section>{section("청구금액 (원)","amount")}{section("청구금액 산출내역","breakdown")}{section("신청이유 - 채권의 발생","basis")}{section("변제기 및 담보권 실행 사유","default_basis")}{section("담보권의 표시","security")}{section("담보권 실행의 취지와 범위","scope")}'
    elif kind in ('statement','demand'):
        body+=f'<p>{"아래와 같이 채권액을 신고합니다." if kind=="statement" else "아래 채권에 관하여 배당을 요구합니다."}</p>'+section('채권액 (원)','amount')+section('산출내역','breakdown')+section('채권 및 자격의 근거','basis')
    elif kind=='preemption':
        body+='<p>민사집행법 제140조에 따라 최고매수신고가격과 같은 가격으로 아래 매각 대상 지분을 우선매수하겠다는 신고를 합니다.</p>'+section('본인의 공유자 지위','share')+section('매각 대상','property')+section('보증 제공','security')+section('신고 근거','basis')
    elif kind=='special':
        try: difference=Decimal(str(d.get('price','0')).replace(',','') or '0')-Decimal(str(d.get('dividend','0')).replace(',','') or '0')
        except Exception: difference='미확인'
        body+='<p>민사집행법 제143조 제2항에 따라 배당받아야 할 금액을 제외한 대금을 배당기일에 지급하고자 신고합니다.</p>'+section('매수가격 (원)','price')+section('배당받아야 할 금액 (원)','dividend')+f'<p>위 배당액을 제외한 금액: {h(difference)}원</p>'+section('기납부 보증금과 처리','security')+section('신고 자격 및 근거','basis')
    elif kind=='correction': body+=section('보정명령일','order_date')+section('보정 내용','correction')
    elif kind=='payment': body+='<p>아래 배당금의 지급을 청구합니다.</p>'+section('지급 청구액 (원)','amount')+section('수령인','payee')+section('지급 계좌','bank')+section('청구 근거','basis')
    body+=section('첨부서류','attachments')+f'<div class="signature"><p>{value("signed_date")}</p><p>신청·신고인　{value("creditor")}　(서명 또는 인)</p><h2>{value("court")} 귀중</h2></div>'
    if kind=='petition': body+='<article class="appendix"><h1>별지 부동산 목록</h1><p>'+value('property')+'</p></article>'
    instruction='<article class="appendix cover"><h1>접수 준비표 · 제출 문서와 분리</h1><p>이 페이지는 본인 보관용입니다. 신청서와 구분해 보관하세요.</p><p>문서번호: '+h(filing['id'])+'</p><ol>'+''.join('<li>'+h(v)+'</li>' for v in CHECKS.values())+'</ol><p>출력 → 서명·날인 → 실제 첨부자료 준비 → 관할 법원 접수 → 접수증 보관 → Song_Guard에 접수기록 등록</p><p>접수일: __________　사건/접수번호: __________________</p><p>접수 담당자: __________　보정·후속 안내: __________________</p><p>공유자 우선매수는 사건별 보증 제공과 신고 시점 확인이 필요합니다. 특별지급은 매각결정기일 종료까지 신고하고 배당액 이의가 있는 경우 추가 납부 가능성을 확인합니다. 배당금 지급은 법원의 지정 서식과 수령자격·계좌증빙을 확인하세요.</p></article>'
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{TITLES[kind]}</title><link rel="stylesheet" href="/print.css"><script src="/print.js" defer></script></head><body><div class="toolbar"><strong>{h(filing["status"])}</strong><span>서명·날인과 첨부자료를 준비하여 사람이 접수합니다.</span><button id="print" {"" if approved else "disabled"}>인쇄 / PDF 저장</button><button id="back">이전 화면</button></div>{"<div class=warning>작성중 문서입니다. 필수 항목과 확인사항을 완료한 뒤 출력본을 확정하세요.</div>" if not approved else ""}<article class="document">{body}</article>{instruction}</body></html>'
