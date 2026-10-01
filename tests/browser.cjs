// Optional browser integration test, run in CI with Playwright installed.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'songguard-ui-'));
 const server=spawn('python',['server.py'],{env:{...process.env,PORT:'8092',SONG_GUARD_DB:path.join(temp,'test.db'),SONG_GUARD_ALLOW_REGISTRATION:'true',SONG_GUARD_SECURE_COOKIE:'false'},stdio:'inherit'});
 let browser,page;
 try {
  for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:8092/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true});page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8092');
  await page.locator('[name=username]').fill('browser-owner');await page.locator('[name=password]').fill('browser-test-password-123');
  await page.locator('#register').click();await page.locator('#shell').waitFor({state:'visible'});
  await page.locator('[data-page=claim]').click();await page.locator('[data-new=claim]').click();
  await page.locator('#record-form [name=title]').fill('테스트 담보채권');await page.locator('[name=debtor]').fill('가상 채무자');
  await page.locator('[name=principal]').fill('100000000');await page.locator('[name=rate]').fill('10');await page.locator('[name=cap]').fill('120000000');
  await page.locator('#add-payment').click();await page.locator('.payment-amount').fill('10000');
  await page.locator('#record-form button[type=submit]').click();await page.locator('#editor').waitFor({state:'hidden'});
  await page.getByText('테스트 담보채권',{exact:true}).waitFor();
  await page.locator('[data-page=asset]').click();await page.locator('[data-new=asset]').click();
  await page.locator('#record-form [name=title]').fill('테스트 공유지분');await page.locator('[name=address]').fill('가상 주소');
  await page.locator('[name=ownership]').selectOption('공유지분 소유');await page.locator('[name=share]').fill('1/10');
  await page.locator('[name=claim_id]').selectOption({label:'테스트 담보채권'});
  await page.locator('#record-form button[type=submit]').click();await page.locator('#editor').waitFor({state:'hidden'});
  await page.locator('[data-page=case]').click();await page.locator('[data-new=case]').click();
  await page.locator('#record-form [name=title]').fill('테스트 경매');await page.locator('[name=number]').fill('2026타경00000');
  await page.locator('[name=court]').fill('가상법원');await page.locator('[name=claim_id]').selectOption({label:'테스트 담보채권'});
  await page.locator('[name=asset_id]').selectOption({label:'테스트 공유지분'});
  await page.locator('[name=auction_date]').fill('2026-11-20');await page.locator('[name=minimum]').fill('90000000');
  await page.locator('#record-form button[type=submit]').click();await page.locator('#editor').waitFor({state:'hidden'});
  await page.locator('[data-page=task]').click();await page.getByText('직접 입찰·공유자 우선매수 검토',{exact:true}).waitFor();
  await page.locator('[data-page=analysis]').click();await page.locator('#analysis-case').selectOption({label:'테스트 경매'});
  await page.waitForFunction(()=>Number(document.querySelector('#scenario-form [name=claim]').value)>0);
  await page.locator('#scenario-form [name=resale]').fill('130000000');await page.locator('#scenario-form button').click();
  await page.locator('#scenario-result strong').first().waitFor();
  assert.match(await page.locator('#scenario-result').textContent(),/배당 추정/);
  await page.locator('#preemption-form [name=coowner_verified]').check();await page.locator('#preemption-form [name=other_share_verified]').check();
  await page.locator('#preemption-form button').click();await page.locator('#preemption-result').getByText(/우선매수 검토 대상/).waitFor();
  await page.locator('[data-page=case]').click();await page.locator('[data-view]').first().click();
  await page.locator('#upload').setInputFiles({name:'proof.txt',mimeType:'text/plain',buffer:Buffer.from('가상 증빙')});await page.locator('#upload-btn').click();
  await page.locator('#detail-content a').filter({hasText:'proof.txt'}).waitFor();await page.locator('#close-detail').click();
  await page.locator('[data-page=filing]').click();await page.locator('#new-filing').click();
  await page.locator('#filing-form [name=form_kind]').selectOption('statement');
  await page.locator('#filing-form [name=creditor]').fill('가상 채권자');await page.locator('#filing-form [name=creditor_address]').fill('가상 주소 1');
  await page.locator('#filing-form [name=phone]').fill('연락처 검증용');await page.locator('#filing-form [name=debtor_address]').fill('가상 주소 2');
  await page.locator('#filing-form [name=amount]').fill('99990000');await page.locator('#filing-form [name=breakdown]').fill('원금 99,990,000원. 이자 없음. 검증용 가상 자료.');
  await page.locator('#filing-form [name=basis]').fill('가상 대여 계약');await page.locator('#filing-form [name=attachments]').fill('가상 대여 계약서\n가상 등기사항증명서');
  await page.locator('[data-check]').evaluateAll(els=>els.forEach(el=>el.checked=true));await page.locator('#approve-filing').click();
  await page.getByText('출력준비',{exact:true}).last().waitFor();
  const printHref=await page.locator('#paperwork a[href^="/api/print/"]').getAttribute('href');
  const printPage=await page.context().newPage();await printPage.goto('http://127.0.0.1:8092'+printHref);
  await printPage.locator('#print:not([disabled])').waitFor();fs.mkdirSync('test-results',{recursive:true});
  await printPage.screenshot({path:'test-results/print-preview.png',fullPage:true});await printPage.close();
  await page.locator('#printed-confirm').check();await page.locator('#printed-filing').click();await page.locator('#receipt-form').waitFor();
  await page.locator('#receipt-file').setInputFiles({name:'receipt.txt',mimeType:'text/plain',buffer:Buffer.from('가상 법원 접수증')});await page.locator('#receipt-upload').click();await page.waitForFunction(()=>document.querySelector('#receipt-form [name=evidence]')?.value);
  await page.locator('#receipt-form [name=number]').fill('가상 접수 123');await page.locator('#receipt-form [name=by]').fill('가상 접수자');await page.locator('#receipt-form [name=signed]').check();await page.locator('#receipt-form button').click();
  await page.getByText('접수완료',{exact:true}).last().waitFor();await page.locator('#close-paperwork').click();
  // Render each form with explicit fictitious facts for PDF layout inspection.
  for(const kind of ['petition','statement','demand','preemption','special','correction','payment']){
   const printHtml=await page.evaluate(async kind=>{
    const st=await (await fetch('/api/state')).json();let caseRecord=st.records.find(r=>r.kind==='case');
    const post=async (route,body)=>{const r=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':st.csrf},body:JSON.stringify(body)});const v=await r.json();if(!r.ok)throw Error(v.error);return v;};
    if(kind==='petition'){
     const asset=await post('record',{kind:'asset',payload:{title:'가상 근저당 자산','ownership':'근저당'}});
     caseRecord={id:(await post('record',{kind:'case',payload:{title:'가상 임의경매 서식 검증','stage':'집행준비',type:'whole',asset_id:asset.id}})).id};
    }
    const data=Object.fromEntries(st.forms[kind].fields.map(f=>[f.key,'가상 검증 자료']));
    Object.assign(data,{signed_date:'2026-10-01',number:'2026타경00000',amount:'1000000',price:'2000000',dividend:'1000000',creditor:'가상 채권자',court:'가상 지방법원',attachments:'가상 계약서 1부\n가상 등기사항증명서 1부',property:'가상 토지: 가상시 가상구 가상동 1-1\n지목: 대, 면적: 100㎡\n실행 대상: 가상 채무자의 10분의 9 지분'});
    const rr=await fetch('/api/filing',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':st.csrf},body:JSON.stringify({action:'save',case_id:caseRecord.id,form_kind:kind,data})});const saved=await rr.json();
    if(!rr.ok)throw Error(saved.error);
    await post('filing',{action:'approve',id:saved.id,version:1,checks:Object.fromEntries(Object.keys(st.forms[kind].checks).map(k=>[k,true]))});
    return '/api/print/'+saved.id;
   },kind);
   const preview=await page.context().newPage();await preview.goto('http://127.0.0.1:8092'+printHtml);
   await preview.pdf({path:'test-results/'+kind+'.pdf',format:'A4',preferCSSPageSize:true});await preview.close();
  }
  await page.locator('[data-page=dashboard]').click();await page.locator('#toast').waitFor({state:'hidden'});fs.mkdirSync('test-results',{recursive:true});await page.screenshot({path:'test-results/desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'test-results/mobile.png',fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'mobile horizontal overflow');
  assert.deepEqual(errors,[],'browser runtime errors');
  console.log('Browser workflow passed: account, claim, case, generated task, analysis, preemption, evidence, responsive layout.');
 } catch(e) {if(page){fs.mkdirSync('test-results',{recursive:true});await page.screenshot({path:'test-results/failure.png',fullPage:true});console.error(await page.locator('#toast').textContent());}throw e;}
 finally {if(browser)await browser.close();server.kill();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
