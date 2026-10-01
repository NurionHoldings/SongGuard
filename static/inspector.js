'use strict';
// Deterministic checks of registered facts. No external legal or payment decisions.
globalThis.SongGuardInspector={version:'1.0',run(records,evidence,asOf){
 const findings=[],byId=new Map(records.map(r=>[r.id,r])),proof=new Map(evidence.map(e=>[e.id,e])),kinds=['asset','claim','case','filing','tax','task','event'];
 const add=(r,code,severity,message,action,due='')=>findings.push({id:r.id+':'+code,record_id:r.id,kind:r.kind,title:r.payload.title||r.id,code,severity,message,action,due});
 const attached=id=>evidence.some(e=>e.record_id===id);
 const validProof=(eid,rid)=>proof.has(eid)&&(!rid||proof.get(eid).record_id===rid);
 for(const r of records){const p=r.payload||{};if(!kinds.includes(r.kind))continue;
  for(const [key,kind] of [['asset_id','asset'],['claim_id','claim'],['case_id','case']])if(p[key]&&byId.get(p[key])?.kind!==kind)add(r,'link-'+key,'error','연결 자료가 없거나 자료 유형이 다릅니다.','해당 연결을 다시 선택하세요.');
  if(r.kind==='asset'){
   if(!p.address)add(r,'address','warning','자산 소재지가 누락되었습니다.','등기 원문으로 소재지를 입력하세요.');
   if(!attached(r.id))add(r,'asset-proof','warning','등기·권리 확인 증빙이 등록되지 않았습니다.','최신 등기 원문과 권리 근거를 등록하세요.');
   if(['공유지분 소유','담보 목적 지분이전'].includes(p.ownership)&&!p.share)add(r,'share','warning','지분율이 누락되었습니다.','등기상 지분과 담보 목적을 확인하세요.');
   if(p.ownership==='근저당'&&(!p.rank||!p.claim_id))add(r,'mortgage','warning','근저당 순위 또는 연결 채권이 누락되었습니다.','등기 순위와 피담보채권 연결을 확인하세요.');
  }
  if(r.kind==='claim'){
   if(!p.debtor||!p.creditor)add(r,'parties','warning','채권자·채무자 정보가 누락되었습니다.','당사자와 계약 정보를 확인하세요.');
   if(!attached(r.id))add(r,'claim-proof','warning','채권 약정·변제 증빙이 없습니다.','계약서와 변제내역 원문을 등록하세요.');
   if(!p.notes)add(r,'interest-basis','review','이율·충당 방식의 검토 근거가 기록되지 않았습니다.','약정과 적용 요건 검토 내용을 남기세요.');
  }
  if(r.kind==='case'){
   if(!p.asset_id||!p.claim_id)add(r,'case-links','warning','사건에 자산 또는 채권이 연결되지 않았습니다.','사건별 담보 자산과 채권을 연결하세요.');
   if(!p.court||!p.number)add(r,'case-identity','review','법원 또는 사건번호가 미등록입니다.','접수 전이면 예정 자료로 관리하고 접수 후 실제 번호를 입력하세요.');
   for(const [key,label] of [['auction_date','매각기일'],['distribution_date','배당기일'],['claim_deadline','채권신고·배당요구 확인기한'],['special_deadline','특별지급 신고기한']])if(p[key]&&p[key]<asOf&&!['전액회수','직접취득'].includes(p.stage))add(r,key,'warning',label+'이 지났습니다.','원문에서 진행 결과·기일 변경·후속 제출 여부를 확인하세요.',p[key]);
   if(['전액회수','직접취득'].includes(p.stage)&&!validProof(p.completion_evidence,r.id))add(r,'completion','error','사건 종결 증빙이 없거나 연결이 맞지 않습니다.','해당 사건의 입금·취득 증빙을 확인하세요.');
   const a=byId.get(p.asset_id)?.payload;if(p.type==='share'&&a?.ownership==='공유지분 소유')add(r,'preemption','review','공유지분 매각 사건의 우선매수 검토가 필요합니다.','매각 대상·공유자 지위·조건·접수 증빙을 확인하세요.');
  }
  if(r.kind==='filing'){
   if(p.status!=='접수완료')add(r,'filing-pending','review','서류 상태: '+p.status,'작성·확정·출력·사람 접수 단계를 확인하세요.');
   if(p.status==='접수완료'&&!validProof(p.receipt?.evidence,p.case_id))add(r,'filing-proof','error','해당 사건의 접수증을 확인할 수 없습니다.','실제 접수증 연결과 접수번호를 확인하세요.');
  }
  if(r.kind==='tax'){
   const confirmed=p.role==='본인 납부'&&p.due_confirmed===true&&p.due&&validProof(p.due_evidence,r.id)&&p.status!=='예상';
   if(p.role==='본인 납부'&&!confirmed&&!['납부완료','취소확인'].includes(p.status))add(r,'tax-date-unverified','review','납부일 확인 필요 — 날짜 안내를 하지 않습니다.','고지서·과세관청 원문으로 실제 납부기한을 확인하세요.');
   if(confirmed&&!['납부완료','취소확인'].includes(p.status)&&p.due<=asOf)add(r,'tax-due','warning',p.due===asOf?'확인된 세금 납부기한이 오늘입니다.':'확인된 세금 납부기한이 지났습니다.','납부·연장·분납 여부를 원문과 대조하세요.',p.due);
   if(p.role==='채무자 조세채권'&&!p.legal_date)add(r,'tax-priority','review','조세 법정기일이 미등록입니다.','교부청구 원문과 담보 설정일·배당순위를 검토하세요.');
   if(['납부완료','취소확인'].includes(p.status)&&!validProof(p.completion_evidence,r.id))add(r,'tax-proof','error','납부·취소 상태를 뒷받침하는 증빙이 없습니다.','해당 세금의 납부·취소 증빙을 등록하세요.');
  }
  if(r.kind==='task'){
   if(p.done&&!validProof(p.evidence))add(r,'task-proof','error','완료 업무의 증빙이 없습니다.','완료 근거를 등록하세요.');
   if(!p.done&&p.due&&p.due<=asOf&&!p.tax_id)add(r,'task-due','warning',p.due===asOf?'업무 기한이 오늘입니다.':'미완료 업무 기한이 지났습니다.','원문 기한과 처리 상태를 확인하세요.',p.due);
  }
  if(r.kind==='event'&&!p.notes)add(r,'event-basis','review','변수 발생 근거가 미등록입니다.','통지·결정·현황 원문과 검토 내용을 기록하세요.');
 }
 findings.sort((a,b)=>({error:0,warning:1,review:2}[a.severity]-{error:0,warning:1,review:2}[b.severity]));
 return {title:'아르카온 점검 보고서',engine_version:this.version,as_of:asOf,created_at:new Date().toISOString(),counts:Object.fromEntries(kinds.map(k=>[k,records.filter(r=>r.kind===k).length])),summary:{error:findings.filter(f=>f.severity==='error').length,warning:findings.filter(f=>f.severity==='warning').length,review:findings.filter(f=>f.severity==='review').length},findings,limitations:['등록 자료에 대한 규칙 기반 점검입니다.','외부 등기·법원·세금 원문을 자동 조회하거나 문서 내용을 판독하지 않습니다.','증빙 연결 확인은 원문의 진위·내용 확인을 대신하지 않습니다.','입찰·납부·법률 판단·코드 수정·배포를 자동 실행하지 않습니다.']};
}};
