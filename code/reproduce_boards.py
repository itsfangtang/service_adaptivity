"""Checks the event loader against the archived Board numbers (Sections 2-3)."""
import numpy as np
from evloader import *
D=np.load('demand.npy'); w=dict(c0=1,cQ=1,cE=1,c_op=2); lam=D[9]
A=[(0,(2,8)),(6,(4,6)),(20,(2,8))]
q,ld,_=run_plan(lam,A,w,0,8); print('queue after 08:00 departure, day 10 plan A:',round(q,6),'(Board 16: 419.814791)')
for u,ref in [((4,6),(906.502059,831.908425)),((6,6),(231.502059,494.408425))]:
    q9,_,c,_=simulate_segment(lam,8,9,q,ld,u,w); print(u,'09:00 queue',round(q9,6),'waiting',round(c['wait0']+c['waitQ'],6),'ref',ref)
q10,ld10,_=run_plan(lam,A,w,0,10); print('queue at 10:00:',round(q10,2),'(Fig. 5: about 988)')
for f,ref in [(4,137.4),(6,91.6)]:
    _,_,c,_=simulate_segment(D[0],8,9,0.0,8.0,(f,6),w); print('day 1, 08-09, f=',f,'waiting',round(c['wait0']+c['waitQ'],2),'ref',ref)
