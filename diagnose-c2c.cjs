// Read-only inspection plus OAuth tests in a separate temporary local server.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');
const crypto = require('node:crypto');
const repo = path.resolve(process.argv[2] || path.join(os.homedir(), 'codex-with-chatgpt'));
const lines = [];
function log(s) { lines.push(s); console.log(s); }
function block(text, term, before=3, after=7) {
 const a=text.split(/\r?\n/), i=a.findIndex(x=>x.includes(term));
 return i < 0 ? '(not found)' : a.slice(Math.max(0,i-before),i+after+1).join('\n');
}
async function main() {
 log('C2C OAuth diagnostic (no live pairing/token changes)');
 log('Node: '+process.version+' | time: '+new Date().toISOString());
 const pkg=JSON.parse(fs.readFileSync(path.join(repo,'package.json'),'utf8'));
 log('Package: '+pkg.version);
 for (const rel of ['src/auth/oauth.ts','dist/auth/oauth.js']) {
  const file=path.join(repo,rel), text=fs.readFileSync(file,'utf8');
  log('\nFILE '+rel+' | modified '+fs.statSync(file).mtime.toISOString());
  log('sha256: '+crypto.createHash('sha256').update(text).digest('hex'));
  for (const term of ['name="request_id"','const pendingRequests','const request = body.request_id']) log(block(text,term));
 }
 const stateDir=process.env.C2C_STATE_DIR || path.join(process.env.LOCALAPPDATA || path.join(os.homedir(),'AppData','Local'),'codex-with-chatgpt');
 const runtimeDir=path.join(stateDir,'runtime');
 if (fs.existsSync(runtimeDir)) {
  for (const name of fs.readdirSync(runtimeDir).filter(x=>x.endsWith('.json'))) {
   try {
    const r=JSON.parse(fs.readFileSync(path.join(runtimeDir,name),'utf8'));
    log('\nRuntime (selected non-secret fields): '+JSON.stringify({pid:r.pid,port:r.port,startedAt:r.startedAt,publicUrl:r.publicUrl}));
   } catch {}
  }
 }
 const logsDir=path.join(stateDir,'logs');
 if(fs.existsSync(logsDir)) {
  const names=fs.readdirSync(logsDir).filter(n=>n.endsWith('.log')).sort((a,b)=>fs.statSync(path.join(logsDir,b)).mtimeMs-fs.statSync(path.join(logsDir,a)).mtimeMs).slice(0,2);
  for(const name of names) {
   const a=fs.readFileSync(path.join(logsDir,name),'utf8').split(/\r?\n/);
   log('\nRecent lifecycle events:');
   for(const line of a.filter(x=>/Bridge listening|Created pairing session|Pairing verification failed|Pairing verified;|Issued access token|Registered OAuth client/.test(x)).slice(-20)) {
    // Report only event types; never copy credentials or arbitrary log content.
    const event=line.match(/Bridge listening|Created pairing session|Pairing verification failed|Pairing verified;|Issued access token|Registered OAuth client/)[0];
    log(event);
   }
  }
 }
 const req=createRequire(path.join(repo,'package.json'));
 const express=req('express');
 const {createOAuthRouter}=await import(pathToFileURL(path.join(repo,'dist/auth/oauth.js')).href);
 const app=express();
 const mockClient={clientId:'isolated-test-client',redirectUris:['https://example.invalid/callback']};
 let issued=0;
 app.use(createOAuthRouter({
  store:{getClient:id=>id===mockClient.clientId?mockClient:undefined,createAuthorizationCode:()=>{issued++;return 'isolated-test-code';}},
  pairing:{verify:code=>code==='TEST-CODE'?{ok:true,sessionId:'isolated-test-session'}:{ok:false,reason:'invalid',attemptsLeft:5}},
  workspaceName:'isolated-test',getBaseUrl:()=> 'http://127.0.0.1',logger:{info(){},warn(){},error(){}}
 }));
 const server=await new Promise(resolve=>{const s=app.listen(0,'127.0.0.1',()=>resolve(s));});
 const base='http://127.0.0.1:'+server.address().port;
 function assert(ok,label){if(!ok)throw new Error('FAIL: '+label);log('PASS: '+label);}
 async function form(){
  const q=new URLSearchParams({client_id:mockClient.clientId,redirect_uri:mockClient.redirectUris[0],response_type:'code',code_challenge:'a'.repeat(43),code_challenge_method:'S256',scope:'workspace.read',state:'isolated-test-state'});
  const r=await fetch(base+'/oauth/authorize?'+q);const html=await r.text();
  assert(r.status===200,'GET authorization page');
  const m=html.match(/name="request_id"\s+value="([^"]+)"/);assert(!!m,'hidden request_id is present');return m[1];
 }
 async function post(id,code='TEST-CODE'){
  const data={pairing_code:code};if(id!==null)data.request_id=id;
  const r=await fetch(base+'/oauth/authorize',{method:'POST',body:new URLSearchParams(data),redirect:'manual'});
  return {status:r.status,text:await r.text(),location:r.headers.get('location')};
 }
 try{
  log('\nIsolated tests of YOUR installed dist/auth/oauth.js:');
  const first=await form(), second=await form();
  assert(first!==second,'two requests have different IDs');
  assert((await post(first,'BAD-CODE')).status===401,'wrong pairing code reaches verification');
  const good=await post(first);
  assert(good.status===302 && new URL(good.location).searchParams.get('state')==='isolated-test-state','retry with correct code redirects with OAuth state');
  assert((await post(first)).status===400,'replayed request is rejected');
  assert((await post(second)).status===302,'second pending request remains valid');
  assert((await post(null)).status===400,'missing request_id is rejected');
  assert((await post('unknown')).status===400,'unknown request_id is rejected');
  assert(issued===2,'only valid requests issue codes');
  log('\nRESULT: isolated flow passed. Live failure requires request payload/lifecycle evidence; expiry alone is not proven.');
 }finally{await new Promise(resolve=>server.close(resolve));}
}
main().catch(e=>{log('ERROR: '+e.message);process.exitCode=1;}).finally(()=>{
 const report=path.join(__dirname,'c2c-diagnostic-report.txt');
 fs.writeFileSync(report,lines.join('\n')+'\n','utf8');console.log('\nReport saved: '+report);
});
