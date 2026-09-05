'use strict';const assert=require('node:assert/strict'),handler=require('../api/work-design-ai.js'),E=require('../work-design/engine.js');let count=0,calls=[];
const envKeys=['OPENAI_API_KEY','WORK_DESIGN_ACCESS_CODE','WORK_DESIGN_ALLOWED_ORIGIN','UPSTASH_REDIS_REST_URL','UPSTASH_REDIS_REST_TOKEN'];for(const k of envKeys)delete process.env[k];
const cfg=()=>Object.assign(process.env,{OPENAI_API_KEY:'test-openai-not-a-real-key',WORK_DESIGN_ACCESS_CODE:'test-access-code-32-characters-000',WORK_DESIGN_ALLOWED_ORIGIN:'https://example.test',UPSTASH_REDIS_REST_URL:'https://test.upstash.io',UPSTASH_REDIS_REST_TOKEN:'test-redis-not-a-real-token'});
function req(){const s=E.sample();return {method:'POST',headers:{origin:'https://example.test',authorization:'Bearer test-access-code-32-characters-000','content-type':'application/json','x-request-id':'test-request-123456789'},body:{concern:s.concern,tasks:s.tasks,consent:true}};}
async function run(r){let result={headers:{}};const res={setHeader(k,v){result.headers[k]=v;return res},status(v){result.status=v;return res},json(v){result.body=v;return res}};await handler(r,res);return result;}
const result=(items=[{id:'t3',strategy:'ai',rationale:'整理を支援する',experiment:'10件で試す',verify:'責任者が確認'}])=>({status:'completed',output:[{type:'message',content:[{type:'output_text',text:JSON.stringify({takeaway:'仕事から見直す',items,questions:['実測時間は？']})}]}]});
function mock(quota=1,output=result(),ok=true){calls=[];global.fetch=async(url,options)=>{calls.push({url,options});return {ok:url.includes('upstash')?true:ok,json:async()=>url.includes('upstash')?{result:quota}:output};};}
const test=async(name,fn)=>{await fn();count++;};
(async()=>{
 await test('disabled status',async()=>{mock();let r=await run({method:'GET',headers:{}});assert.equal(r.body.enabled,false);assert.equal(calls.length,0)});
 await test('disabled POST fails closed',async()=>{mock();let r=await run(req());assert.equal(r.status,503);assert.equal(calls.length,0)});
 cfg();
 await test('configured status',async()=>{let r=await run({method:'GET',headers:{}});assert.equal(r.body.enabled,true)});
 await test('unsupported method',async()=>{let r=await run({method:'PUT',headers:{}});assert.equal(r.status,405)});
 await test('origin check',async()=>{mock();let q=req();q.headers.origin='https://other.test';assert.equal((await run(q)).status,403);assert.equal(calls.length,0)});
 await test('auth check',async()=>{mock();let q=req();q.headers.authorization='Bearer incorrect';assert.equal((await run(q)).status,401);assert.equal(calls.length,0)});
 await test('missing auth',async()=>{let q=req();delete q.headers.authorization;assert.equal((await run(q)).status,401)});
 await test('consent check',async()=>{mock();let q=req();q.body.consent=false;assert.equal((await run(q)).status,400);assert.equal(calls.length,0)});
 await test('content type',async()=>{let q=req();q.headers['content-type']='text/plain';assert.equal((await run(q)).status,415)});
 await test('oversize',async()=>{mock();let q=req();q.body.concern='あ'.repeat(9000);assert.equal((await run(q)).status,413);assert.equal(calls.length,0)});
 await test('NaN rejected',async()=>{let q=req();q.body.tasks[0].minutes=NaN;assert.equal((await run(q)).status,400)});
 await test('idempotency header required',async()=>{let q=req();delete q.headers['x-request-id'];assert.equal((await run(q)).status,400)});
 await test('duplicate task id',async()=>{let q=req();q.body.tasks[1].id='t1';assert.equal((await run(q)).status,400)});
 await test('quota stops before model',async()=>{mock(-1);assert.equal((await run(req())).status,429);assert.equal(calls.length,1)});
 await test('duplicate request stops',async()=>{mock(-3);assert.equal((await run(req())).status,409);assert.equal(calls.length,1)});
 await test('counter offline fails closed',async()=>{calls=[];global.fetch=async()=>{throw Error('down')};assert.equal((await run(req())).status,503)});
 await test('successful structured output',async()=>{mock();let r=await run(req());assert.equal(r.status,200);assert.equal(r.body.mode,'live');assert.equal(calls.length,2);let payload=JSON.parse(calls[1].options.body);assert.equal(payload.store,false);assert.equal(payload.max_output_tokens,4000);assert.equal(payload.text.format.strict,true);assert.equal(payload.tools,undefined);assert.equal(JSON.parse(payload.input).tasks[0].why,undefined)});
 await test('private extra fields stripped',async()=>{mock();let q=req();q.body.private='SECRET';q.body.workers=[{name:'PERSON'}];q.body.tasks[0].private='SECRET';await run(q);assert.ok(!calls[1].options.body.includes('SECRET'));assert.ok(!calls[1].options.body.includes('PERSON'))});
 await test('unsafe AI onsite prevented',async()=>{mock(1,result([{id:'t1',strategy:'ai',rationale:'bad',experiment:'bad',verify:'bad'}]));let r=await run(req());assert.equal(r.status,200);assert.equal(r.body.result.items[0].strategy,'hire')});
 await test('unknown output id rejected',async()=>{mock(1,result([{id:'unknown',strategy:'ai',rationale:'x',experiment:'x',verify:'x'}]));assert.equal((await run(req())).status,502)});
 await test('unknown strategy rejected',async()=>{mock(1,result([{id:'t3',strategy:'fire',rationale:'x',experiment:'x',verify:'x'}]));assert.equal((await run(req())).status,502)});
 await test('upstream error not fake success',async()=>{mock(1,{},false);assert.equal((await run(req())).status,502)});
 await test('incomplete rejected',async()=>{mock(1,{status:'incomplete'});assert.equal((await run(req())).status,502)});
 await test('invalid JSON rejected',async()=>{mock(1,{status:'completed',output:[{content:[{type:'output_text',text:'not json'}]}]});assert.equal((await run(req())).status,502)});
 await test('no secret in response',async()=>{mock();let r=await run(req());assert.ok(!JSON.stringify(r).includes(process.env.OPENAI_API_KEY));assert.equal(r.headers['Cache-Control'],'no-store')});
 for(const k of envKeys)delete process.env[k];console.log(JSON.stringify({suite:'api with network stubs',passed:count,failed:0}));
})().catch(e=>{console.error(e);process.exit(1)});
