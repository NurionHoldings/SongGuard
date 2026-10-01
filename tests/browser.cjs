// Optional browser integration test, run in CI with Playwright installed.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'songguard-ui-'));
 const netlifyRuntime=process.env.SONG_GUARD_TEST_RUNTIME==='netlify';
 const server=spawn(netlifyRuntime?'node':'python',netlifyRuntime?['tests/netlify-test-server.mjs']:['server.py'],{env:{...process.env,PORT:'8092',SONG_GUARD_DB:path.join(temp,'test.db'),SONG_GUARD_ALLOW_REGISTRATION:'true',SONG_GUARD_SECURE_COOKIE:'false'},stdio:'inherit'});
 let browser,page;
 try {
  for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:8092/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true,executablePath:process.env.SONG_GUARD_BROWSER_PATH||undefined});const context=await browser.newContext({viewport:{width:1440,height:1000}});page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8092');
  assert.equal(await page.locator('#shell').isVisible(),false);assert.equal(await page.locator('#auth').isVisible(),false);await page.locator('#start').waitFor({state:'visible'});fs.mkdirSync('test-results',{recursive:true});await page.screenshot({path:'test-results/start.png',fullPage:true});assert.equal(await page.locator('#enter-cockpit').isVisible(),false);await page.locator('#start-account').click();await page.locator('#auth').waitFor({state:'visible'});
  await page.locator('[name=username]').fill('browser-owner');await page.locator('[name=password]').fill('browser-test-password-123');
  assert.equal(await page.locator('#register').isVisible(),false);
  await page.evaluate(runtime=>window.songGuardTestRuntime=runtime,netlifyRuntime?'netlify':'python');
  const signup=await page.evaluate(async()=>{const r=await fetch((window.songGuardTestRuntime==='netlify'?'/api/login':'/api/register'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'browser-owner',password:'browser-test-password-123'})});return r.status});assert.equal(signup,200);await page.reload();await page.locator('#start').waitFor({state:'visible'});assert.equal(await page.locator('#shell').isVisible(),false);await page.locator('#enter-cockpit').click();await page.locator('#shell').waitFor({state:'visible'});
  await page.locator('nav [data-page=claim]').click();await page.locator('[data-new=claim]').click();
  await page.locator('#record-form [name=title]').fill('테스트 담보채권');await page.locator('[name=debtor]').fill('가상 채무자');
  await page.locator('[name=principal]').fill('100000000');await page.locator('[name=rate]').fill('10');await page.locator('[name=cap]').fill('120000000');
  await page.locator('#add-payment').click();await page.locator('.payment-amount').fill('10000');
  await page.locator('#record-form button[type=submit]').click();await page.locator('#editor').waitFor({state:'hidden'});
  await page.getByText('테스트 담보채권',{exact:true}).waitFor();
  const mirror=await context.newPage();await mirror.goto('http://127.0.0.1:8092');await mirror.locator('#enter-cockpit').click();await mirror.locator('nav [data-page=asset]').click();
  await page.locator('nav [data-page=dashboard]').click();await page.locator('.command-strip [data-new=asset]').click();
  await page.locator('#record-form [name=title]').fill('테스트 공유지분');await page.locator('[name=address]').fill('가상 주소');
  await page.locator('[name=ownership]').selectOption('공유지분 소유');await page.locator('[name=share]').fill('1/10');
  await page.locator('[name=claim_id]').selectOption({label:'테스트 담보채권'});
  await page.locator('#record-form button[type=submit]').click();await page.locator('#editor').waitFor({state:'hidden'});
  await page.getByText('테스트 공유지분',{exact:true}).waitFor();await mirror.getByText('테스트 공유지분',{exact:true}).waitFor({timeout:20000});await mirror.reload();await mirror.locator('#enter-cockpit').click();await mirror.locator('nav [data-page=asset]').click();await mirror.getByText('테스트 공유지분',{exact:true}).waitFor();await mirror.close();
  await page.locator('nav [data-page=case]').click();await page.locator('[data-new=case]').click();
  await page.locator('#record-form [name=title]').fill('테스트 경매');await page.locator('[name=number]').fill('2026타경00000');
  await page.locator('[name=court]').fill('가상법원');await page.locator('[name=claim_id]').selectOption({label:'테스트 담보채권'});
  await page.locator('[name=asset_id]').selectOption({label:'테스트 공유지분'});
  await page.locator('[name=auction_date]').fill('2026-11-20');await page.locator('[name=minimum]').fill('90000000');
  await page.locator('#record-form button[type=submit]').click();await page.locator('#editor').waitFor({state:'hidden'});
  await page.locator('nav [data-page=task]').click();await page.getByText('직접 입찰·공유자 우선매수 검토',{exact:true}).waitFor();
  await page.locator('nav [data-page=analysis]').click();await page.locator('#analysis-case').selectOption({label:'테스트 경매'});
  await page.waitForFunction(()=>Number(document.querySelector('#scenario-form [name=claim]').value)>0);
  await page.locator('#scenario-form [name=resale]').fill('130000000');await page.locator('#scenario-form button').click();
  await page.locator('#scenario-result strong').first().waitFor();
  assert.match(await page.locator('#scenario-result').textContent(),/배당 추정/);
  await page.locator('#preemption-form [name=coowner_verified]').check();await page.locator('#preemption-form [name=other_share_verified]').check();
  await page.locator('#preemption-form button').click();await page.locator('#preemption-result').getByText(/우선매수 검토 대상/).waitFor();
  await page.locator('nav [data-page=case]').click();await page.locator('[data-view]').first().click();
  await page.locator('#upload').setInputFiles({name:'proof.txt',mimeType:'text/plain',buffer:Buffer.from('가상 증빙')});await page.locator('#upload-btn').click();
  await page.locator('#detail-content a').filter({hasText:'proof.txt'}).waitFor();await page.locator('#close-detail').click();
  await page.locator('nav [data-page=filing]').click();await page.locator('#new-filing').click();
  await page.locator('#filing-form [name=form_kind]').selectOption('statement');
  await page.locator('#filing-form [name=creditor]').fill('가상 채권자');await page.locator('#filing-form [name=creditor_address]').fill('가상 주소 1');
  await page.locator('#filing-form [name=phone]').fill('연락처 검증용');await page.locator('#filing-form [name=debtor_address]').fill('가상 주소 2');
  await page.locator('#filing-form [name=amount]').fill('99990000');await page.locator('#filing-form [name=breakdown]').fill('원금 99,990,000원. 이자 없음. 검증용 가상 자료.');
  await page.locator('#filing-form [name=basis]').fill('가상 대여 계약');await page.locator('#filing-form [name=attachments]').fill('가상 대여 계약서\n가상 등기사항증명서');
  await page.locator('[data-check]').evaluateAll(els=>els.forEach(el=>el.checked=true));await page.locator('#approve-filing').click();
  await page.getByText('출력준비',{exact:true}).last().waitFor();
  const printHref=await page.getByRole('link',{name:'A4 출력 미리보기 / PDF 저장',exact:true}).getAttribute('href');
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
    const st=await (await fetch('/api/state')).json();let caseRecord=st.records.find(r=>r.kind==='case'&&r.payload.type==='share');
    const post=async (route,body)=>{const r=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':st.csrf},body:JSON.stringify(body)});const v=await r.json();if(!r.ok)throw Error(v.error);return v;};
    if(kind==='petition'){
     const asset=await post('record',{kind:'asset',payload:{title:'가상 근저당 자산',address:'가상시 가상동 1','ownership':'근저당'}});
     caseRecord={id:(await post('record',{kind:'case',payload:{title:'가상 임의경매 서식 검증','stage':'집행준비',type:'whole',asset_id:asset.id}})).id};
    }
    const data=Object.fromEntries(st.forms[kind].fields.map(f=>[f.key,'가상 검증 자료']));
    Object.assign(data,{signed_date:'2026-10-01',order_date:'2026-10-01',number:'2026타경00000',amount:'1000000',price:'2000000',dividend:'1000000',creditor:'가상 채권자',court:'가상 지방법원',attachments:'가상 계약서 1부\n가상 등기사항증명서 1부',property:'가상 토지: 가상시 가상구 가상동 1-1\n지목: 대, 면적: 100㎡\n실행 대상: 가상 채무자의 10분의 9 지분'});
    const rr=await fetch('/api/filing',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':st.csrf},body:JSON.stringify({action:'save',case_id:caseRecord.id,form_kind:kind,data})});const saved=await rr.json();
    if(!rr.ok)throw Error(saved.error);
    await post('filing',{action:'approve',id:saved.id,version:1,checks:Object.fromEntries(Object.keys(st.forms[kind].checks).map(k=>[k,true]))});
    return '/api/print/'+saved.id;
   },kind);
   const preview=await page.context().newPage();await preview.goto('http://127.0.0.1:8092'+printHtml);
   await preview.pdf({path:'test-results/'+kind+'.pdf',format:'A4',preferCSSPageSize:true});await preview.close();
  }
  await page.locator('nav [data-page=dashboard]').click();
  assert.equal(await page.locator('.brand-logo').evaluate(img=>img.complete&&img.naturalWidth>0),true,'brand logo loads');
  const animationFrames=await page.locator('.brand-logo').evaluate(img=>{const animations=img.getAnimations();const sample=t=>{animations.forEach(a=>{a.pause();a.currentTime=t});const s=getComputedStyle(img);return {transform:s.transform,filter:s.filter}};const start=sample(0),later=sample(3000);animations.forEach(a=>a.play());return {count:animations.length,start,later}});
  assert.equal(animationFrames.count,2,'logo motion and colour animations');assert.notEqual(animationFrames.start.transform,animationFrames.later.transform,'logo moves');assert.notEqual(animationFrames.start.filter,animationFrames.later.filter,'logo colour changes');
  await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await page.locator('.brand-logo').evaluate(img=>getComputedStyle(img).animationName),'none','reduced motion disables animation');await page.emulateMedia({reducedMotion:'no-preference'});

  for(const selector of ['.annunciator[data-filter=overdue]','.annunciator[data-filter=today]','.annunciator[data-filter=pending]','.annunciator[data-page=event]','.instrument[data-page=task]','.instrument[data-page=claim]','.instrument[data-page=case]','.command-strip [data-page=filing]','.command-strip [data-page=analysis]','.command-strip [data-page=audit]','.connector [data-page=filing]','.connector [data-page=asset]','.connector [data-page=audit]']){
   await page.locator('#content '+selector).first().click();assert.equal(await page.locator('#content').textContent().then(x=>x.length>0),true,'linked page renders: '+selector);await page.locator('nav [data-page=dashboard]').click();
  }
  for(const kind of ['asset','claim','case']){await page.locator('.command-strip [data-new='+kind+']').click();await page.locator('#editor').waitFor({state:'visible'});await page.locator('#close-editor').click();}
  await page.locator('#toast').waitFor({state:'hidden'});fs.mkdirSync('test-results',{recursive:true});await page.screenshot({path:'test-results/desktop.png',fullPage:true});
  await page.locator('nav [data-page=tax]').click();await page.locator('[data-new=tax]').click();
  await page.locator('#record-form [name=title]').fill('테스트 세금 고지');await page.locator('#record-form [name=status]').selectOption('고지확인');await page.locator('#record-form [name=amount]').fill('10000');await page.locator('#record-form [name=paid]').fill('0');await page.locator('#record-form button[type=submit]').click();await page.locator('#editor').waitFor({state:'hidden'});await page.getByText('테스트 세금 고지',{exact:true}).waitFor();await page.locator('nav [data-page=task]').click();assert.equal(await page.getByText('확인된 세금 납부기한 · 테스트 세금 고지',{exact:true}).count(),0,'unverified tax must not create notification');await page.locator('nav [data-page=dashboard]').click();
  for(const size of [{width:320,height:740},{width:390,height:844},{width:700,height:900},{width:844,height:390}]){
   await page.setViewportSize(size);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'dashboard overflow '+size.width);
  }
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.locator('#logout').isVisible(),true,'mobile logout remains reachable');
  assert.equal(await page.locator('#logout').evaluate(b=>b.getBoundingClientRect().height>=44),true,'mobile touch target');
  await page.screenshot({path:'test-results/mobile.png',fullPage:true});
  await page.locator('nav [data-page=claim]').click();
  assert.equal(await page.locator('.records-table td').first().getAttribute('data-label'),'자료명','record card labels');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'record cards overflow');
  await page.screenshot({path:'test-results/mobile-records.png',fullPage:true});
  await page.locator('[data-new=claim]').click();
  assert.equal(await page.locator('#editor input[name=principal]').evaluate(i=>getComputedStyle(i).fontSize),'16px','mobile input avoids focus zoom');
  assert.equal(await page.locator('#editor').evaluate(d=>d.scrollWidth<=d.clientWidth),true,'mobile form overflow');
  await page.screenshot({path:'test-results/mobile-form.png',fullPage:true});await page.locator('#close-editor').click();
  await page.locator('nav [data-page=filing]').click();await page.locator('#new-filing').click();
  assert.equal(await page.locator('#paperwork').evaluate(d=>d.scrollWidth<=d.clientWidth),true,'mobile filing overflow');await page.locator('#close-paperwork').click();
  await page.locator('nav [data-page=dashboard]').click();
  await page.locator('#home').click();await page.locator('#start').waitFor({state:'visible'});assert.equal(await page.locator('#shell').isVisible(),false);await page.locator('#enter-cockpit').click();await page.locator('#shell').waitFor({state:'visible'});assert.deepEqual(errors,[],'browser runtime errors');
  console.log('Browser workflow passed: account, claim, case, generated task, analysis, preemption, evidence, responsive layout.');
 } catch(e) {if(page){fs.mkdirSync('test-results',{recursive:true});await page.screenshot({path:'test-results/failure.png',fullPage:true});console.error(await page.locator('#toast').textContent());}throw e;}
 finally {if(browser)await browser.close();server.kill();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
