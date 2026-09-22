"""Section 5 figure: stage loss under a proportional shock vs a shape-changing shock (priced-departure form)."""
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
hour=np.arange(0,24,1/60)+1/120; dt=1/60
full=380+2050*np.exp(-0.5*((hour-8)/1.45)**2)+760*np.exp(-0.5*((hour-13)/3.1)**2)+2250*np.exp(-0.5*((hour-17.4)/1.65)**2)
mult=np.where((hour>=6)&(hour<10),0.350,np.where((hour>=10)&(hour<15),0.484,np.where((hour>=15)&(hour<19),0.391,0.383)))
def gap(lam,Mmax=6,k=10):
    lb=lam.reshape(-1,k).mean(1); N=len(lb); cs=np.concatenate([[0],np.cumsum(lb)])
    blk=lambda i,j:(j-i)*k*dt*np.sqrt((cs[j]-cs[i])/(j-i))
    F=np.full((Mmax+1,N+1),1e18); F[0,0]=0
    for m in range(1,Mmax+1):
        for j in range(1,N+1): F[m,j]=min((F[m-1,i]+blk(i,j) for i in range(m-1,j)),default=1e18)
    G=np.sum(np.sqrt(lb))*k*dt
    return np.array([F[m,N]-G for m in range(1,Mmax+1)])
base=gap(full); uni=gap(0.40*full); per=gap(full*mult)
res=dict(base=base.tolist(),uniform=(uni/base).tolist(),period=(per/base).tolist()); json.dump(res,open('s5_shape.json','w'),indent=1)
print(res)
plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans'})
fig,ax=plt.subplots(1,2,figsize=(10.5,3.6))
ax[0].plot(hour,full,color='#7f8c8d',lw=1.6,label='full-recovery profile')
ax[0].plot(hour,0.40*full,color='#1f5a94',lw=1.6,label='uniform factor 0.40')
ax[0].plot(hour,full*mult,color='#d95d5d',lw=1.6,label='period factors 0.35/0.48/0.39/0.38')
ax[0].set_xlabel('Hour of day'); ax[0].set_ylabel('Arrivals, passengers/h'); ax[0].set_title('(a) Two shocks of similar size',loc='left')
ax[0].legend(frameon=False,fontsize=8.5); ax[0].set_xticks(range(0,25,4)); ax[0].spines[['top','right']].set_visible(False)
M=np.arange(1,7); w=0.38
ax[1].bar(M-w/2,uni/base,w,color='#1f5a94',label='uniform factor 0.40')
ax[1].bar(M+w/2,per/base,w,color='#d95d5d',label='period factors')
ax[1].axhline(np.sqrt(0.40),color='#1f5a94',ls=':',lw=1); ax[1].text(6.45,np.sqrt(0.40)+0.01,r'$\sqrt{0.40}$',fontsize=9,color='#1f5a94')
ax[1].set_xlabel("Stages $m'$"); ax[1].set_ylabel('Stage loss relative to full profile'); ax[1].set_ylim(0,0.8)
ax[1].set_title('(b) Stage loss with optimal boundaries',loc='left'); ax[1].legend(frameon=False,fontsize=8.5,loc='lower left'); ax[1].spines[['top','right']].set_visible(False)
fig.tight_layout(); fig.savefig('fig_shape_shock.pdf'); fig.savefig('fig_shape_shock.png',dpi=150)
