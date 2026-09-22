"""Event-based loader (Section 2 v25) on hourly piecewise-constant arrivals.
Departures continue from the last departure with the headway of the action in force
just after that departure; capacity of a departure uses the action in force at its time.
Day starts empty at t=0 with a departure phase of 0 (first departure at 0+headway).
Queue left after the last departure <= T is cleared at zero operating cost (v21 rule);
waiting up to T is charged."""
import numpy as np
KAPPA=56.25
def cum_arr(lam, t):
    # cumulative arrivals from 0 to t (hours), lam hourly
    h=int(np.floor(t)); h=min(h,len(lam)-1) if t<len(lam) else len(lam)
    if t>=len(lam): return lam.sum()
    return lam[:h].sum()+lam[h]*(t-h)
def area_arr(lam, a, b):
    # integral_a^b (A(t)-A(a)) dt for piecewise-constant lam
    tot=0.0; t=a; Aacc=0.0
    while t<b-1e-12:
        h=int(np.floor(t+1e-12)); nxt=min(b,h+1)
        dt=nxt-t; tot+=Aacc*dt+lam[h]*dt*dt/2; Aacc+=lam[h]*dt; t=nxt
    return tot
def simulate_segment(lam, t0, t1, q, last_dep, u, w, T=24.0):
    """Run from t0 to t1 with action u=(f,n) in force. State: q = passengers waiting at t0
    (after any departure at t0), last_dep = time of last departure (<= t0).
    Returns q_at_t1, last_dep_new, costs dict. Departures in (t0, t1] use u."""
    f,n=u; H=1.0/f; C=KAPPA*n
    c=dict(wait0=0.0,waitQ=0.0,unused=0.0,op=0.0,deps=0,boarded=0.0)
    # q at t0 split: Q (left behind) vs P0 (arrived since last dep); track P0 separately
    t=t0; P=q
    # number of arrivals since last departure up to t0 = P0_at_t0
    P0=cum_arr(lam,t0)-cum_arr(lam,last_dep) if last_dep<t0 else 0.0
    P0=min(P0,P); Q=P-P0
    nd=last_dep+H
    while nd<=t1+1e-9:
        # wait from t to nd
        a=area_arr(lam,t,nd); newarr=cum_arr(lam,nd)-cum_arr(lam,t)
        c['wait0']+=P0*(nd-t)+a; c['waitQ']+=Q*(nd-t)
        P0+=newarr; P=P0+Q
        B=min(P,C); E=C-B
        c['boarded']+=B; c['unused']+=E; c['op']+=w['c_op']*n; c['deps']+=1
        # FIFO: backlog Q boards first
        bQ=min(Q,B); Q-=bQ; P0-=(B-bQ); Q+=P0; P0=0.0   # everyone left becomes backlog
        t=nd; last_dep=nd; nd=last_dep+H
    a=area_arr(lam,t,t1); newarr=cum_arr(lam,t1)-cum_arr(lam,t)
    c['wait0']+=P0*(t1-t)+a; c['waitQ']+=Q*(t1-t); P0+=newarr
    return P0+Q, last_dep, c, (P0,Q)
def cost_of(c,w): return w['c0']*c['wait0']+w['cQ']*c['waitQ']+w['cE']*c['unused']+c['op']
def run_plan(lam, plan, w, t0=0.0, t1=24.0, q=0.0, last_dep=0.0):
    """plan: list of (start_hour, (f,n)), sorted; action in force from start."""
    tot=dict(wait0=0,waitQ=0,unused=0,op=0,deps=0,boarded=0)
    for k,(s,u) in enumerate(plan):
        e=plan[k+1][0] if k+1<len(plan) else t1
        a=max(s,t0); b=min(e,t1)
        if b<=a: continue
        q,last_dep,c,_=simulate_segment(lam,a,b,q,last_dep,u,w)
        for kk in tot: tot[kk]+=c[kk]
    return q,last_dep,tot
