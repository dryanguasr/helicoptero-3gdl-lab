import numpy as np
from scipy.linalg import expm, solve_discrete_are
from scipy.signal import place_poles
from plant import nominal, rk4, jacobian, linearize, C

CREF = C[[0, 2]]  # internal outputs: elevation-positive-up and yaw


def discrete_system(p, e, dt):
    xe, ue, A, B = linearize(p, e)
    block = np.zeros((8, 8)); block[:6, :6] = A; block[:6, 6:] = B
    disc = expm(block * dt)
    return xe, ue, A, B, disc[:6, :6], disc[:6, 6:]


def require_stabilizable(A, B):
    for v in np.linalg.eigvals(A):
        if abs(v) >= 1 - 1e-9 and np.linalg.matrix_rank(
            np.column_stack([v*np.eye(len(A)) - A, B]), tol=1e-8
        ) < len(A):
            raise ValueError(
                'Equilibrio no estabilizable: cerca de empuje colectivo nulo se pierde '
                'autoridad lineal sobre yaw. Cambia el punto de operación o usa un controlador no lineal.'
            )


def require_controllable(A, B):
    blocks = [B]
    for _ in range(1, len(A)):
        blocks.append(A @ blocks[-1])
    if np.linalg.matrix_rank(np.hstack(blocks), tol=1e-8) < len(A):
        raise ValueError('El par linealizado (A,B) no es controlable en este punto de operación.')


def design_gain(c, A, B, augmented=False):
    method = c.get('gainMethod', 'lqr')
    if method == 'poles':
        require_controllable(A, B)
        poles = c['integralPoles'] if augmented else c['desiredPoles']
        z = np.exp(np.array(poles, dtype=float) * c['dt'])
        return place_poles(A, B, z).gain_matrix
    require_stabilizable(A, B)
    if augmented:
        Q = np.diag(c['lqrQ'] + [c['integralWeight']]*2)
    else:
        Q = np.diag(c['lqrQ'])
    R = np.diag(c['lqrR'])
    P = solve_discrete_are(A, B, Q, R)
    return np.linalg.solve(R + B.T@P@B, B.T@P@A)


def regulator_maps(A, B, C=CREF):
    """Steady-state maps x_ss = Nx r, u_ss = Nu r for deviations."""
    M = np.block([[A, B], [C, np.zeros((C.shape[0], B.shape[1]))]])
    rhs = np.vstack([np.zeros((A.shape[0], C.shape[0])), np.eye(C.shape[0])])
    sol = np.linalg.solve(M, rhs)
    return sol[:A.shape[0]], sol[A.shape[0]:]


def sat(x):
    return np.clip(x, -1.0, 1.0)


