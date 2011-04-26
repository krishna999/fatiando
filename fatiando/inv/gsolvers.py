# Copyright 2010 The Fatiando a Terra Development Team
#
# This file is part of Fatiando a Terra.
#
# Fatiando a Terra is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Fatiando a Terra is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Fatiando a Terra.  If not, see <http://www.gnu.org/licenses/>.
"""
Gradient solvers for inverse problems with optional regularization.

Implemented algorithms:

* Levemberg-Marquardt

Uses higher order functions (functions that take functions as arguments) to
implement generic solvers and to apply generic regularization.

Functions:

* :func:`fatiando.inv.gsolvers.marq`
    Solve the (non)-linear system f(p) = d with optional constraints
    (regularization) in a least-squares sense using the Levemberg-Marquardt
    algorithm.

"""
__author__ = 'Leonardo Uieda (leouieda@gmail.com)'
__date__ = 'Created 25-Apr-2011'


import logging


import numpy
from numpy import dot as dot_product
from numpy.linalg import solve as linsys_solver


import fatiando

log = logging.getLogger('fatiando.inv.gsolvers')
log.addHandler(fatiando.default_log_handler)


def linsolver(data, func, jac, reg_norm=None, reg_grad=None, reg_hess=None):

    # Make lambdas that do nothing if no regularization is given
    if reg_norm is None or reg_grad is None or reg_hess is None:
        reg_norm = lambda x: 0
        reg_grad = lambda x, g: g
        reg_hess = lambda x, h: h
    hessian = reg_hess(None, dot_product(jac.T, jac))
    estimate = linsys_solver(hessian, dot_product(jac.T, data))
    residuals = data - func(estimate)
    return {'estimate':estimate, 'residuals':residuals}



def marq(data, init, func, jac, lmstart=100, lmstep=10, maxsteps=20, maxit=100,
         tol=10**(-5), reg_norm=None, reg_grad=None, reg_hess=None):

    # Make lambdas that do nothing if no regularization is given
    if reg_norm is None or reg_grad is None or reg_hess is None:
        reg_norm = lambda x: 0
        reg_grad = lambda x, g: g
        reg_hess = lambda x, h: h

    residuals = data - func(init)
    rms = numpy.linalg.norm(residuals)**2
    reg = reg_norm(init)
    goals = [rms + reg]

    lm_param = lmstart
    next = init
    for iteration in xrange(maxit):
        prev = next
        jacobian = jac(prev)
        gradient = reg_grad(prev, -1*dot_product(jacobian.T, residuals))
        hessian = reg_hess(prev, dot_product(jacobian.T, jacobian))
        # Don't calculate things twice
        hessian_diag = hessian.diagonal()
        gradient *= -1
        # Enter the Marquardt loop to find the best step size
        stagnation = True
        for lm_iteration in xrange(maxsteps):
            delta = linsys_solver(hessian + lm_param*hessian_diag, gradient)
            next = prev + delta
            residuals = data - func(next)
            rms = numpy.linalg.norm(residuals)**2
            reg = reg_norm(next)
            goal = rms + reg
            if goal < goals[-1]:
                # Don't let lm_param be smaller than this
                if lm_param > 10**(-10):
                    lm_param /= lmstep
                stagnation = False
                break
            else:
                # Don't let lm_param be larger than this
                if lm_param < 10**(10):
                    lm_param *= lmstep
        if stagnation:
            next = prev
            log.warning("WARNING: convergence tolerance not achieved")
            break
        else:
            goals.append(goal)
            # Check if goal function decreases more than a threshold
            if abs((goals[-1] - goals[-2])/goals[-2]) <= tol:
                break
    result = {'estimate':next, 'residuals':residuals, 'goal_p_it':goals}
    return result
