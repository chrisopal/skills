/* Uses the host's existing Playwright installation; never downloads dependencies.
 * PLAYWRIGHT_MODULE=/absolute/node_modules/playwright node tests/run-huixin-browser.cjs URL OUTPUT_DIR
 */
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
 const url=process.argv[2],output=process.argv[3];
 if(!url||!output)throw Error('Provide reference URL and absolute artifact output directory');
 if(!path.isAbsolute(output))throw Error('Output must be absolute');
 const target=new URL(url);
 if(!['127.0.0.1','localhost'].includes(target.hostname)||!target.pathname.endsWith('/assets/reference-huixin/'))throw Error('Only the isolated local reference URL is supported');
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL || 'chrome',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  await context.addInitScript(value=>{window.__HUIXIN_EVIDENCE_DIR__=value;},output);
  const page=await context.newPage();await page.goto(url);
  const run=vm.runInThisContext('('+fs.readFileSync(path.join(__dirname,'huixin-browser-check.js'),'utf8')+'\n)');
  const result=await run(page);result.browser=browser.version();
  if(result.status==='PASS'){
   try {const runtimeCheck=vm.runInThisContext('('+fs.readFileSync(path.join(__dirname,'huixin-runtime-check.js'),'utf8')+'\n)');result.runtime=await runtimeCheck(page);}
   catch(error){result.status='FAIL';result.error='Provider integration: '+error.message;}
  }
  fs.writeFileSync(path.join(output,'browser-result.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({status:result.status,error:result.error,assertions:result.assertions,runtimeAssertions:result.runtime?.assertions,controls:Object.keys(result.observations||{}).length,matrix:result.matrix.length,browser:result.browser,errors:result.errors}));
  if(result.status!=='PASS')process.exitCode=1;
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
