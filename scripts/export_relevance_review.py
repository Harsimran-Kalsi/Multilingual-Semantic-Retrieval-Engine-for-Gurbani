#!/usr/bin/env python3
"""Create an offline, ungraded human review worksheet with complete source context."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gurbani relevance review</title><style>
body{font:16px/1.6 system-ui,sans-serif;background:#f5f3ed;color:#172c34;margin:0}main{max-width:980px;margin:auto;padding:32px 24px}h1{font-size:30px;margin:0}header p{max-width:760px;color:#465a60}.toolbar{position:sticky;top:0;background:#f5f3ed;padding:16px 0;display:flex;gap:12px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #bdc9c9;z-index:1}button,select,input{font:inherit;padding:9px;border:1px solid #9cabaf;border-radius:8px;background:white;color:#172c34}button{cursor:pointer}button.primary{background:#185b5b;color:white}#question{font-size:23px}.card{background:white;border:1px solid #d4ddda;border-radius:12px;margin:18px 0;padding:22px}.meta{font-size:13px;color:#52666c}.grade{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.line{border-bottom:1px solid #e5e8e6;padding:12px 0}.gurmukhi{font-size:21px;line-height:1.7}details{margin-top:14px}summary{cursor:pointer;color:#185b5b;font-weight:600}.status{color:#185b5b;font-weight:600}#querySelect{max-width:100%}.help{padding:16px;background:#e4ece7;border-radius:10px}@media(max-width:600px){main{padding:20px 14px}.toolbar{gap:8px}.card{padding:16px}}
</style><main><header><h1>Gurbani relevance review</h1><p>Assess whether each complete passage helps answer the question. Candidate order is shuffled and retrieval methods are hidden. Questions are assistant-authored test candidates, not real user submissions.</p></header>
<p class="help"><strong>Grades:</strong> 0 = irrelevant; 1 = related topic but does not answer; 2 = partly answers; 3 = directly useful. Read the full passage before grading. Leave uncertain items ungraded. This worksheet does not judge generated answers.</p>
<label>Reviewer initials or alias <input id="reviewer" autocomplete="off" placeholder="Your reviewer label"></label>
<div class="toolbar"><button id="previous">Previous</button><select id="querySelect" aria-label="Question"></select><button id="next">Next</button><button class="primary" id="download">Download ratings</button><span class="status" id="progress"></span></div>
<h2 id="question"></h2><p id="queryMeta" class="meta"></p><div id="candidates"></div></main>
<script id="reviewData" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('reviewData').textContent),key='gurbani-review-'+data.fingerprint;
let saved={ratings:{},reviewer:''};try{saved=JSON.parse(localStorage.getItem(key))||saved}catch(e){}
const qs=document.getElementById('querySelect'),reviewer=document.getElementById('reviewer'),container=document.getElementById('candidates');reviewer.value=saved.reviewer||'';
function persist(){saved.reviewer=reviewer.value.trim();try{localStorage.setItem(key,JSON.stringify(saved))}catch(e){}updateProgress()}
function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el}
function updateProgress(){const total=data.queries.reduce((n,q)=>n+q.candidates.length,0),count=Object.keys(saved.ratings).length;document.getElementById('progress').textContent=count+' / '+total+' passages graded'}
data.queries.forEach((q,i)=>{const option=node('option',(i+1)+'. '+q.query);option.value=i;qs.append(option)});
function render(){const q=data.queries[Number(qs.value)];document.getElementById('question').textContent=q.query;document.getElementById('queryMeta').textContent=q.id+' · '+q.language;container.replaceChildren();q.candidates.forEach((c,i)=>{const card=node('article',undefined,'card');card.append(node('h3','Passage '+(i+1)),node('p','Ang '+c.ang+' · Source '+c.source_id,'meta'));const grade=node('div',undefined,'grade'),label=node('label','Relevance '),select=node('select');select.setAttribute('aria-label','Grade passage '+(i+1));[['','Not graded'],['0','0 — Irrelevant'],['1','1 — Related topic'],['2','2 — Partly answers'],['3','3 — Directly useful']].forEach(([v,t])=>{const o=node('option',t);o.value=v;select.append(o)});const ratingKey=q.id+'|'+c.shabad_id;if(saved.ratings[ratingKey])select.value=saved.ratings[ratingKey].grade;select.addEventListener('change',()=>{if(select.value==='')delete saved.ratings[ratingKey];else saved.ratings[ratingKey]={grade:Number(select.value),reviewed_at:new Date().toISOString()};persist()});label.append(select);grade.append(label);card.append(grade);const details=node('details');details.append(node('summary','Read complete passage ('+data.passages[c.shabad_id].length+' lines)'));data.passages[c.shabad_id].forEach(line=>{const row=node('div',undefined,'line');row.append(node('div',line.gurmukhi,'gurmukhi'),node('div',line.translation||''),node('div','Ang '+line.ang+' · '+line.source_id,'meta'));details.append(row)});card.append(details);container.append(card)});updateProgress()}
qs.addEventListener('change',render);reviewer.addEventListener('input',persist);document.getElementById('previous').onclick=()=>{qs.value=Math.max(0,Number(qs.value)-1);render()};document.getElementById('next').onclick=()=>{qs.value=Math.min(data.queries.length-1,Number(qs.value)+1);render()};
document.getElementById('download').onclick=()=>{if(!reviewer.value.trim()){alert('Enter reviewer initials or an alias before exporting.');return}const rows=data.queries.map(q=>{const candidates=q.candidates.map(c=>({...c,relevance_grade:saved.ratings[q.id+'|'+c.shabad_id]?.grade??null,reviewed_at:saved.ratings[q.id+'|'+c.shabad_id]?.reviewed_at??null}));return {...q,reviewer_id:reviewer.value.trim(),review_status:candidates.every(c=>c.relevance_grade!==null)?'complete':'partial',candidates}});const blob=new Blob([rows.map(row=>JSON.stringify(row)).join('\n')+'\n'],{type:'application/x-ndjson'}),url=URL.createObjectURL(blob),link=node('a');link.href=url;link.download='gurbani-human-ratings.jsonl';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};render();
</script></html>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pool',type=Path,default=ROOT/'reports/conceptual_review_pool.jsonl')
    parser.add_argument('--corpus',type=Path,default=ROOT/'data/sggs.jsonl')
    parser.add_argument('--output',type=Path,default=ROOT/'reports/relevance_review.html')
    args=parser.parse_args()
    queries=[json.loads(line) for line in args.pool.read_text().splitlines() if line.strip()]
    ids={candidate['shabad_id'] for query in queries for candidate in query['candidates']}
    passages=defaultdict(list)
    for raw in args.corpus.read_text().splitlines():
        row=json.loads(raw)
        key=row['context']['shabad_id']
        if key in ids:
            passages[key].append({'gurmukhi':row['gurmukhi'],'translation':row.get('translation'),
                'ang':row['citation']['ang'],'source_id':row['citation']['source_id']})
    if ids-set(passages):
        raise ValueError('Review pool references a passage missing from the corpus')
    payload=json.dumps({'queries':queries,'passages':passages,'fingerprint':hashlib.sha256(args.pool.read_bytes()).hexdigest()},ensure_ascii=False).replace('<','\\u003c')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(TEMPLATE.replace('__DATA__',payload))
    print(f'Created offline review worksheet: {len(queries)} questions, {sum(len(q["candidates"]) for q in queries)} candidates; all ratings remain ungraded.')


if __name__=='__main__':
    main()
