"""Section 6 exhibit: value of (M,N) under three disruption magnitudes.
Restricted-pool nested evaluation: candidate daily plans = exact day-optimal plans (M<=5) of every day;
each plan evaluated on every day with the event loader; exact day-to-day partition into N blocks over that pool."""
import numpy as np, itertools, json, sys
from evloader import run_plan, cost_of
from dayDP import day_dp
def demand(delta, days=30, seed=19):
    rng=np.random.default_rng(seed); hour=np.linspace(0.5,23.5,24)
    full=380+2050*np.exp(-0.5*((hour-8)/1.45)**2)+760*np.exp(-0.5*((hour-13)/3.1)**2)+2250*np.exp(-0.5*((hour-17.4)/1.65)**2)
    d=np.arange(days); r=np.exp(-d/10.5)
    noise=rng.normal(0,0.025,(days,24))
    return (1-delta*r)[:,None]*full[None,:]*(1+noise)
w=dict(c0=1,cQ=1,cE=1.0,c_op=2)
def plan_list(p): return [(s,tuple(u)) for s,u in p]
out={}
for delta in (0.3,0.58,0.8):
    D=demand(delta); nd=D.shape[0]
    pool={}
    for d in range(nd):
        best,_=day_dp(D[d],w,5)
        for m,(c,p,q) in best.items(): pool[tuple(p)]=m
    plans=list(pool); P=len(plans); stages=np.array([len(p) for p in plans])
    C=np.array([[cost_of(run_plan(D[d],list(p),w)[2],w) for d in range(nd)] for p in plans])
    cs=np.concatenate([np.zeros((P,1)),C.cumsum(1)],1)
    res={}
    for Mc in range(1,6):
        mask=stages<=Mc
        blk=lambda r,d: (cs[mask,d]-cs[mask,r]).min()
        B=np.array([[blk(r,d) if d>r else np.inf for d in range(nd+1)] for r in range(nd+1)])
        V=np.full((5,nd+1),np.inf); V[0,0]=0
        for n in range(1,5):
            for d in range(1,nd+1):
                V[n,d]=min(V[n-1,r]+B[r,d] for r in range(d))
        for N in range(1,5): res[(Mc,N)]=V[:N+1,nd].min()
    J11=res[(1,1)]
    print(f"delta={delta}: pool={P} plans; J(1,1)={J11:.0f}")
    for Mc in range(1,6):
        print('  M<=%d'%Mc,' '.join(f"N<={N}: {100*(J11-res[(Mc,N)])/J11:5.1f}%" for N in range(1,5)))
    out[str(delta)]={f"{k[0]},{k[1]}":v for k,v in res.items()}
json.dump(out,open('s6_nested.json','w'),indent=1)
