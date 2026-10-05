"""Eight-neighbour stochastic CA """
import math
import random
import numpy as np

WINDS = {'none': (0, 0), 'E': (0, 1), 'N': (-1, 0), 'W': (0, -1), 'S': (1, 0)}


def simulate(original, height, width, ignition, seed, wind='none', steps=150,
             edge=50, p0=.2, residual=.2, consumption=.2,
             wind_strength=.5, slope_strength=1., frame_callback=None, bands=None, protection_col=None, rectangles=None):
    """Fix the near edge; widen away from ignition """
    n = len(original)
    if not (0 <= width <= n-edge and 0 <= ignition[1] < edge):
        raise ValueError('Band or ignition outside allowed region')
    segments = [(edge,width)] if bands is None else list(bands)
    mask = np.zeros((n,n),dtype=bool)
    for start,band_width in segments:
        if start < edge or band_width < 1 or start+band_width > n:
            if bands is None and band_width == 0: continue
            raise ValueError('Invalid band geometry')
        if mask[:,start:start+band_width].any(): raise ValueError('Overlapping bands')
        mask[:,start:start+band_width] = True
    if rectangles is not None:
        # Rectangles: row, column, length, width 
        mask[:] = False
        segments = []
        for row,col,length,bw in rectangles:
            if min(row,col,length-1,bw-1)<0 or row+length>n or col<edge or col+bw>n:
                raise ValueError('Invalid treatment rectangle')
            if mask[row:row+length,col:col+bw].any(): raise ValueError('Overlapping rectangles')
            mask[row:row+length,col:col+bw]=True
    far_edge = max((c+w for r,c,l,w in rectangles),default=edge) if rectangles is not None else max((s+w for s,w in segments),default=edge)
    adjacent = np.zeros_like(mask)
    if rectangles is not None:
        # All eight surrounding cells, including segment tips 
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                source=(slice(max(0,-dr),min(n,n-dr)),slice(max(0,-dc),min(n,n-dc)))
                target=(slice(max(0,dr),min(n,n+dr)),slice(max(0,dc),min(n,n+dc)))
                adjacent[target] |= mask[source]
        adjacent &= ~mask
    if protection_col is not None and not (far_edge <= protection_col < n):
        raise ValueError('Protection line must be beyond every band')
    fuel = original.copy()
    fuel[mask] *= residual
    removed = float(original.sum()-fuel.sum())
    if fuel[ignition] <= 0:
        raise ValueError('Ignition needs positive fuel')
    state = np.zeros((n,n), dtype=np.uint8)
    state[ignition] = 1
    # Precompute target probabilities; unburned fuel stays constant.
    links = []
    wr,wc = WINDS[wind]
    for dr in (-1,0,1):
        for dc in (-1,0,1):
            if dr == dc == 0:
                continue
            source = (slice(max(0,-dr),min(n,n-dr)),slice(max(0,-dc),min(n,n-dc)))
            target = (slice(max(0,dr),min(n,n+dr)),slice(max(0,dc),min(n,n+dc)))
            distance = math.hypot(dr,dc)
            slope = np.arctan2(height[target]-height[source],distance)
            prob = np.clip(p0*fuel[target]/distance*np.exp(wind_strength*(dr*wr+dc*wc)/distance+slope_strength*slope),0,1)
            links.append((source,target,prob))
    contact = cross = None
    history = []
    total = 0.
    far = far_edge
    band_contact = [None]*len(segments)
    band_cross = [None]*len(segments)
    arrival = None
    # Width 0 is a no-treatment reference 
    for t in range(steps+1):
        if contact is None and (np.any(state[adjacent]>0) if rectangles is not None else np.any(state[:,edge-1] > 0)):
            contact = t
        if cross is None and far < n and np.any(state[:,far] > 0):
            cross = t
        if protection_col is not None:
            for i,(start,bw) in enumerate(segments):
                if band_contact[i] is None and np.any(state[:,start-1]>0): band_contact[i]=t
                if band_cross[i] is None and start+bw<n and np.any(state[:,start+bw]>0): band_cross[i]=t
            if arrival is None and np.any(state[:,protection_col]>0): arrival=t
        active = int(np.count_nonzero(state == 1))
        history.append(dict(step=t,total_burned=total,burning_cells=active))
        if protection_col is not None:
            history[-1]['protected_burned_fraction']=float(np.mean(state[:,protection_col:]>0))
        # Optional visual output must not affect RNG 
        if frame_callback is not None:
            frame_callback(state)
        if t == steps or active == 0:
            break
        burning = state == 1
        survival = np.ones((n,n))
        for source,target,prob in links:
            survival[target] *= np.where(burning[source],1-prob,1.)
        # Follow V2's seed-by-step draws and synchronous updates.
        rng = random.Random(seed*1000003+t+1)
        draws = np.fromiter((rng.random() for _ in range(n*n)),float,n*n).reshape(n,n)
        ignite = (state == 0) & (draws < 1-survival)
        used = np.minimum(fuel,consumption)*burning
        fuel -= used
        total += float(used.sum())
        exhausted = burning & (fuel < 1e-12)
        fuel[exhausted] = 0.
        state[exhausted] = 2
        state[ignite] = 1
    # Unreached and time-censored runs must not count as successful barriers.
    status = ('crossed' if cross is not None else 'not_reached' if contact is None
              else 'blocked_extinct' if active == 0 else 'not_crossed_yet')
    assert abs(float(original.sum())-removed-total-float(fuel.sum())) < 1e-6
    result = dict(contact_step=contact,cross_step=cross,
                crossing_delay=None if contact is None or cross is None else cross-contact,
                status=status,total_burned=total,fuel_removed=removed,
                burning_cells=active,end_step=t)
    if protection_col is not None:
        result.update(protection_arrival=arrival,protected_burned_fraction=float(np.mean(state[:,protection_col:]>0)),
                      band_contact_steps=band_contact,band_cross_steps=band_cross)
    return result,history
