"""Final fit with the chosen hypotheses (FLAG=ignore, HUE_POS=post, no extra stages) -> cache/params.npz"""
import io
import os

import numpy as np
from scipy.optimize import least_squares

import fit

W_REL = 0.5
r = least_squares(fit.residuals, fit.x0(), args=('ignore', W_REL), method='trf', max_nfev=3000, x_scale='jac')
np.savez(os.path.join(fit.HERE, 'cache', 'params.npz'), x=r.x, idx=np.array([(k, v.start, v.stop) for k, v in fit.IDX.items()], dtype=object))
s = io.StringIO(); fit.report(r.x, 'ignore', s)
open(os.path.join(fit.HERE, 'cache', 'fit_report.txt'), 'w').write(s.getvalue())
pp = fit.params(r.x)
print('cost', r.cost, 'nfev', r.nfev)
print('theta', np.round(np.rad2deg(pp['hue']['theta']) % 360, 1), 'alpha deg/u', np.round(np.rad2deg(pp['hue']['alpha']), 3),
      'beta %/u', np.round(100 * pp['hue']['beta'], 3), 'w', np.round(pp['hue']['w'], 2))
print('boost', np.round(np.exp(pp['boost']), 3), 'satk', round(pp['satk'], 4))
