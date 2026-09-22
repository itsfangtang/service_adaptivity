"""Table (Section 4.1): exact excess waiting L(m') of the stage-partition loss, modeled day 10."""
import numpy as np
lamh=np.load('demand.npy')[9]
tm=np.arange(24)+0.5; g=np.linspace(0,24,24*60+1); gc=(g[:-1]+g[1:])/2; dt=1/60
lam=np.interp(gc,tm,lamh); c0=1.0; n=96
k=10; lb=lam.reshape(-1,k).mean(1); N=len(lb); cs=np.concatenate([[0],np.cumsum(lb)])
blk=lambda i,j:(j-i)*k*dt*np.sqrt((cs[j]-cs[i])/(j-i))
F=np.full((9,N+1),1e18); F[0,0]=0
for m in range(1,9):
    for j in range(1,N+1):
        F[m,j]=min((F[m-1,i]+blk(i,j) for i in range(m-1,j)),default=1e18)
S=np.sum(np.sqrt(lb))*k*dt
print('Newell optimum',round(c0*S**2/(2*n),1))
L=[c0/(2*n)*(F[m,N]**2-S**2) for m in range(1,9)]
print("L(m')",[round(x,1) for x in L]); print('gains',[round(L[i]-L[i+1],1) for i in range(7)])
