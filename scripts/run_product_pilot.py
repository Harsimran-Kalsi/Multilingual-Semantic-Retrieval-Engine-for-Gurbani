"""Run the three agreed synthetic tasks through unchanged project components."""
import hashlib, json, os, sqlite3, sys, tempfile, time
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT/'.env')
from backend.app.retrieval import CorpusRetriever
from backend.app.generation import GroundedAnswerGenerator
from backend.app.schemas import SearchRequest
OUT=ROOT/'reports/product_validation'
TASKS=[
('pilot-01', 'I remember something like “mann jeetay jag jeet.” Find the original line, its English translation, and the surrounding passage.'),
('pilot-02', 'Find passages about helping other people without becoming proud of how generous or good you are. Explain how the passages relate to that tension.'),
('pilot-03', 'People translate “hukam rajai chalna” as accepting God’s will. Does the surrounding passage suggest being passive, or something different? Show the source and distinguish the translation from your interpretation.')]

def main():
    results=[]
    with tempfile.TemporaryDirectory() as tmp:
        with sqlite3.connect(ROOT/'data/search.sqlite') as src, sqlite3.connect(Path(tmp)/'search.sqlite') as dst:
            src.backup(dst)
        retriever=CorpusRetriever(index_path=str(Path(tmp)/'search.sqlite'))
        generator=GroundedAnswerGenerator()
        for tid,query in TASKS:
            start=time.perf_counter()
            keyword=retriever.search(SearchRequest(query=query,top_k=8,mode='lexical'))
            sources=retriever.search(SearchRequest(query=query,top_k=8,mode='hybrid'))
            diagnostics=retriever.search_diagnostics
            record={'id':tid,'query':query,'provenance':'assistant_authored_user_accepted_synthetic_pilot',
                    'model':generator.model,'diagnostics':diagnostics,
                    'keyword_sources':[s.model_dump() for s in keyword],
                    'ask_sources':[s.model_dump() for s in sources]}
            try:
                record['answer']=generator.generate(query,sources).model_dump()
                record['generated']=True
            except Exception as exc:
                record['generated']=False
                record['error_type']=type(exc).__name__
            record['elapsed_seconds']=round(time.perf_counter()-start,3)
            record['full_passages']={s.verse_id:[x.model_dump() for x in retriever.passage(s.verse_id)] for s in sources}
            results.append(record)
            print(tid, 'generated=',record['generated'],diagnostics,flush=True)
            (OUT/'project_pilot_results.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),'human_scored':False,'chatgpt_comparison_complete':False,'results':results},ensure_ascii=False,indent=2))
    prompts=['# Three agreed comparison tasks','', 'Attach sggs_multilingual.txt. Use a fresh chat per task with the same file. Record the visible model. Save the full response.','']
    for tid,q in TASKS:
        prompts += [f'## {tid}', '', 'Use only the attached source file. You may search it with available tools. Give Shabad IDs and Angs for the passages you use. Do not invent references; say when the evidence is insufficient. Do not browse the web.', '',q,'']
    (OUT/'THREE_TASK_PROMPTS.md').write_text('\n'.join(prompts))
if __name__=='__main__': main()
