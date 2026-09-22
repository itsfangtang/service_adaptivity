import numpy as np, sys
sys.path.insert(0,'.')
from evloader import *; from dayDP import ACTIONS
def dp_from(lam,w,h0,q0,ld0,u0,m0,Mmax,T=24):
    labels={(m0,u0,int(round((h0-ld0)*60))):[(q0,0.0,((h0,u0),))]}
    for h in range(h0,T):
        new={}
        for (m,u,off),labs in labels.items():
            ld=h-off/60.0
            opts=[(m,u)]+[(m+1,v) for v in ACTIONS if v!=u and m+1<=Mmax]   # R08: a change is admissible at the first continuation node as well
            for (m2,v) in opts:
                for (q,cost,plan) in labs:
                    q2,ld2,c,_=simulate_segment(lam,h,h+1,q,ld,v,w)
                    new.setdefault((m2,v,int(round((h+1-ld2)*60))),[]).append((q2,cost+cost_of(c,w),plan if v==u else plan+((h,v),)))
        for k,labs in new.items():
            labs.sort(key=lambda x:(x[0],x[1])); kept=[]
            for L in labs:
                if not any(K[0]<=L[0]+1e-9 and K[1]+w['cE']*(L[0]-K[0])<=L[1]+1e-9 for K in kept): kept.append(L)
            new[k]=kept
        labels=new
    return min(((c,p,m) for (m,u,o),labs in labels.items() for (q,c,p) in labs),key=lambda x:x[0])
D=np.load('demand.npy'); lam=D[9]
A=[(0,(2,8)),(6,(4,6)),(20,(2,8))]
for cE in (1.0,0.0):
    w=dict(c0=1,cQ=1,cE=cE,c_op=2)
    q8,ld8,t08=run_plan(lam,A,w,0,8); pre=cost_of(t08,w)
    res={}
    for lab,u,m in [('keep',(4,6),2),('switch',(6,6),3)]:
        q9,ld9,c,_=simulate_segment(lam,8,9,q8,ld8,u,w); l=cost_of(c,w)
        for Mmax in (3,4):
            cv,p,mf=dp_from(lam,w,9,q9,ld9,u,m,Mmax)
            res[(lab,Mmax)]=(l,cv,p)
            print(f"cE={cE} {lab:6s} M<={Mmax}: l(08-09)={l:8.1f} J9*={cv:9.1f} l+J9={l+cv:9.1f} day total={pre+l+cv:9.1f} cont plan={[(s,u) for s,u in p]}")
    print('  pre-08 cost',round(pre,1))
