import os,csv
from l2_engine import build_l2
from assistant import build_assistant

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L1=os.path.join(ROOT,"output")
PRIVATE=os.path.join(ROOT,"data","private")
combined=os.path.join(PRIVATE,"l2_plus_demo.csv")
if not os.path.exists(combined):
    rows=[]
    for name in ("l2_messages.csv","l2_demo_messages.csv"):
        with open(os.path.join(PRIVATE,name),encoding="utf-8-sig",newline="") as f: rows.extend(list(csv.DictReader(f)))
    rows.sort(key=lambda x:x["timestamp"])
    with open(combined,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["message_id","timestamp","sender","message"]); w.writeheader(); w.writerows(rows)
OUT=os.path.join(ROOT,"output","demo")
build_l2(L1,combined,OUT)
build_assistant(L1,OUT,os.path.join(PRIVATE,"l2_demo_queries.csv"))
print("Demo outputs written to output/demo/")
