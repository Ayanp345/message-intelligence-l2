import json, os, time, re
from retrieval import LocalRetriever, build_documents
from assistant import answer_query

def keyword_search(documents,query,top_k=6):
    q=set(re.findall(r"[a-z0-9]+",query.lower()))
    scored=[]
    for d in documents:
        toks=set(re.findall(r"[a-z0-9]+",d["text"].lower()))
        score=len(q&toks)/(len(q)**0.5*max(1,len(toks))**0.5)
        if score>0:scored.append((score,d))
    scored.sort(key=lambda x:-x[0])
    return [{**d,"relevance_score":round(float(s),4)} for s,d in scored[:top_k]]

def benchmark(l1_dir,out_dir,queries_csv):
    docs=build_documents(l1_dir,out_dir)
    r=LocalRetriever(docs)
    import csv
    with open(queries_csv,encoding="utf-8-sig",newline="") as f:qs=list(csv.DictReader(f))
    base_times=[];opt_times=[];comparison=[]
    for q in qs:
        t=time.perf_counter();b=keyword_search(docs,q["query"]);base_times.append(time.perf_counter()-t)
        t=time.perf_counter();o=r.search(q["query"]);opt_times.append(time.perf_counter()-t)
        comparison.append({"query_id":q["query_id"],"baseline_top":b[0]["doc_id"] if b else None,"optimized_top":o[0]["doc_id"] if o else None})
    import numpy as np
    report={
      "benchmark_queries":len(qs),
      "baseline_keyword_mean_ms":round(float(np.mean(base_times)*1000),3),
      "baseline_keyword_p95_ms":round(float(np.percentile(base_times,95)*1000),3),
      "optimized_tfidf_mean_ms":round(float(np.mean(opt_times)*1000),3),
      "optimized_tfidf_p95_ms":round(float(np.percentile(opt_times,95)*1000),3),
      "index_documents":len(docs),
      "index_vocabulary":len(r.vectorizer.vocabulary_),
      "quality_note":"Retrieval quality is compared using the supplied mandatory queries; production answers still require evidence-grounded structured handling.",
      "query_comparison":comparison
    }
    with open(os.path.join(out_dir,"benchmark_report.json"),"w") as f:json.dump(report,f,indent=2)
    return report
