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
  await page.locator('#record-form button[type=submit]').click();await page.locator('#editor').waitFor({state:'hidden'});
  await page.getByText('테스트 담보채권',{exact:true}).waitFor();
  await page.locator('[data-page=case]').click();await page.locator('[data-new=case]').click();
  await page.locator('#record-form [name=title]').fill('테스트 경매');await page.locator('[name=number]').fill('2026타경00000');
  await page.locator('[name=court]').fill('가상법원');await page.locator('[name=claim_id]').selectOption({label:'테스트 담보채권'});
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
  await page.locator('[data-page=dashboard]').click();fs.mkdirSync('test-results',{recursive:true});await page.screenshot({path:'test-results/desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'test-results/mobile.png',fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'mobile horizontal overflow');
  assert.deepEqual(errors,[],'browser runtime errors');
  console.log('Browser workflow passed: account, claim, case, generated task, analysis, preemption, evidence, responsive layout.');
 } catch(e) {if(page){fs.mkdirSync('test-results',{recursive:true});await page.screenshot({path:'test-results/failure.png',fullPage:true});console.error(await page.locator('#toast').textContent());}throw e;}
 finally {if(browser)await browser.close();server.kill();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
