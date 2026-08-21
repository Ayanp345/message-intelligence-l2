"""
retrieval.py
Local TF-IDF retrieval over safe message text and structured records.
"""
import json, os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class LocalRetriever:
    def __init__(self, documents):
        self.documents=documents
        self.vectorizer=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True,lowercase=True)
        self.matrix=self.vectorizer.fit_transform([d["text"] for d in documents]) if documents else None
    def search(self,query,top_k=6):
        if self.matrix is None:return []
        q=self.vectorizer.transform([query])
        scores=cosine_similarity(q,self.matrix).ravel()
        idx=np.argsort(-scores)[:top_k]
        return [{**self.documents[i],"relevance_score":round(float(scores[i]),4)} for i in idx if scores[i]>0]

def build_documents(l1_dir,out_dir):
    with open(os.path.join(l1_dir,"display_messages.json"),encoding="utf8") as f:l1=json.load(f)
    with open(os.path.join(out_dir,"l2_display_messages.json"),encoding="utf8") as f:l2=json.load(f)
    with open(os.path.join(out_dir,"l2_tasks_events.json"),encoding="utf8") as f:items=json.load(f)
    with open(os.path.join(out_dir,"related_groups.json"),encoding="utf8") as f:groups=json.load(f)
    docs=[]
    for m in l1+l2:
        text=m.get("text",m.get("message",""))
        docs.append({"doc_id":m["message_id"],"kind":"message","message_id":m["message_id"],"text":text})
    for i in items:
        docs.append({"doc_id":i["item_id"],"kind":"task_event","item_id":i["item_id"],
                     "text":f'{i.get("title","")} {i.get("description","")} deadline {i.get("deadline","")} date {i.get("date","")}'})
    for g in groups:
        docs.append({"doc_id":g["group_id"],"kind":"group","group_id":g["group_id"],
                     "text":f'{g["title"]} {g["summary"]} status {g["status"]} deadline {g.get("latest_deadline","")}'})
    return docs

def save_index_metadata(retriever,out_dir):
    meta={"document_count":len(retriever.documents),
          "vocabulary_size":len(retriever.vectorizer.vocabulary_),
          "nonzero_entries":int(retriever.matrix.nnz)}
    with open(os.path.join(out_dir,"retrieval_metadata.json"),"w") as f:json.dump(meta,f,indent=2)
    return meta
