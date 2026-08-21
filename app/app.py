import os, json, sys
from flask import Flask, render_template, request, jsonify
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from assistant import build_assistant, answer_query
from retrieval import LocalRetriever, build_documents

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
L1=os.path.join(ROOT,"output")
L2OUT=os.path.join(ROOT,"output","l2")
DEMOOUT=os.path.join(ROOT,"output","demo")
app=Flask(__name__)

def load(name, demo=False):
    out=DEMOOUT if demo else L2OUT
    with open(os.path.join(out,name),encoding="utf8") as f:return json.load(f)

def get_retriever(demo=False):
    out=DEMOOUT if demo else L2OUT
    return LocalRetriever(build_documents(L1,out))

@app.route("/")
def index():
    return render_template("index.html",
        summary=load("summary.json") if os.path.exists(os.path.join(L2OUT,"summary.json")) else {},
        priorities=load("priority_output.json"),
        groups=load("related_groups.json"))

@app.route("/priorities")
def priorities():
    return render_template("priorities.html",items=load("priority_output.json"))

@app.route("/groups")
def groups():
    return render_template("related_groups.html",groups=load("related_groups.json"))

@app.route("/messages")
def messages():
    return render_template("messages.html",messages=load("l2_display_messages.json"))

@app.route("/privacy")
def privacy():
    return render_template("sensitive.html",items=load("privacy_routing.json"))

@app.route("/demo")
def demo_page():
    qs=[]
    import csv
    with open(os.path.join(ROOT,"data/private/l2_demo_queries.csv"),encoding="utf-8-sig") as f: qs=list(csv.DictReader(f))
    return render_template("demo.html",queries=qs)

@app.route("/demo/<query_id>")
def demo_result(query_id):
    r=get_retriever(demo=True)
    qs=[]
    import csv
    with open(os.path.join(ROOT,"data/private/l2_demo_queries.csv"),encoding="utf-8-sig") as f: qs=list(csv.DictReader(f))
    q=next((x["query"] for x in qs if x["query_id"]==query_id),None)
    if q is None:return "Unknown query",404
    ans=answer_query(q,r,DEMOOUT); ans["query_id"]=query_id
    return render_template("demo_result.html",result=ans)

@app.route("/assistant", methods=["GET","POST"])
def assistant_page():
    answer=None
    query=""
    if request.method=="POST":
        query=request.form.get("query","").strip()
        if query:
            r=get_retriever(demo=False)
            answer=answer_query(query,r,L2OUT)
    return render_template("assistant.html",answer=answer,query=query)

@app.route("/api/assistant",methods=["POST"])
def assistant_api():
    data=request.get_json(force=True)
    query=str(data.get("query","")).strip()
    if not query:return jsonify({"error":"query is required"}),400
    r=get_retriever(demo=False)
    return jsonify(answer_query(query,r,L2OUT))

@app.route("/api/demo/<query_id>")
def demo_query(query_id):
    r=get_retriever(demo=True)
    qs=[]
    with open(os.path.join(ROOT,"data/private/l2_demo_queries.csv"),encoding="utf-8-sig") as f:
        import csv; qs=list(csv.DictReader(f))
    q=next((x["query"] for x in qs if x["query_id"]==query_id),None)
    if q is None:return jsonify({"error":"unknown query"}),404
    result=answer_query(q,r,DEMOOUT); result["query_id"]=query_id
    return jsonify(result)

@app.route("/health")
def health(): return jsonify({"status":"ok","l2":"loaded"})

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
