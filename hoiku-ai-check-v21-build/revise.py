"""Scoped, fail-closed revision of the existing L CREW demonstration app."""
from pathlib import Path
import base64, hashlib, json, re, subprocess

TARGET = Path('hoiku-ai-check/index.html')
BASE_SHA = '64e470453de3dc51f1ca35b059387b5d8a08efd8a433c95ebed99576ead08152'
OUT = Path('/tmp/hoiku-v21/release')
OUT.mkdir(parents=True, exist_ok=True)
raw = TARGET.read_bytes()
html = raw.decode('utf-8')
already = "const VERSION='2.1.0'" in html
if not already:
    assert hashlib.sha256(raw).hexdigest() == BASE_SHA, 'Unexpected source revision; refusing to overwrite'

def replace(old, new, count=1):
    global html
    assert html.count(old) == count, f'Patch anchor mismatch: {old[:100]}'
    html = html.replace(old, new)

def function(name, next_name, new):
    global html
    start = html.index('function '+name+'(')
    end = html.index('function '+next_name+'(', start)
    html = html[:start] + new.strip() + '\n' + html[end:]

if not already:
    replace("const VERSION='2.0.0', RULE_VERSION='2026-09-demo-2'", "const VERSION='2.1.0', RULE_VERSION='2026-09-demo-2.1'")
    replace('DEMO v2.0', 'DEMO v2.1')
    replace('v2.0.0 · 実AI・共有サーバー未接続', 'v2.1.0 · 実AI・共有サーバー未接続')
    replace("short:'今の方法を続ける'", "short:'現状維持・いったん保留'")
    replace('気になる仕事を最大5つ。うまく回っている仕事も選べます。', 'まずは気になる仕事を3つ程度。最大5つまで選べます。うまく回っている仕事も選べます。')
    replace('<details class="p20"><summary class="small muted">AIとICTの違いを、もう一度見る</summary><div class="note p12">AI：文章の下書き・要約などを助けるもの。人の確認が必要です。<br>ICT：記録・計算・共有のための道具。AIもICTに含まれますが、ここでは役割を分けて考えます。</div></details>', '<div class="note p20"><b>はじめに、AIとICTの違い。</b><br>AI：文章の下書き・要約などを助けるもの。最後は人が確認します。<br>ICT：記録・計算・共有の道具。まず、今ある道具でできないかを考えます。<br><span class="muted">AIもICTの一部ですが、この診断では得意な仕事を分けて整理します。</span></div>')
    start = html.index(' if(wstep===3){body=')
    end = html.index(' if(wstep===4)', start)
    html = html[:start] + ''' if(wstep===3){body=`<h2>今の負担と、変えたい気持ちを教えてください。</h2><p class="intro">まずは各業務の3項目だけ。分からないところは、そのままで大丈夫です。<br>時間や担当の偏りは、下の「詳しく答える」から任意で追加できます。</p>${d.selected.length?d.selected.map(id=>{const a=d.answers[id]||unknownAnswer();const more=d.baselineId||a.minutes!=='unknown'||a.owner!=='unknown';return `<div class="taskedit"><div class="taskedit-head"><h3>${esc(taskName(d.industry,id))}</h3><span class="tag outline">あなたの実感で</span></div><div class="taskfields quickfields"><div class="field"><label for="a-${id}-burden">負担は、どれくらい？</label><select id="a-${id}-burden" data-answer="${id}" data-key="burden">${optionList(BURDENS,a.burden)}</select></div><div class="field"><label for="a-${id}-mode">今は、どう進めている？</label><select id="a-${id}-mode" data-answer="${id}" data-key="mode">${optionList(MODES,a.mode)}</select></div><div class="field"><label for="a-${id}-hope">今、改善したい？</label><select id="a-${id}-hope" data-answer="${id}" data-key="hope">${optionList(HOPES,a.hope||'unknown')}</select></div></div><details class="optional-questions" ${more?'open':''}><summary>詳しく答える：時間・担当の偏り（任意）</summary><p class="small muted p12">時間は、あなた1人分・1週間の合計です。確認や修正も含めます。不明は0分として計算しません。</p><div class="taskfields optionfields p12"><div class="field"><label for="a-${id}-minutes">合計の作業時間</label><select id="a-${id}-minutes" data-answer="${id}" data-key="minutes">${optionList({unknown:'まだ分からない',0:'0分（していない）',15:'15分',30:'30分',60:'1時間',120:'2時間',240:'4時間',480:'8時間',960:'16時間'},a.minutes)}</select></div><div class="field"><label for="a-${id}-owner">担当の偏り</label><select id="a-${id}-owner" data-answer="${id}" data-key="owner">${optionList(OWNERS,a.owner)}</select></div></div></details></div>`}).join(''):`<div class="note">困っている仕事がない場合は、この質問を省略できます。</div>`}`;}\n''' + html[end:]
    function('classify','evaluate', r'''function classify(id,a,goal){
 const burden=a.burden==='unknown'?null:Number(a.burden),mins=a.minutes==='unknown'?null:Number(a.minutes);
 let cat='keep',priority='later',reason='',action='',benefit='',route='self',risk=false,unknown=false,deferred=false;
 if(id==='safety'){
  cat='human';priority=burden===0?'later':burden>=2?'now':'next';risk=true;route='expert';
  reason='安全や専門的な判断、相手への影響が大きい仕事です。改善希望にかかわらず、AIへ最終判断を渡しません。';
  action='責任者・専門職への連絡先と、迷ったときに相談する手順をそろえる。';
  benefit='判断する人を孤立させず、対応の抜け漏れを減らすことを目指します。';
 }else if(a.hope==='no'){
  deferred=true;
  reason='「今はそのままでよい」という意向を優先して、着手を保留します。改善が不要だと断定する判定ではありません。'+(burden>=2?' 負担が大きいという回答は残し、必要になったら再検討できます。':'');
  action='今は新しいAIやシステムを増やさない。困りごとや希望が変わったときに、この仕事だけ見直す。';
  benefit='本人の意向を尊重し、望まない変更や学び直しの負担を増やさないことを目指します。';
 }else if(burden===0){
  reason='「困っていない」という回答です。今うまく回っている方法を残します。';
  action='今の手順を続け、担当変更や新たな負担が出たときだけ見直す。';
  benefit='導入の手間を増やさず、必要な仕事に集中できます。';
 }else if(burden===null||a.mode==='unknown'){
  unknown=true;priority='next';
  reason=burden===null?'負担の大きさが未確認のため、導入の判断は保留です。':'今のやり方が未確認のため、AIや新しいシステムが必要とは判断しません。';
  action='まず、今の手順と困った場面を確認する。必要なら1週間だけ作業時間を記録する。';
  benefit='必要のない導入や、見当違いの改善を避ける判断材料になります。';
 }else if(a.mode==='double'||['shift','billing'].includes(id)){
  cat='ict';priority=burden>=2?'now':'next';route='system';
  reason=a.mode==='double'?'二重入力・転記があるため、AI導入より入力先と共有方法の整理を優先します。':'正確な集計や条件確認が中心です。まず既存の道具の設定・連携を確認します。';
  action='正本にする入力先を1つに決め、今ある道具の集計・共有機能を確認する。足りない機能があるときだけ導入を比較。';
  benefit='入力のやり直しや照合を減らし、最新の情報を共有することを目指します。';
 }else if(a.mode==='tool'&&burden<=1&&a.owner!=='one'){
  reason='今のツールで円滑に進み、負担も小さい回答です。置き換えより現状維持を優先します。';
  action='使い方を短い手順に残し、今の道具を継続する。';
  benefit='操作の負担を増やさず、今の良い流れを保ちます。';
 }else{
  cat='ai';risk=['record','handover'].includes(id);priority=risk?'next':burden>=2?'now':'next';route=risk?'expert':'self';
  reason='文章のたたき台や情報整理が中心で、人が内容を確認できる仕事です。'+(a.owner==='one'?' 1人に集中しているため、手順の共有も合わせて検討します。':'');
  action=risk?'個人情報を含まない架空例で、記録・引き継ぎの共通書式を試す。実情報を使う前に送信先・権限・会社のルールを確認。':'伝える事実を箇条書きにし、AIで下書き。担当者が修正し、責任者の確認後に正式版として保存する。';
  benefit='書き始めや整理の負担を減らし、確認と人への関わりに時間を使うことを目指します。';
 }
 const rank=(priority==='now'?100:priority==='next'?40:0)+(burden??0)*10+(a.owner==='one'?8:0)+Math.min((mins??0)/60,8)+(a.hope==='yes'?5:0)+((goal==='team'&&a.owner==='one')?6:0)+((goal==='business'&&['recruit','billing'].includes(id))?5:0);
 return {id,cat,priority,reason,action,benefit,route,risk,unknown,deferred,rank,minutes:mins,burden,mode:a.mode,owner:a.owner,hope:a.hope||'unknown'};
}''')
    function('evaluate','unknownAnswer',r'''function evaluate(rec){
 const items=rec.selected.map(id=>classify(id,rec.answers[id]||unknownAnswer(),rec.goal)).sort((a,b)=>b.rank-a.rank||IDS.indexOf(a.id)-IDS.indexOf(b.id));
 const excluded=x=>x.deferred||['skip','hold'].includes(rec.decisions?.[x.id]);
 const actionable=items.filter(x=>x.cat!=='keep'&&!x.unknown&&x.priority!=='later'&&!excluded(x));
 const known=items.filter(x=>x.minutes!==null),eligible=actionable.filter(x=>['ai','ict'].includes(x.cat)&&x.minutes!==null);
 return {items,actionable,top:actionable.slice(0,3),knownCount:known.length,knownMinutes:known.reduce((s,x)=>s+x.minutes,0),eligibleMinutes:eligible.reduce((s,x)=>s+x.minutes,0),eligibleKnownCount:eligible.length,keep:items.filter(x=>(x.cat==='keep'&&!x.unknown)||excluded(x)).length,unknown:items.filter(x=>x.unknown&&!excluded(x)).length,deferred:items.filter(excluded).length};
}''')
    replace("function resultStateText(e){if(!e.items.length)", "function resultStateText(e){if(e.items.length&&!e.top.length&&e.deferred)return ['今回は、着手を見送る選択です。','保留・不要にした仕事は、改善候補と時間の試算から外しています。負担の回答は残し、希望が変われば見直せます。'];if(!e.items.length)")
    replace('まずは、仕事の負担を確かめるところから。', 'まずは、仕事の状態を確かめるところから。')
    replace('負担が分からない仕事は、測ってから考えます。', '未確認の項目は、今の状態を確かめてから考えます。')
    replace('変えなくてよい仕事</div>', '今は着手しない仕事</div>')
    replace('採否を変えても、元の回答と分類は残します。', '元の回答と分類は残し、改善候補と試算には採否を反映します。')
    replace('<div class="effect-number" id="gainValue">${gain}<span>', '<div class="effect-number" id="gainValue">${e.eligibleKnownCount?gain:\'未計算\'}<span>')
    replace('${fmtMinutes(e.eligibleMinutes)} / 週。', '${fmtMinutes(e.eligibleKnownCount?e.eligibleMinutes:null)} / 週。')
    replace('人の判断・現状維持・時間不明は計算から除外。', '人の判断・現状維持・時間不明・保留・不要は計算から除外。時間を入力していない場合は未計算です。')
    replace("$('#gainValue').innerHTML=Math.round(evaluate(current).eligibleMinutes*ratio/100)+'<span>分 / 週・あなた1人</span>';", "const summary=evaluate(current);$('#gainValue').innerHTML=(summary.eligibleKnownCount?Math.round(summary.eligibleMinutes*ratio/100):'未計算')+'<span>分 / 週・あなた1人</span>';")
    replace("if(wstep<5){wstep++;render();", "if(wstep<5){wstep+=(wstep===2&&draft.noConcern?2:1);render();")
    replace("else{wstep--;render();window.scrollTo(0,0)}", "else{wstep-=(wstep===4&&draft?.noConcern?2:1);render();window.scrollTo(0,0)}")
    replace("const r=copy(draft);r.createdAt=new Date().toISOString();", "const r=copy(draft);r.createdAt=new Date().toISOString();r.ruleVersion=RULE_VERSION;r.version=VERSION;")
    replace("rule:r.ruleVersion,selected:r.selected", "rule:RULE_VERSION,recordRule:r.ruleVersion,selected:r.selected")
    replace("before.industry!==after.industry||before.role!==after.role||before.ruleVersion!==after.ruleVersion", "before.industry!==after.industry||before.role!==after.role")
    replace('業種・立場・判断ルールが異なるため比較しません。', '業種・立場が異なるため比較しません。')
    replace("return {valid:true,common,before:b,after:a,delta:b-a};", "return {valid:true,common,before:b,after:a,delta:b-a,ruleChanged:before.ruleVersion!==after.ruleVersion};")
    replace('return `<div class="sourcelabel">${label}', 'return `${v.ruleChanged?\'<div class="note info p12">判定ルールの版が異なるため、分類・順位は比較しません。ここでは同じ業務の自己申告時間だけを比較しています。</div>\':\'\'}<div class="sourcelabel">${label}')
    replace("const shown=e.items.filter(x=>filter==='all'||x.cat===filter);", "const shown=e.items.filter(x=>filter==='all'||x.cat===filter);")
    replace(')+`<div class="summaryhero"><div><span', ')+`${r.ruleVersion!==RULE_VERSION?\'<div class="note info p20">過去の回答を、現在の判断ルールで再整理して表示しています。保存した回答自体は変更していません。</div>\':\'\'}<div class="summaryhero"><div><span')
    next_steps = r'''function nextStepsHTML(r,e){return `<section class="section" id="next-steps"><div class="sectionhead"><div><div class="eyebrow">CHOOSE YOUR NEXT STEP</div><h2>次に進む道を、分けて考える。</h2><p>候補に残した仕事だけを表示しています。すべてを外部に頼む必要はありません。</p></div></div><div class="grid three">${[['self','自分たちで改善する','共通の書式や、公開情報での下書きから小さく試します。'],['expert','専門家と確かめる','安全・個人情報・判断の範囲を確認。必要に応じて研修や支援へ。'],['system','道具の設定・導入を検討','まず今のツールでできるか確認。足りない機能だけ導入を比べます。']].map(([key,name,desc])=>{const items=e.actionable.filter(x=>x.route===key);return `<div class="card next-route"><span class="tag outline">${items.length}件</span><h3 class="p12">${name}</h3><p class="small muted p8">${desc}</p><p class="small p12">${items.map(x=>esc(taskName(r.industry,x.id))).join('<br>')||'今回は該当なし'}</p></div>`}).join('')}</div></section>`;}
'''
    replace('function resultsView(){', next_steps+'function resultsView(){')
    replace('${effectHTML(r,e)}<section', '${effectHTML(r,e)}${nextStepsHTML(r,e)}<section')
    replace("${button('相談したい','to-consult','secondary')}${button('会社全体で診断する'", "${button('相談したい','to-consult','secondary')}${button('詳しい改善提案を受けたい','consult-kind','secondary','data-kind=\"proposal\"')}${button('会社全体で診断する'")
    replace('</style>', '.taskfields.quickfields{grid-template-columns:repeat(3,minmax(0,1fr))}.taskfields.optionfields{grid-template-columns:repeat(2,minmax(0,1fr))}.optional-questions{margin-top:18px;border-top:1px solid var(--line);padding-top:13px}.optional-questions summary{font-size:12px;color:var(--green);cursor:pointer;overflow-wrap:anywhere}.next-route p{overflow-wrap:anywhere}@media(max-width:680px){.taskfields.quickfields,.taskfields.optionfields{grid-template-columns:1fr}.taskedit-head{align-items:flex-start}.taskedit-head .tag{white-space:normal;flex-shrink:0}}\n</style>')

scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
assert len(scripts) == 1
csp_hash = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
html, count = re.subn(r"script-src 'sha256-[^']+'", "script-src 'sha256-"+csp_hash+"'", html)
assert count == 1 and "connect-src 'none'" in html
js = OUT/'application-check.js'; js.write_text(scripts[0])
subprocess.run(['node', '--check', str(js)], check=True)
result = html.encode('utf-8')
TARGET.write_bytes(result)
(OUT/'保育AIチェック_LCREW_業務改善診断_v2.1.html').write_bytes(result)
(OUT/'manifest.json').write_text(json.dumps({'version':'2.1.0','base_sha256':BASE_SHA,'sha256':hashlib.sha256(result).hexdigest(),'bytes':len(result),'public_url':'https://ruu-first-app.vercel.app/hoiku-ai-check/','scope':'Frontend demo only; no server, AI API, cross-device sharing, or real consultation submission'}, ensure_ascii=False, indent=2))
print('Scoped revision prepared:', hashlib.sha256(result).hexdigest())
