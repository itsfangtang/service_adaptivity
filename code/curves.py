import numpy as np, sys, json, time
sys.path.insert(0,'.')
from evloader import *; from dayDP import day_dp
D=np.load('demand.npy')
out={}
for cE in (1.0,0.0):
    w=dict(c0=1,cQ=1,cE=cE,c_op=2)
    for day in (0,9,19,29):
        t0=time.time(); best,stats=day_dp(D[day],w,8)
        Js=[]
        for m in range(1,9):
            Js.append(best[m][0] if m in best else float('inf'))
        out[f"cE{int(cE)}_day{day+1}"]=dict(J=Js,plans={m:[(s,list(u)) for s,u in best[m][1]] for m in best},maxlabels=max(stats),sec=round(time.time()-t0,2))
        mv=[Js[k]-Js[k+1] for k in range(7)]
        print(f"cE={cE} day {day+1}: J*={[round(x,1) for x in Js]}\n   marginal={[round(x,1) for x in mv]} labels={max(stats)} t={time.time()-t0:.1f}s")
json.dump(out,open('curves.json','w'),indent=1)