class Controller:
    def __init__(self, c):
        self.integral = np.zeros(3)
        self.update(c)

    def update(self, c):
        self.c = c; p = c['nominal']
        self.xe, self.ue, self.A, self.B, self.Ad, self.Bd = discrete_system(
            p, np.deg2rad(c['trim']), c['dt'])
        mode = c['controller']
        if mode in ['state', 'prefilter', 'integral']:
            self.K = design_gain(c, self.Ad, self.Bd)
            self.Nx, self.Nu = regulator_maps(self.A, self.B)
            self.N = self.Nu + self.K @ self.Nx
            self.poles = np.linalg.eigvals(self.Ad - self.Bd@self.K).tolist()
        if mode == 'integral':
            Aa = np.block([
                [self.Ad, np.zeros((6, 2))],
                [-CREF*c['dt'], np.eye(2)]
            ])
            Ba = np.vstack([self.Bd, np.zeros((2, 2))])
            Ka = design_gain(c, Aa, Ba, augmented=True)
            self.K = Ka[:, :6]
            # With xi_dot = r-y, standard u=-Ka*z becomes -Kx*x + Ki*xi.
            self.Ki = -Ka[:, 6:]
            self.poles = np.linalg.eigvals(Aa - Ba@Ka).tolist()

    def command(self, x, ref):
        c = self.c; p = c['nominal']; dt = c['dt']
        a, av, r, rv, y, yv = x; limited = False
        err = ref[:, 0] - x[[0, 4]]
        mode = c['controller']

        if mode in ['state', 'prefilter', 'integral']:
            dr = ref[:, 0] - CREF@self.xe
            self.old_integral = self.integral.copy()
            if mode == 'state':
                # x_d is the steady-state state map, but no reference input feedforward Nu*r.
                xd = self.xe + self.Nx@dr
                # Preserve trajectory velocity information for the two commanded outputs.
                xd[[1, 5]] = ref[:, 1]
                return self.ue - self.K@(x - xd), 0.0, limited
            if mode == 'prefilter':
                return self.ue - self.K@(x - self.xe) + self.N@dr, 0.0, limited
            self.integral[:2] += err*dt
            return self.ue - self.K@(x - self.xe) + self.Ki@self.integral[:2], 0.0, limited

        kp = np.array(c['kp']); kd = np.array(c['kd']); ki = np.array(c['ki'])
        self.old_integral = self.integral.copy()

        if mode == 'smc':
            lam = np.array(c['smcLambda']); eta = np.array(c['smcEta']); phi = np.array(c['smcPhi'])
            ea = ref[0, 0] - a; eda = ref[0, 1] - av
            ey = ref[1, 0] - y; edy = ref[1, 1] - yv
            sa = eda + lam[0]*ea; sy = edy + lam[1]*ey
            va = ref[0, 2] + lam[0]*eda + eta[0]*sat(sa/max(phi[0], 1e-5))
            vy = ref[1, 2] + lam[1]*edy + eta[1]*sat(sy/max(phi[1], 1e-5))
            c1 = (va + p['k_alpha']*np.sin(a) + p['b_alpha']*av)/p['a_alpha']
            c2 = (vy + p['b_psi']*yv)/(p['a_psi']*max(np.cos(a), .2))
            raw = np.arctan2(c2, c1)
            if raw > np.pi/2: raw -= np.pi
            if raw < -np.pi/2: raw += np.pi
            theta = np.clip(raw, -np.deg2rad(c['rollLimit']), np.deg2rad(c['rollLimit']))
            limited = bool(abs(raw-theta) > 1e-10)
            uc = c1/max(np.cos(theta), .2)
            er = theta-r; edr = -rv; sr = edr + lam[2]*er
            vr = lam[2]*edr + eta[2]*sat(sr/max(phi[2], 1e-5))
            ud = (vr + p['k_theta']*np.sin(r) + p['b_theta']*rv)/p['a_theta']
            return np.array([uc, ud]), float(theta), limited

        # Legacy comparison controllers: PID cascade and nonlinear dynamic allocation.
        self.integral[:2] += err*dt
        acc = ref[:, 2] + kp[:2]*err + kd[:2]*(ref[:, 1] - x[[1, 5]])
        if mode == 'pid':
            acc += ki[:2]*self.integral[:2]
            uc = (acc[0] + p['k_alpha']*np.sin(ref[0, 0]))/p['a_alpha']
            authority = p['a_psi']*uc*np.cos(a)
            raw = (acc[1]/authority) if abs(authority) > .05 else 0.
            limited = abs(authority) <= .05 and abs(acc[1]) > 1e-5
        else:
            c1 = (acc[0] + p['k_alpha']*np.sin(a) + p['b_alpha']*av)/p['a_alpha']
            c2 = (acc[1] + p['b_psi']*yv)/(p['a_psi']*max(np.cos(a), .2))
            raw = np.arctan2(c2, c1)
            if raw > np.pi/2: raw -= np.pi
            if raw < -np.pi/2: raw += np.pi
            uc = c1
        theta = np.clip(raw, -np.deg2rad(c['rollLimit']), np.deg2rad(c['rollLimit']))
        limited = bool(limited or abs(raw-theta) > 1e-10)
        if mode == 'nonlinear': uc /= max(np.cos(theta), .2)
        self.integral[2] += (theta-r)*dt
        rd = kp[2]*(theta-r) - kd[2]*rv
        if mode == 'pid': rd += ki[2]*self.integral[2]
        ud = (rd + p['k_theta']*np.sin(r) + (p['b_theta']*rv if mode == 'nonlinear' else 0))/p['a_theta']
        return np.array([uc, ud]), float(theta), limited

    def antiwindup(self, limited):
        if limited:
            self.integral = self.old_integral.copy()


class Observer:
    """Receives only measured angles and nominally reconstructed commanded input."""
    def __init__(self, c):
        self.x = np.zeros(6); self.P = np.eye(6)*.03; self.previous_y = None; self.update(c)

    def update(self, c):
        self.c = c
        if c['observer'] == 'luenberger':
            self.xe, self.ue, _, _, self.Ad, self.Bd = discrete_system(c['nominal'], np.deg2rad(c['trim']), c['dt'])
            poles = np.exp(-c['observerSpeed']*np.array([1,1.2,1.4,1.6,1.8,2])*c['dt'])
            self.L = place_poles(self.Ad.T, (C@self.Ad).T, poles).gain_matrix.T

    def step(self, y, u):
        c = self.c; dt = c['dt']; mode = c['observer']
        if mode == 'filtered':
            v = np.zeros(3) if self.previous_y is None else (y-self.previous_y)/dt
            blend = 1-np.exp(-dt*c['filterHz']*2*np.pi)
            self.x[::2] = y; self.x[1::2] += blend*(v-self.x[1::2]); self.previous_y = y.copy()
        elif mode == 'luenberger':
            prior = self.xe + self.Ad@(self.x-self.xe) + self.Bd@(u-self.ue)
            self.x = prior + self.L@(y-C@prior)
        elif mode == 'ekf':
            f = lambda x: rk4(lambda z,v:nominal(z,v,c['nominal']), x, u, dt)
            F = jacobian(f, self.x); xp = f(self.x)
            Q = np.diag([2e-6,8e-4,2e-6,8e-4,2e-6,1.2e-3])*c['ekfQ']*(dt/.02)
            R = np.diag(np.deg2rad(c['ekfR'])**2)
            P = F@self.P@F.T+Q; S = C@P@C.T+R; L = np.linalg.solve(S, C@P).T
            self.x = xp + L@(y-C@xp); J = np.eye(6)-L@C
            self.P = J@P@J.T + L@R@L.T
        return self.x.copy()
