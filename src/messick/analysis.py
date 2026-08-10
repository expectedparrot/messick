"""Dependency-free response and classical scale diagnostics."""
from __future__ import annotations
import math, statistics
from datetime import datetime
from collections import Counter
from .errors import MessickError

MISSING=(None,"")
def number(v):
    try: return float(v)
    except (TypeError,ValueError): return None
def col(rows,key): return [r.get(key) for r in rows]
def mean(x): return sum(x)/len(x) if x else None
def variance(x): return sum((v-mean(x))**2 for v in x)/(len(x)-1) if len(x)>1 else None
def covariance(x,y): return sum((a-mean(x))*(b-mean(y)) for a,b in zip(x,y))/(len(x)-1) if len(x)>1 else None
def correlation(x,y):
    pairs=[(number(a),number(b)) for a,b in zip(x,y)]; pairs=[p for p in pairs if None not in p]
    if len(pairs)<3:return None
    a,b=zip(*pairs); va,vb=variance(a),variance(b)
    return covariance(a,b)/math.sqrt(va*vb) if va and vb else None

def eigen_symmetric(matrix,iterations=100):
    """Jacobi eigendecomposition for small correlation matrices."""
    n=len(matrix); a=[row[:] for row in matrix]; vectors=[[1.0 if i==j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(iterations):
        pairs=[(abs(a[i][j]),i,j) for i in range(n) for j in range(i+1,n)]
        if not pairs: break
        magnitude,p,q=max(pairs)
        if magnitude<1e-12: break
        angle=.5*math.atan2(2*a[p][q],a[q][q]-a[p][p]); c,s=math.cos(angle),math.sin(angle)
        for k in range(n):
            apk,aqk=a[p][k],a[q][k]; a[p][k]=c*apk-s*aqk; a[q][k]=s*apk+c*aqk
        for k in range(n):
            akp,akq=a[k][p],a[k][q]; a[k][p]=c*akp-s*akq; a[k][q]=s*akp+c*akq
            vkp,vkq=vectors[k][p],vectors[k][q]; vectors[k][p]=c*vkp-s*vkq; vectors[k][q]=s*vkp+c*vkq
    ordered=sorted(range(n),key=lambda i:a[i][i],reverse=True)
    return [a[i][i] for i in ordered],[[vectors[r][i] for r in range(n)] for i in ordered]

def alpha_for(matrix):
    if len(matrix)<2 or len(matrix[0])<2:return None
    k=len(matrix[0]); item_vars=[variance([r[j] for r in matrix]) for j in range(k)]; total_var=variance([sum(r) for r in matrix])
    return (k/(k-1))*(1-sum(item_vars)/total_var) if total_var and all(x is not None for x in item_vars) else None

def response_diagnostics(rows, bounds=None):
    bounds=bounds or {}; keys=sorted({k for r in rows for k in r}); items=[]
    for key in keys:
        vals=col(rows,key); present=[v for v in vals if v not in MISSING]; numeric=[number(v) for v in present]; all_numeric=present and all(v is not None for v in numeric)
        counts=Counter(str(v) for v in present); n=len(rows); item={"question_id":key,"n":n,"answered":len(present),"missing_rate":round((n-len(present))/n,6) if n else None,"option_utilization":dict(counts),"entropy":None}
        if counts:
            item["entropy"]=round(-sum((c/len(present))*math.log2(c/len(present)) for c in counts.values()),6)
        if all_numeric:
            lo,hi=bounds.get(key,(None,None)); item.update({"mean":mean(numeric),"sd":math.sqrt(variance(numeric)) if variance(numeric) is not None else None,"invalid_count":sum(1 for x in numeric if (lo is not None and x<lo) or (hi is not None and x>hi)),"floor_rate":sum(x==lo for x in numeric)/len(numeric) if lo is not None else None,"ceiling_rate":sum(x==hi for x in numeric)/len(numeric) if hi is not None else None})
        items.append(item)
    durations=[]
    for row in rows:
        direct=number(row.get("duration_seconds"))
        if direct is not None: durations.append(direct); continue
        try:
            start=datetime.fromisoformat(str(row.get("started_at")).replace("Z","+00:00")); end=datetime.fromisoformat(str(row.get("completed_at")).replace("Z","+00:00")); durations.append((end-start).total_seconds())
        except (TypeError,ValueError): pass
    timing=None
    if durations:
        ordered=sorted(durations)
        def pct(p): return ordered[min(len(ordered)-1,round((len(ordered)-1)*p))]
        timing={"observed":True,"n":len(ordered),"median_seconds":statistics.median(ordered),"p25_seconds":pct(.25),"p75_seconds":pct(.75),"p90_seconds":pct(.9)}
    return {"row_count":len(rows),"items":items,"observed_timing":timing}

def scale(rows, definition):
    items=definition.get("items",[])
    if len(items)<2: raise MessickError("INVALID_SCALE","A scale requires at least two items.")
    reverse=set(definition.get("reverse_scored") or definition.get("reverse-scored") or [])
    low,high=definition.get("range",[None,None]); vectors={}
    for item in items:
        values=[]
        for raw in col(rows,item):
            v=number(raw)
            if v is not None and item in reverse:
                if low is None or high is None: raise MessickError("INVALID_SCALE","Reverse scoring requires a declared range.",item=item)
                v=low+high-v
            values.append(v)
        vectors[item]=values
    complete=[i for i in range(len(rows)) if all(vectors[x][i] is not None for x in items)]
    matrix=[[vectors[x][i] for x in items] for i in complete]; n=len(matrix)
    item_stats=[]
    totals=[sum(row) for row in matrix]
    for j,item in enumerate(items):
        vals=[row[j] for row in matrix]; rest=[totals[i]-vals[i] for i in range(n)]
        item_stats.append({"question_id":item,"mean":mean(vals),"sd":math.sqrt(variance(vals)) if variance(vals) is not None else None,"corrected_item_total_correlation":correlation(vals,rest)})
    k=len(items); alpha=alpha_for(matrix)
    corr=[[1.0 if i==j else correlation([r[i] for r in matrix],[r[j] for r in matrix]) for j in range(k)] for i in range(k)] if n else []
    usable=bool(corr) and all(x is not None for row in corr for x in row)
    eigenvalues,eigenvectors=eigen_symmetric(corr) if usable else ([],[])
    loadings=[math.sqrt(max(0,eigenvalues[0]))*x for x in eigenvectors[0]] if eigenvalues else []
    uniqueness=[max(0,1-x*x) for x in loadings]; omega=(sum(loadings)**2)/(sum(loadings)**2+sum(uniqueness)) if loadings and sum(loadings)**2+sum(uniqueness)>0 else None
    for j,item in enumerate(item_stats): item["alpha_if_deleted"]=alpha_for([[v for c,v in enumerate(row) if c!=j] for row in matrix])
    warnings=[]
    if n<max(20,5*k): warnings.append({"code":"SMALL_SAMPLE","message":"Sample is small for stable scale or dimensionality estimates.","n":n})
    dimensionality={"status":"computed" if eigenvalues else "not_computed","eigenvalues":eigenvalues,"first_factor_loadings":dict(zip(items,loadings)),"method":"unrotated principal-component approximation from the Pearson correlation matrix","limitations":"Exploratory diagnostic; not confirmatory factor analysis."}
    return {"scale_id":definition.get("scale_id"),"n":n,"items":item_stats,"cronbach_alpha":alpha,"inter_item_correlations":corr,"mcdonald_omega":omega,"dimensionality":dimensionality,"warnings":warnings,"scoring":{"reverse_scored":sorted(reverse),"range":[low,high]}}

def compare(left,right):
    ld={x["question_id"]:x for x in response_diagnostics(left)["items"]}; rd={x["question_id"]:x for x in response_diagnostics(right)["items"]}; comparisons=[]
    for key in sorted(ld.keys()&rd.keys()):
        a,b=ld[key],rd[key]; comparisons.append({"question_id":key,"left_missing_rate":a["missing_rate"],"right_missing_rate":b["missing_rate"],"mean_difference":(b.get("mean")-a.get("mean")) if a.get("mean") is not None and b.get("mean") is not None else None,"left_distribution":a["option_utilization"],"right_distribution":b["option_utilization"]})
    return {"left_n":len(left),"right_n":len(right),"items":comparisons,"pooled":False,"equivalence_claimed":False}
