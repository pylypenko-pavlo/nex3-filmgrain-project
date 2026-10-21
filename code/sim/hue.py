"""Hue-table stage model: 4 hue axes in the CbCr plane (codes 0..1023 domain, after tone curve).

A colour vector v lying between adjacent axes j, j+1 is decomposed v = a*u_j + b*u_{j+1} (a, b >= 0);
output v' = a*s_j*R(r_j)u_j + b*s_{j+1}*R(r_{j+1})u_{j+1}   (piecewise-linear 'colour correction by hue area').
r_j = alpha_j * (Q0_j + w2*Q2_j + w4*Q4_j)   (rotation, radians)
log s_j = beta_j * (Q1_j + w3*Q3_j + w5*Q5_j) (saturation)
T here is the record DELTA vs the native Standard record (see fit.delta_table).
This is an EMPIRICAL model fitted on chart experiments, not decoded from firmware.
"""
import numpy as np

NP = 4 + 4 + 4 + 4  # theta, alpha, beta, (w2, w4, w3, w5)


def unpack(v):
    v = np.asarray(v, float)
    return dict(theta=v[0:4], alpha=v[4:8], beta=v[8:12], w=v[12:16])


def axes_params(T, hp):
    T = np.asarray(T, float)
    w2, w4, w3, w5 = hp['w']
    rot = hp['alpha'] * (T[0] + w2 * T[2] + w4 * T[4])
    lgs = hp['beta'] * (T[1] + w3 * T[3] + w5 * T[5])
    return rot, np.exp(lgs)


def _sector(ang, theta):
    """index j of the sector [theta_j, theta_{j+1}) containing ang (theta sorted, cyclic)."""
    d = (ang[..., None] - theta[None, :]) % (2 * np.pi)
    return np.argmin(d, axis=-1)


def apply(cbcr, T, hp, inverse=False):
    """cbcr: (...,2). Returns transformed (or inverse-transformed) cbcr."""
    theta = np.asarray(hp['theta']) % (2 * np.pi)
    order = np.argsort(theta); th = theta[order]
    rot, s = axes_params(T, hp)
    rot, s = rot[order], s[order]
    U = np.stack([np.cos(th), np.sin(th)], -1)                    # input axes
    V = np.stack([s * np.cos(th + rot), s * np.sin(th + rot)], -1)  # output axes
    if inverse:
        U, V = V, U
        ang_axes = np.arctan2(U[:, 1], U[:, 0]) % (2 * np.pi)
        order2 = np.argsort(ang_axes)
        if not np.array_equal(order2, np.argsort(np.arange(4))) and not np.array_equal(np.roll(order2, -np.argmin(order2)), np.arange(4)):
            pass  # axes crossed; inverse still computed sector-wise below (approximate)
        th_in = ang_axes
    else:
        th_in = th
    x = cbcr.reshape(-1, 2)
    ang = np.arctan2(x[:, 1], x[:, 0]) % (2 * np.pi)
    j = _sector(ang, th_in); k = (j + 1) % 4
    A = np.stack([U[j], U[k]], -1)      # (n,2,2) columns u_j, u_k
    ab = np.linalg.solve(A, x[..., None])[..., 0]
    out = ab[:, :1] * V[j] + ab[:, 1:] * V[k]
    return out.reshape(cbcr.shape)
