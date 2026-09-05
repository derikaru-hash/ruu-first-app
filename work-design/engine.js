/* Work Design OS v1.0.0 — deterministic, minute-based capacity model. */
(function(root){'use strict';
const DAYS=['月','火','水','木','金','土','日'], HOURS=Array.from({length:10},(_,i)=>i+8);
const SKILLS=['接客','調理','事務','現場対応','責任者判断','制作'];
const LABELS={remove:'なくす',batch:'まとめる',ai:'AIへ任せる',move:'再配置する',hire:'人が担う・採用を検討'};
const clone=x=>JSON.parse(JSON.stringify(x));
const uid=()=>globalThis.crypto?.randomUUID?.()||'w'+Date.now().toString(36)+Math.random().toString(36).slice(2,10);
function grid(values,days=[0,1,2,3,4]){return DAYS.map((_,d)=>HOURS.map((h,i)=>days.includes(d)?(values[h]||0):0));}
function sample(){
 const task=(id,name,minutes,start,end,skill,place,strategy,after,review,why,extra={})=>({id,name,minutes,start,end,skill,place,strategy,after,review,why,days:[0,1,2,3,4],mode:'flex',source:'仮想店舗のデモ用仮定。実測ではありません。',evidence:'assumed',essential:false,active:false,newStart:start,newEnd:end,...extra});
 return {version:1,company:'まちの食堂（仮想事例）',concern:'お昼の受付が足りません。事務作業も増えたので、万能なスタッフを一人採用しようと考えています。',scope:'1店舗の対象業務。担当者の時間は休憩・対象外の仕事を除いた対応可能時間。',tasks:[
 task('t1','店頭の受付・注文',180,10,13,'接客','onsite','hire',180,0,'この時間に店頭にいる人が必要。文章AIでは置き換えない。',{mode:'coverage',essential:true}),
 task('t2','料理の提供・片付け',120,11,13,'現場対応','onsite','hire',120,0,'提供と片付けは現地での対応を残す。',{mode:'coverage',essential:true}),
 task('t3','予約内容の転記',60,9,10,'事務','either','ai',15,10,'入力整理を支援し、予約日時・人数を人が確認する。15分には確認10分を含む。'),
 task('t4','同じ数字の二重入力',30,14,15,'事務','either','remove',0,0,'正本を一つにできるかを確認。法令・契約で必要な記録なら廃止しない。'),
 task('t5','売上確認レポート',30,14,15,'事務','either','batch',10,5,'報告先と正本を統一。集計と確認を合わせて10分と仮定。'),
 task('t6','翌日の仕込み準備',90,11,13,'調理','onsite','move',90,0,'当日提供に不要な準備だけを13〜15時へ移す。保存・衛生条件は責任者が確認。',{newStart:13,newEnd:15}),
 task('t7','問い合わせ返信の下書き',30,9,10,'事務','either','ai',15,10,'下書きまでを支援。人が内容を確認して送信する。15分には確認10分を含む。'),
 task('t8','返金・例外対応の判断',30,10,12,'責任者判断','onsite','hire',30,0,'金額と対応方針の判断は責任者が担う。',{essential:true})
 ],workers:[
 {id:'p1',name:'現場リーダー',skills:['接客','責任者判断'],place:'onsite',capacity:grid({9:60,10:60,11:60,13:60,14:60})},
 {id:'p2',name:'厨房・提供担当',skills:['調理','現場対応'],place:'onsite',capacity:grid({9:60,10:60,11:60,12:60,13:60,14:60})},
 {id:'p3',name:'事務サポート',skills:['事務'],place:'remote',capacity:grid({9:60,13:30,14:60})}
 ],mentor:'現場リーダー',setupMinutes:120,trainingMinutes:180,observations:[],checks:{},approval:null,history:[],revision:1};
}
function blank(){const s=sample();s.company='自社の仕事設計';s.concern='';s.scope='対象業務と、対象外業務・休憩を除いた対応可能時間を記録してください。';s.tasks=[];s.workers=[];s.mentor='未定';return s;}
function errors(s){
 const out=[],num=(x,min,max)=>typeof x==='number'&&Number.isFinite(x)&&x>=min&&x<=max&&Number.isInteger(x);
 if(!s||s.version!==1)return ['対応していないデータ形式です。'];
 if(!Array.isArray(s.tasks)||s.tasks.length>30||!Array.isArray(s.workers)||s.workers.length>12)return ['業務30件・担当12枠までです。'];
 if(!s.tasks.length)out.push('業務を1件以上登録してください。');
 if(!s.workers.length)out.push('対応可能時間を1枠以上登録してください。');
 const ids=new Set();
 s.tasks.forEach(t=>{
 if(!t||typeof t.id!=='string'||ids.has(t.id)){out.push('業務IDが不正または重複しています。');return;}ids.add(t.id);
 const n=t.name||'名称未入力の業務';
 if(typeof t.name!=='string'||!t.name.trim()||t.name.length>100)out.push('業務名は1〜100文字で入力してください。');
 if(!num(t.minutes,1,600))out.push(n+'：必要時間を1〜600分で入力してください。不明は0と扱いません。');
 if(!num(t.start,8,17)||!num(t.end,9,18)||t.start>=t.end)out.push(n+'：時間帯が不正です。');
 if(t.minutes>(t.end-t.start)*60)out.push(n+'：1人で処理する時間が枠を超えています。並行作業は別業務として分けてください。');
 if(!Array.isArray(t.days)||!t.days.length||t.days.some(d=>!num(d,0,6))||new Set(t.days).size!==t.days.length)out.push(n+'：実施曜日を選んでください。');
 if(!SKILLS.includes(t.skill)||!['onsite','either'].includes(t.place)||!['flex','coverage'].includes(t.mode))out.push(n+'：場所・技能・実施方法を確認してください。');
 if(!Object.keys(LABELS).includes(t.strategy))out.push(n+'：仕分けが不正です。');
 if(!['assumed','measured','unknown'].includes(t.evidence))out.push(n+'：根拠の種類を選んでください。');
 if(t.evidence==='unknown')out.push(n+'：時間が未確認です。測定するか、仮定として明示してください。');
 if(typeof t.why!=='string'||t.why.length>1600)out.push(n+'：改善理由の形式を確認してください。');
 if(typeof t.source!=='string'||!t.source.trim()||t.source.length>600)out.push(n+'：根拠・測定メモを入力してください。');
 if(typeof t.essential!=='boolean'||typeof t.active!=='boolean')out.push(n+'：確認フラグが不正です。');
 if(!num(t.after,0,600)||!num(t.review,0,600)||!num(t.newStart,8,17)||!num(t.newEnd,9,18)||t.newStart>=t.newEnd)out.push(n+'：改善後の時間・時間帯が不正です。');
 });
 const pids=new Set();s.workers.forEach(w=>{
 if(!w||typeof w.id!=='string'||pids.has(w.id)){out.push('担当IDが不正または重複しています。');return;}pids.add(w.id);
 if(typeof w.name!=='string'||!w.name.trim()||w.name.length>80)out.push('担当名を入力してください。');
 if(!Array.isArray(w.skills)||!w.skills.length||w.skills.some(k=>!SKILLS.includes(k))||new Set(w.skills).size!==w.skills.length)out.push(w.name+'：対応できる技能を選んでください。');
 if(!['onsite','remote'].includes(w.place))out.push(w.name+'：場所が不正です。');
 if(!Array.isArray(w.capacity)||w.capacity.length!==7||w.capacity.some(r=>!Array.isArray(r)||r.length!==10||r.some(v=>!num(v,0,60))))out.push(w.name+'：対応時間は曜日・時間帯ごとに0〜60分です。空欄は保存できません。');
 });
 if(!num(s.setupMinutes,0,100000)||!num(s.trainingMinutes,0,100000))out.push('初期設定・教育時間を0以上の整数で入力してください。');
 if(typeof s.company!=='string'||s.company.length>100||typeof s.concern!=='string'||s.concern.length>5000||typeof s.scope!=='string'||s.scope.length>1000)out.push('事業情報の入力上限を超えています。');
 return [...new Set(out)];
}
function effective(t,after){
 let r={...t,blocked:'',changed:false};if(!after||!t.active)return r;
 if(t.strategy==='remove'&&t.essential)r.blocked='責任・安全・必要記録があるため、なくす案は停止しました。';
 else if(t.strategy==='ai'&&(t.essential||t.place==='onsite'||t.mode==='coverage'))r.blocked='現地対応・常時対応・重要判断は文章AIへ移せません。';
 else if(t.strategy==='ai'&&(t.review<1||t.after<t.review))r.blocked='AI案には1分以上の人の確認と、その時間を含む残作業時間が必要です。';
 else if(t.strategy==='batch'&&(t.essential||t.mode==='coverage'))r.blocked='必要な対応・記録をまとめてよいか確認が必要です。';
 else if(t.strategy==='batch'&&(t.after<1||t.after<t.review))r.blocked='まとめる案では残作業と確認時間を残してください。';
 else if(t.strategy==='move'&&(t.mode==='coverage'||t.essential))r.blocked='時間帯に必要な対応は動かせません。現場確認が必要です。';
 if(r.blocked)return r;
 if(t.strategy==='remove')r.minutes=0;
 if(['ai','batch'].includes(t.strategy))r.minutes=t.after;
 if(t.strategy==='move'){r.start=t.newStart;r.end=t.newEnd;}
 if(r.minutes>(r.end-r.start)*60){r={...t,blocked:'改善後の時間枠を超えています。元の条件で計算します。',changed:false};return r;}
 r.changed=r.minutes!==t.minutes||r.start!==t.start||r.end!==t.end;return r;
}
class Flow{
 constructor(){this.g=[];}
 node(){this.g.push([]);return this.g.length-1;}
 edge(a,b,c){const x={to:b,rev:this.g[b].length,cap:c,original:c},y={to:a,rev:this.g[a].length,cap:0,original:0};this.g[a].push(x);this.g[b].push(y);return x;}
 run(s,t){let total=0;while(true){let level=Array(this.g.length).fill(-1),q=[s];level[s]=0;for(let i=0;i<q.length;i++)for(const e of this.g[q[i]])if(e.cap>0&&level[e.to]<0){level[e.to]=level[q[i]]+1;q.push(e.to);}if(level[t]<0)break;let it=Array(this.g.length).fill(0);const dfs=(v,f)=>{if(v===t)return f;for(;it[v]<this.g[v].length;it[v]++){let e=this.g[v][it[v]];if(e.cap>0&&level[v]+1===level[e.to]){const k=dfs(e.to,Math.min(f,e.cap));if(k){e.cap-=k;this.g[e.to][e.rev].cap+=k;return k;}}}return 0;};let f;while((f=dfs(s,1e9))>0)total+=f;}return total;}
}
function schedule(s,after){
 const f=new Flow(),src=f.node(),sink=f.node(),wn=[],usedGrid=DAYS.map(()=>HOURS.map(()=>0)),capGrid=clone(usedGrid),fixedGap=clone(usedGrid),jobs=[],assignments=[];
 s.workers.forEach((w,p)=>{wn[p]=DAYS.map((_,d)=>HOURS.map((h,i)=>{const n=f.node(),cap=w.capacity[d][i];f.edge(n,sink,cap);capGrid[d][i]+=cap;return n;}));});
 const effectiveTasks=s.tasks.map(t=>effective(t,after));
 for(const t of [...effectiveTasks].sort((a,b)=>Number(b.skill==='責任者判断')-Number(a.skill==='責任者判断'))){if(!t.minutes)continue;for(const d of t.days){
 const spans=t.mode==='coverage'?Array.from({length:t.end-t.start},(_,i)=>[t.start+i,t.start+i+1,t.minutes/(t.end-t.start)]):[[t.start,t.end,t.minutes]];
 for(const [start,end,demand] of spans){
 const node=f.node(),sedge=f.edge(src,node,demand),job={taskId:t.id,name:t.name,skill:t.skill,place:t.place,mode:t.mode,day:d,start,end,demand,sedge,links:[]};
 for(let h=start;h<end;h++){const hn=f.node();f.edge(node,hn,60);s.workers.forEach((w,p)=>{if(w.skills.includes(t.skill)&&(t.place!=='onsite'||w.place==='onsite')){const e=f.edge(hn,wn[p][d][h-8],60);job.links.push({edge:e,workerId:w.id,worker:w.name,hour:h,day:d,taskId:t.id});}});}jobs.push(job);
 }
 }}
 const filled=f.run(src,sink),gaps=[];
 for(const j of jobs){const remaining=j.sedge.cap;if(remaining>1e-6){gaps.push({taskId:j.taskId,name:j.name,skill:j.skill,place:j.place,day:j.day,start:j.start,end:j.end,minutes:remaining,mode:j.mode});if(j.mode==='coverage')fixedGap[j.day][j.start-8]+=remaining;}
 for(const x of j.links){const m=x.edge.original-x.edge.cap;if(m>0){usedGrid[x.day][x.hour-8]+=m;assignments.push({workerId:x.workerId,worker:x.worker,day:x.day,hour:x.hour,taskId:x.taskId,minutes:m});}}}
 const demand=jobs.reduce((a,j)=>a+j.demand,0),capacity=capGrid.flat().reduce((a,b)=>a+b,0);
 return {demand,filled,gap:demand-filled,capacity,usedGrid,capGrid,fixedGap,gaps,assignments,tasks:effectiveTasks};
}
function roles(result){const out={};for(const g of result.gaps){const key=g.skill+'|'+g.place;if(!out[key])out[key]={skill:g.skill,place:g.place,minutes:0,days:[],windows:[],tasks:[]};const r=out[key];r.minutes+=g.minutes;r.days.push(g.day);r.windows.push([g.start,g.end]);r.tasks.push(g.name);}return Object.values(out).map(r=>({...r,days:[...new Set(r.days)].sort(),tasks:[...new Set(r.tasks)],start:Math.min(...r.windows.map(w=>w[0])),end:Math.max(...r.windows.map(w=>w[1]))})).sort((a,b)=>b.minutes-a.minutes);}
function analyze(s){const es=errors(s);if(es.length)return {errors:es};const before=schedule(s,false),after=schedule(s,true);return {errors:[],before,after,saved:before.demand-after.demand,roles:roles(after),warnings:after.tasks.filter(t=>t.blocked).map(t=>t.name+'：'+t.blocked),assumed:s.tasks.filter(t=>t.evidence!=='measured').length};}
const hours=m=>(Math.round(m/6)/10).toLocaleString('ja-JP',{maximumFractionDigits:1});
function fingerprint(s){const data=JSON.stringify([s.company,s.concern,s.scope,s.tasks,s.workers,s.mentor,s.setupMinutes,s.trainingMinutes,s.observations,s.checks]);let a=2166136261;for(let i=0;i<data.length;i++){a^=data.charCodeAt(i);a=Math.imul(a,16777619);}return (a>>>0).toString(16);}
function report(s){const a=analyze(s);if(a.errors.length)return '入力を確認してください。\n'+a.errors.join('\n');const L=['仕事設計OS｜ルウ王子版','判断資料・採用要件のたたき台（募集文ではありません）',s.company,'作成：'+new Date().toLocaleString('ja-JP'),'版：'+s.revision+' / 条件ID：'+fingerprint(s),'','相談：'+s.concern,'対象範囲：'+s.scope,'','【時間の比較・試算】','再設計前 '+hours(a.before.demand)+'時間／週 → 試算後 '+hours(a.after.demand)+'時間／週','作業時間の差 '+hours(a.saved)+'時間／週。人の確認時間を含む。実現した削減ではない。','この配分案の未充足 '+hours(a.before.gap)+'時間／週 → '+hours(a.after.gap)+'時間／週','初期設定 '+s.setupMinutes+'分、教育担当の時間 '+s.trainingMinutes+'分（初週の別枠。週次削減から自動相殺しない）','','【五つの仕分け】'];for(const t of a.after.tasks)L.push(t.name+'｜'+LABELS[t.strategy]+'｜'+(t.active?'試算対象':'未適用')+'｜'+t.minutes+'分／実施日｜'+t.start+'〜'+t.end+'時｜'+DAYS.filter((_,i)=>t.days.includes(i)).join('・')+'｜根拠：'+t.source+(t.blocked?'｜停止：'+t.blocked:''));
 L.push('','【残る役割】');if(!a.roles.length)L.push('この計算条件では未充足なし。ただし採用不要の確定ではない。連続作業・移動・休憩・突発対応を現場確認する。');for(const r of a.roles)L.push(r.skill+'／'+(r.place==='onsite'?'現地':'現地または遠隔')+'／'+r.days.map(d=>DAYS[d]).join('・')+'／'+r.start+'〜'+r.end+'時の範囲／未充足 '+hours(r.minutes)+'時間／週／'+r.tasks.join('、'));
 L.push('','求人にする前の確認：雇用形態、賃金、勤務地、契約期間、勤務・休憩、必要な資格、教育時間を責任者が別途確定。時間の合計を人数へ換算しない。','候補者の年齢・性別・性格・健康等を推定／評価しない。','', '【試行と育成】','責任者：'+s.mentor,'開始前：対象業務の手順・基準・停止条件を確認。教育時間を確保する。','7日：回数・実測時間・確認工数・ミス・引継ぎを比較。品質悪化なら停止。','30日：同じ条件の前後で比較。単独対応の合格は責任者が確認。','60日：例外対応と支援負担を確認。','90日：仕事量・配置・求人要件を見直す。','180日：継続状況と担当できる仕事を確認。本人同意なしの定着予測はしない。','','【観察記録】');for(const o of s.observations||[])L.push(o.date+'｜'+o.task+'｜前 '+o.before+'分／後 '+o.after+'分（確認込）｜回数 '+o.count+'｜ミス '+o.errors+'｜'+o.note);if(!(s.observations||[]).length)L.push('まだ記録なし。仮定を実績として扱わない。');
 const ok=s.approval&&s.approval.hash===fingerprint(s);L.push('','【確認】',ok?'試行計画を確認済み：'+s.approval.by+' / '+s.approval.at:'未確認。まだ正式運用・採用承認ではありません。','','【計算の限界と保存】','曜日別・1時間枠の分割可能作業として最大流で配分。技能と現地条件を照合し、担当枠の容量を二重使用しない。唯一の最適な役割分担ではなく、一つの配分案。連続作業、移動、細かな同時発生、法令適合を保証しない。','データは同じ端末・同じブラウザのローカル保存。共有DB・候補者選考・自動求人掲載・給与計算は対象外。');return L.join('\n');}
const api={DAYS,HOURS,SKILLS,LABELS,clone,uid,grid,sample,blank,errors,effective,schedule,roles,analyze,hours,fingerprint,report};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.WD=api;
})(typeof globalThis!=='undefined'?globalThis:this);
