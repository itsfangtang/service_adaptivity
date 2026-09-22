import json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
c=json.load(open('curves.json'))
def hull(J):
    pts=list(zip(range(1,len(J)+1),J)); h=[]
    for p in pts:
        while len(h)>=2 and (h[-1][1]-h[-2][1])*(p[0]-h[-2][0])>=(p[1]-h[-2][1])*(h[-1][0]-h[-2][0]): h.pop()
        h.append(p)
    return [p[0] for p in h]
plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans'})
fig,axes=plt.subplots(1,2,figsize=(11,4.1))
cols={'1':'#7f8c8d','10':'#1f5a94','20':'#2a9d8f','30':'#d95d5d'}
for ax,cE,ttl in ((axes[0],1,'(a) $c_E=1$ per unused space'),(axes[1],0,'(b) $c_E=0$')):
    for d in ('1','10','20','30'):
        J=c[f'cE{cE}_day{d}']['J']; H=hull(J); M=list(range(1,9))
        ax.plot(M,[j/1000 for j in J],'-',color=cols[d],lw=1.4,label=f'day {d}')
        for m,j in zip(M,J):
            ax.plot(m,j/1000,'o',ms=6,mfc=cols[d] if m in H else 'white',mec=cols[d],mew=1.4)
    ax.set_xlabel("Implemented stages, $m'$"); ax.set_ylabel("$J^{=}(m')$, thousand cost units")
    ax.set_title(ttl,loc='left'); ax.set_xticks(range(1,9)); ax.grid(axis='y',color='#e5e8eb')
    ax.spines[['top','right']].set_visible(False)
axes[0].legend(frameon=False,fontsize=9)
fig.text(0.01,0.01,'Filled: on the lower convex hull (chosen by some transition charge). Hollow: never chosen by a fixed charge.',fontsize=8.5,color='#555')
fig.tight_layout(rect=(0,0.04,1,1)); fig.savefig('fig_Jstar_M.pdf'); fig.savefig('fig_Jstar_M.png',dpi=160)
