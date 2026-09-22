"""Table (Section 4.2) / Appendix A.2: one-stage losses with steady drift, fluid queue."""
import numpy as np
def run(M,mode,sign,N=200000,T=1.0,a=1.0):
    dt=T/N; tc=(np.arange(N)+0.5)*dt; lam=10+sign*a*tc; e=np.linspace(0,T,M+1); st=np.minimum((tc*M/T).astype(int),M-1)
    lv={'start':10+sign*a*e[:-1],'mid':10+sign*a*(e[:-1]+e[1:])/2,'max':np.maximum(10+sign*a*e[:-1],10+sign*a*e[1:])}[mode]
    Q=W=E=0.0
    for l,m in zip(lam,lv[st]):
        x=Q+(l-m)*dt
        if x>=0: Q=x
        else: E-=x; Q=0.0
        W+=Q*dt
    return W,E
for sign in (1,-1):
    for mode in ('max','mid','start'):
        print('rising' if sign>0 else 'falling',mode,[tuple(round(v,6) for v in run(M,mode,sign)) for M in (4,8,16)])
