import numpy as np, itertools, time, sys
sys.path.insert(0,'.')
from evloader import *; from dayDP import day_dp, ACTIONS
D=np.load('demand.npy'); lam=D[9]
for cE in (1.0,0.0):
    w=dict(c0=1,cQ=1,cE=cE,c_op=2)
    best,_=day_dp(lam,w,3)
    # brute force exact counts m'=1,2,3 by enumeration of plans
    t0=time.time()
    for M in (1,2,3):
        bb=float('inf')
        for cuts in itertools.combinations(range(1,24),M-1):
            starts=(0,)+cuts
            for acts in itertools.product(ACTIONS,repeat=M):
                if any(acts[k]==acts[k+1] for k in range(M-1)): continue
                q,ld,t=run_plan(lam,list(zip(starts,acts)),w)
                c=cost_of(t,w)
                if c<bb: bb=c
        print('cE',cE,"m'",M,'brute',round(bb,4),'dp',round(best[M][0],4))
    print('brute time',round(time.time()-t0,1))
