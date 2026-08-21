import os,sys,json
from l2_engine import build_l2
from assistant import build_assistant
from benchmark import benchmark

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L1=os.path.join(ROOT,"output")
# L1 outputs are kept in output/ from the original submission. Before running
# this script, preserve them; L2 outputs are written under output/l2/.
OUT=os.path.join(ROOT,"output","l2")
L2=os.path.join(ROOT,"data","private","l2_messages.csv")
Q=os.path.join(ROOT,"data","private","l2_demo_queries.csv")

def main():
    # The original L1 outputs live in output/. We copy their inputs conceptually
    # by referencing the existing L1 JSONs and write only new L2 artifacts below.
    build_l2(L1,L2,OUT)
    r,results,meta=build_assistant(L1,OUT,Q)
    report=benchmark(L1,OUT,Q)
    print(json.dumps({"retrieval":meta,"benchmark":report},indent=2))

if __name__=="__main__":main()
