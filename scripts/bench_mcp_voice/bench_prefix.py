import json,time,requests,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
os_out=Path(__file__).resolve().parent/'results'
from apps.voice.knowledge import build_context, retrieve_cards, _INSTRUCTIONS
from apps.voice.contracts import Intent, Evidence, SourceStamp
q="should I pit now for inters or stay out"
cards=retrieve_cards(Intent("complex"),q,game_season=None)
def ev(i):
    m=time.monotonic()
    return Evidence("complex",42,1,3,m+2,m+2,None,{"get_player_tyre_wear":{"current_wear_avg_pct":31.5+i*0.1,"tyre_compound":"Medium"},"get_session_info":{"environment":{"rain_pct":5+i}}},(),(SourceStamp("get_session_info",time.time(),m),))
def run(model,builder,label,n=4):
    out=[]
    for i in range(n):
        p=builder(i)
        r=requests.post("http://127.0.0.1:11434/api/generate",json={"model":model,"prompt":p,"stream":False,"keep_alive":"2h","options":{"temperature":0,"num_predict":8,"num_ctx":4096}},timeout=600).json()
        out.append({"total_s":round(r["total_duration"]/1e9,2),"prompt_eval_tokens":r.get("prompt_eval_count"),"prompt_eval_s":round(r.get("prompt_eval_duration",0)/1e9,2),"resp":r.get("response","")[:30]})
    return out
def current(i): return build_context(q,ev(i),cards)
def reordered(i):
    c=current(i); body=json.loads(c[len(_INSTRUCTIONS)+1:])
    static={"eligible_ids":body["eligible_ids"],"cards":body["cards"],"limitations":body["limitations"]}
    dyn={"question":body["question"],"evidence":body["evidence"]}
    return _INSTRUCTIONS+"\n"+json.dumps(static,sort_keys=True)+"\n"+json.dumps(dyn,sort_keys=True)
res={}
for model in ("llama3.1:8b","llama3.2:3b"):
    requests.post("http://127.0.0.1:11434/api/generate",json={"model":model,"prompt":"hi","stream":False,"keep_alive":"2h","options":{"num_predict":1}},timeout=600)
    res[model]={"current_order":run(model,current,"cur"),"static_prefix_first":run(model,reordered,"re")}
    requests.post("http://127.0.0.1:11434/api/generate",json={"model":model,"keep_alive":0})
json.dump(res,open(os_out/"prefix_cache.json","w"),indent=1);print(json.dumps(res,indent=1))
