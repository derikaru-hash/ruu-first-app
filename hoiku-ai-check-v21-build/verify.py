"""Verify the demo locally before publication and again over public HTTPS."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import argparse, hashlib, json, os, threading, time, urllib.request, traceback

args = argparse.ArgumentParser()
args.add_argument('--local', action='store_true')
args.add_argument('--public', action='store_true')
mode = args.parse_args()
assert mode.local != mode.public
OUT = Path('/tmp/hoiku-v21')
OUT.mkdir(parents=True, exist_ok=True)
manifest = json.loads((OUT/'release/manifest.json').read_text())
expected = manifest['sha256']
server = None
scope = 'public' if mode.public else 'local'
if mode.local:
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(Path.cwd())))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/hoiku-ai-check/'
else:
    url = manifest['public_url']
    report = {'url':url, 'verified':False, 'expected_sha256':expected}
    for attempt in range(36):
        try:
            req = urllib.request.Request(url+'?release='+expected[:16], headers={'User-Agent':'L-CREW-Revision-Verification/2.1'})
            with urllib.request.urlopen(req, timeout=15) as res:
                body = res.read()
                report.update(status=res.status, final_url=res.url, sha256=hashlib.sha256(body).hexdigest())
            if report['status']==200 and report['sha256']==expected:
                report['verified']=True
                break
        except Exception as exc:
            report['error']=str(exc)[:250]
        time.sleep(5)
    (OUT/'public-http-verification.json').write_text(json.dumps(report, indent=2))
    assert report['verified'], 'Published HTML not verified; no authenticated bypass is used'

checks=[]
succeeded=False
def ck(name, condition):
    checks.append({'name':name, 'passed':bool(condition)})
    assert condition, name

def action(p, name):
    p.locator('[data-action="'+name+'"]:visible').first.click()
    p.wait_for_timeout(45)

def route(p, name):
    p.evaluate('(r)=>location.hash=r', name)
    p.wait_for_timeout(60)

try:
    regression_out = OUT/(scope+'-regression')
    regression_out.mkdir(exist_ok=True)
    os.environ['HOIKU_VERIFY_OUT']=str(regression_out)
    prior = Path('hoiku-ai-check-v2-build/public-smoke.py').read_text()
    prior = prior.replace("URL='https://ruu-first-app.vercel.app/hoiku-ai-check/'", 'URL='+repr(url))
    prior = prior.replace("json.loads(Path('hoiku-ai-check-v2-build/publish.json').read_text())['sha256']", repr(expected))
    prior = prior.replace("'2.0.0'", "'2.1.0'").replace('app version is 2.0.0', 'app version is 2.1.0')
    prior = prior.replace('b=pw.chromium.launch(headless=True)', "b=pw.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None,args=['--no-sandbox'])")
    prior = prior.replace("   for k,v in {'minutes'", "   p.locator('#a-'+t+'-minutes').locator('xpath=ancestor::details').locator('summary').click()\n   for k,v in {'minutes'")
    exec(compile(prior,'reviewed-v2-regression','exec'), {'__name__':'__main__'})
    checks.extend(json.loads((regression_out/'browser-verification.json').read_text())['checks'])
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None,args=['--no-sandbox'])
        ctx=b.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        p=ctx.new_page(); errors=[]; transmissions=[]
        p.on('pageerror', lambda e:errors.append(str(e)))
        p.on('request', lambda r:transmissions.append(r.url) if r.resource_type in ['xhr','fetch'] else None)
        response=p.goto(url,wait_until='networkidle')
        ck('revision response matches tested artifact', hashlib.sha256(response.body()).hexdigest()==expected)
        unit=p.evaluate(r'''() => {
          const t=HoikuDemoTest,base={minutes:'120',burden:'3',mode:'paper',owner:'one',hope:'yes'},tests=[];
          const add=(name,passed)=>tests.push({name,passed:!!passed});
          add('ordinary writing may use AI',t.classify('comm',base,'people').cat==='ai');
          let x=t.classify('comm',{...base,hope:'no'},'people');
          add('do-not-change preference defers ordinary work',x.cat==='keep'&&x.deferred&&x.priority==='later');
          add('defer is not stated as proof of no improvement need',x.reason.includes('不要だと断定する判定ではありません'));
          x=t.classify('comm',{...base,mode:'unknown'},'people');
          add('unknown current method does not recommend AI',x.unknown&&x.cat==='keep');
          add('unknown burden remains unconfirmed',t.classify('comm',{...base,burden:'unknown'},'people').unknown);
          add('safety remains human even when improvement declined',t.classify('safety',{...base,hope:'no'},'people').cat==='human');
          add('double input favors existing tools',t.classify('comm',{...base,mode:'double'},'people').cat==='ict');
          add('no burden keeps current workflow',t.classify('comm',{...base,burden:'0'},'people').cat==='keep');
          add('sensitive records require expert checks',t.classify('record',base,'people').route==='expert');
          let r=t.sampleRecord(); r.selected=['comm'];r.answers={comm:{...base}};r.decisions={};
          add('time evidence used when actually entered',t.evaluate(r).eligibleMinutes===120);
          r.decisions.comm='skip';x=t.evaluate(r);
          add('declined item removed from top suggestions and time scenario',x.top.length===0&&x.eligibleMinutes===0&&x.deferred===1);
          r.decisions.comm='hold';add('held item removed from time scenario',t.evaluate(r).eligibleMinutes===0);
          r.decisions.comm='adopt';add('adoption restores eligible time',t.evaluate(r).eligibleMinutes===120);
          r.answers.comm.minutes='unknown';add('missing time is not counted as known zero',t.evaluate(r).eligibleKnownCount===0);
          r.answers.comm.hope='no';add('initial improvement preference excludes candidate',t.evaluate(r).top.length===0);
          r=t.sampleRecord();r.selected=[];add('no concerns never creates three fake suggestions',t.evaluate(r).top.length===0);
          add('suggestions are capped at three',t.evaluate(t.sampleRecord()).top.length<=3);
          const before=t.sampleRecord(),after=JSON.parse(JSON.stringify(before)); after.ruleVersion='another-rule';after.answers.comm.minutes='60';
          x=t.compareRecords(before,after);add('cross-version comparison is raw time only and marked',x.valid&&x.ruleChanged&&x.delta===60);
          after.role='staff';add('different roles not falsely compared',!t.compareRecords(before,after).valid);
          const csv=t.csvText([['=1+1','@test']]);add('CSV formula prefixes remain neutralized',csv.includes("'=1+1")&&csv.includes("'@test"));
          return tests;
        }''')
        for item in unit: ck(item['name'], item['passed'])
        action(p,'start')
        ck('AI and ICT explanation visible before questions',p.get_by_text('はじめに、AIとICTの違い。').is_visible())
        ck('initial diagnosis has no contact fields',p.locator('#contact-name,#contact-company,#contact-email').count()==0)
        p.locator('#industry').select_option('food');p.locator('#role').select_option('staff');action(p,'next')
        ck('industry-specific task wording',p.get_by_text('お店のお知らせ・販促文',exact=True).is_visible())
        ck('role-specific question wording','向き合う時間を圧迫' in p.locator('#view').inner_text())
        for task in ['comm','billing','safety']:p.locator('input[name="tasks"][value="'+task+'"]').check()
        action(p,'next')
        ck('three primary visible fields per selected job',p.locator('.taskedit select:visible').count()==9)
        ck('optional detailed questions collapsed initially',p.locator('.optional-questions[open]').count()==0)
        p.screenshot(path=str(OUT/(scope+'-quick-diagnosis-desktop.png')),full_page=True)
        for task in ['comm','billing','safety']:
            p.locator('#a-'+task+'-burden').select_option('2')
            p.locator('#a-'+task+'-mode').select_option('paper')
            p.locator('#a-'+task+'-hope').select_option('no' if task=='billing' else 'yes')
        action(p,'next');p.locator('input[name="goal"][value="people"]').check();action(p,'next');action(p,'next')
        ck('diagnosis completes without optional time and owner',p.locator('.summaryhero').count()==1)
        ck('missing time visibly uncalculated','未計算' in p.locator('#gainValue').inner_text())
        p.locator('#ratio').evaluate("el=>{el.value='40';el.dispatchEvent(new Event('input',{bubbles:true}))}")
        ck('moving scenario does not fabricate missing time','未計算' in p.locator('#gainValue').inner_text())
        ck('no save without explicit choice',p.evaluate("localStorage.getItem('ruu.hoiku-check.v2')") is None)
        ck('three next-step routes on result screen',p.locator('#next-steps .next-route').count()==3)
        ck('declined billing not a top candidate',not p.locator('.priorities').get_by_text('売上・仕入・在庫の集計',exact=True).count())
        p.screenshot(path=str(OUT/(scope+'-result-desktop.png')),full_page=True)
        p.locator('[data-action="consult-kind"][data-kind="proposal"]').click()
        ck('detailed proposal button selects intended consultation',p.locator('#contact-kind').input_value()=='proposal')
        ck('consultation clearly remains an unsent demo','デモ' in p.locator('#view').inner_text())
        route(p,'home');action(p,'start');p.locator('#role').select_option('office');action(p,'next');p.locator('#noConcern').check();action(p,'next')
        ck('no-concern path skips burden screen',p.locator('input[name="goal"]').count()==5)
        action(p,'back');ck('back button returns to task choices after skip',p.locator('#noConcern').is_checked())
        action(p,'next');p.locator('input[name="goal"][value="rest"]').check();action(p,'next');action(p,'next')
        ck('no-concern result gives no artificial tasks','無理に変えなくて大丈夫' in p.locator('.summaryhero').inner_text())
        for width in [390,820,1440]:
            p.set_viewport_size({'width':width,'height':900})
            for name in ['home','results','team','plan','measure','consult','admin']:
                route(p,name)
                ck(f'no horizontal overflow {width}px {name}',p.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1'))
            route(p,'home');action(p,'start');p.locator('#role').select_option('manager');action(p,'next');p.locator('input[name="tasks"][value="comm"]').check();action(p,'next')
            ck(f'quick form fits at {width}px',p.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1'))
            if width==390:p.screenshot(path=str(OUT/(scope+'-quick-diagnosis-mobile.png')),full_page=True)
        ck('no JavaScript exceptions in additional tests',not errors)
        ck('no diagnosis or consultation API transmissions',not transmissions)
        ctx.close();b.close()
    succeeded=True
except Exception:
    (OUT/(scope+'-failure.txt')).write_text(traceback.format_exc())
    raise
finally:
    if not succeeded:checks.append({'name':'verification completed without an exception','passed':False})
    if server:server.shutdown()
    report={'version':'2.1.0','scope':scope,'url':url,'sha256':expected,'checks':checks,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'limitations':['Chromium only; not physical Safari/iPhone/iPad testing','Frontend demo only; no shared server, live consultation submission, or AI API','Human completion time and real improvement outcomes not measured']}
    (OUT/(scope+'-verification.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'scope':scope,'passed':report['passed'],'failed':report['failed']},ensure_ascii=False))
