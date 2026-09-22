import numpy as np, sys, time
sys.path.insert(0,'.')
from evloader import *
ACTIONS=[(2,8),(3,6),(3,8),(4,6),(4,8),(6,6),(6,8)]
def day_dp(lam, w, Mmax, T=24, prune=True):
    """Exact forward label-setting. Transitions permitted only at integer hours.
    Returns best[m] = (cost, plan) for plans with exactly m stages (adjacent actions differ)."""
    labels={}  # key (m,u,ld_offset_minutes) -> list of (q, cost, plan)
    for u in ACTIONS:
        labels.setdefault((1,u,0),[]).append((0.0,0.0,((0,u),)))
    stats=[]
    for h in range(T):
        new={}
        for (m,u,off),labs in labels.items():
            ld=h-off/60.0
            opts=[(m,u)] if h==0 else [(m,u)]+[(m+1,v) for v in ACTIONS if v!=u and m+1<=Mmax]
            for (m2,v) in opts:
                for (q,cost,plan) in labs:
                    q2,ld2,c,_=simulate_segment(lam,h,h+1,q,ld,v,w)
                    off2=int(round((h+1-ld2)*60))
                    p2=plan if v==u else plan+((h,v),)
                    new.setdefault((m2,v,off2),[]).append((q2,cost+cost_of(c,w),p2))
        # prune
        for k,labs in new.items():
            labs.sort(key=lambda x:(x[0],x[1]))
            kept=[]
            for L in labs:
                dom=False
                if prune:
                    for K in kept:
                        if K[0]<=L[0]+1e-9 and K[1]+w['cE']*(L[0]-K[0])<=L[1]+1e-9:
                            dom=True;break
                if not dom: kept.append(L)
            new[k]=kept
        labels=new
        stats.append(sum(len(v) for v in labels.values()))
    best={}
    for (m,u,off),labs in labels.items():
        for (q,cost,plan) in labs:
            if m not in best or cost<best[m][0]: best[m]=(cost,plan,q)
    return best,stats
if __name__=='__main__':
    D=np.load('demand.npy'); day=int(sys.argv[1]) if len(sys.argv)>1 else 9
    for cE in (1.0,0.0):
        w=dict(c0=1,cQ=1,cE=cE,c_op=2)
        t0=time.time(); best,stats=day_dp(D[day],w,5)
        print('cE',cE,'time',round(time.time()-t0,1),'max labels',max(stats))
        run=float('inf')
        for m in sorted(best):
            c,p,q=best[m]; run=min(run,c)
            print(f"  exactly m'={m}: {c:10.1f}  best<=M: {run:10.1f}  plan {[(s,u) for s,u in p]} cleared {q:.1f}")
