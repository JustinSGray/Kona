import numpy as np

EPS = np.finfo(float).eps

def abs_sign(x, y):
    """
    Returns the value :math:`|x|\mathsf{sign}(y)`; used in GMRES, for example.

    Parameters
    ----------
    x : float
    y : float
    """
    return abs(x)*np.sign(y)

def CalcEpsilon(eval_at_norm, mult_by_norm):
    """
    Determines the perturbation parameter for forward-difference based
    matrix-vector products

    Parameters
    ----------
    eval_at_norm : float
        the norm of the vector at which the Jacobian-like matrix is evaluated
    mult_by_norm : float
        the norm of the vector that is being multiplied
    """
    if mult_by_norm < EPS*eval_at_norm or mult_by_norm < EPS:
        # multiplying vector is zero in a relative or absolute sense
        return 1.0
    else:
        if eval_at_norm < EPS*mult_by_norm:
            # multiplying vector dominates, so treat eval_at vector like zero
            return np.sqrt(EPS)/mult_by_norm
        else:
            return np.sqrt(EPS)*eval_at_norm/mult_by_norm

def eigen_decomp(A):
    """
    Returns the (sorted) eigenvalues and eigenvectors of the symmetric part of a
    square matrix.

    The matrix A is stored in dense format and is not assumed to be exactly
    symmetric.  The eigenvalues are found by calling np.linalg.eig, which is
    given 0.5*(A^T + A) as the input matrix, not A itself.

    Parameters
    ----------
    A : numpy 2d array
        matrix stored in dense format; not necessarily symmetric

    Returns
    -------
    eig_vals : numpy array
        the eigenvalues in ascending order
    eig_vecs : numpy 2d array
        the eigenvectors sorted appropriated
    """
    eig_vals, eig_vec = np.linalg.eig(0.5*(A + A.T))
    idx = eig_vals.real.argsort() # eig doesn't sort, so we have to
    inv_idx = np.empty(idx.shape[0], dtype=int)
    inv_idx[idx] = np.arange(idx.shape[0])
    return eig_vals[idx].real, eig_vec[:,inv_idx].real

def applyGivens(s, c, h1, h2):
    """
    Applies a Givens rotation to a 2-vector

    Parameters
    ----------
    s : float
        sine of the Givens rotation angle
    c : float
        cosine of the Givens rotation angle
    h1 : float
        first element of 2x1 vector being transformed
    h2 : float
        second element of 2x1 vector being transformed
    """
    temp = c*h1 + s*h2
    h2 = c*h2 - s*h1
    h1 = temp

def generateGivens(dx, dy, s, c):
    """
    Generates the Givens rotation matrix for a given 2-vector

    Based on givens() of SPARSKIT, which is based on p.202 of "Matrix
    Computations" by Golub and van Loan.

    Parameters
    ----------
    dx : float
        element of 2x1 vector being transformed
    dy : float
        element of 2x1 vector being set to zero
    s : float
        sine of the Givens rotation angle
    c : float
        cosine of the Givens rotation angle
    """
    if dx == 0.0 and dy == 0.0:
        c = 1.0
        s = 0.0
    elif abs(dy) > abs(dx):
        tmp = dx/dy
        dx = np.sqrt(1.0 + tmp*tmp)
        s = abs_sign(1.0/dx, dy)
        c = tmp*s
    elif abs(dy) <= abs(dx):
        tmp = dy/dx
        dy = np.sqrt(1.0 + tmp*tmp)
        c = abs_sign(1.0/dy, dx)
        s = tmp*c
    else:   # dx and/or dy must be invalid
        dx = 0.0
        dy = 0.0
        c = 1.0
        s = 0.0
    dx = abs(dx*dy)
    dy = 0.0

def solve_tri(A, b, x, lower=False):
    """
    Solve an upper-triangular system :math:`Ux = b` (lower=False) or
    lower-triangular system :math:`Lx = b` (lower=True)

    Parameters
    ----------
    A : numpy 2d array
        a triangular matrix
    b : numpy array
        the right-hand side of the system
    x : numpy array
        on exit, the solution
    lower : boolean
        if True, A stores an lower-triangular matrix; stores an upper-triangular
        matrix otherwise
    """

def solve_trust_reduced(H, g, radius):
    """
    Solves the reduced-space trust-region subproblem (the secular equation)

    This assumes the reduced space objective is in the form :math:`g^Tx +
    \frac{1}{2}x^T H x`.  Furthermore, the case :math:`g = 0` is not handled
    presently.

    Parameters
    ----------
    H : numpy 2d array
        reduced-space Hessian
    g : numpy array
        gradient in the reduced space
    radius : float
        trust-region radius

    Returns
    -------
    y : numpy array
        solution to reduced-space trust-region problem
    lam : float
        Lagrange multiplier value
    pred : float
        predicted decrease in the objective
    """
    if radius < 0.0:
        raise ValueError('trust-region radius must be nonnegative: radius = %f'%radius)
    if H.shape[0] != H.shape[1] != g.shape[0]:
        raise ValueError('reduced Hessian or gradient shape inconsistency')

    eig_vals, eig = eigenvalues(H)
    eigmin = eig[0]
    lam = 0.0
    if eigmin > 1e-12:
        # Hessian is semi-definite on span(Z), so solve for y and check if ||y||
        # is in trust region radius
        y, fnc, dfnc = secular_function(H, g, lam, radius)
        if (fnc < 0.0): # i.e. norm_2(y) < raidus
            # compute predicted decrease in objective and return
            pred = -y.dot(0.5*H.dot(y) + g)
            return y, lam, pred

    # if we get here, either the Hessian is semi-definite or ||y|| > radius

    # find upper bound for bracket, lam < lam_h
    max_brk = 20
    dlam = 0.1*max(-eigmin, EPS)
    lam_h = max(-eigmin, 0.0) + dlam
    y, fnc_h, dfnc = secular_function(H, g, lam_h, radius)
    for k in xrange(max_brk):
        if fnc_h > 0.0:
            break
        dlam *= 0.1
        lam_h = max(-eigmin, 0.0) + dlam
        y, fnc_h, dfnc = secular_function(H, g, lam_h, radius)

    # find lower bound for bracket, lam_l < lam
    dlam = np.sqrt(EPS)
    lam_l = max(-eigmin, 0.0) + dlam
    y, fnc_l, dfnc = secular_function(H, g, lam_l, radius)
    for k in xrange(max_brk):
        if fnc_l < 0.0:
            break
        dlam *= 100.0
        lam_l = max(-eigmin, 0.0) + dlam
        y, fnc_l, dfnc = secular_function(H, g, lam_l, radius)

    # Apply (safe-guarded) Newton's method to find lam
    max_Newt = 50
    lam = 0.5*(lam_l + lam_h)
    dlam_old = abs(lam_h - lam_l)
    dlam = dlam_old
    tol = np.sqrt(EPS)
    lam_tol = tol*dlam
    y, fnc, dfnc = secular_function(H, g, lam, radius)
    res0 = abs(fnc)
    for l in xrange(max_Newt):
        # check if y lies on the trust region; if so, exit loop
        if abs(fnc) < tol*res0 or abs(dlam) < lam_tol:
            break
        # choose safe-guarded step
        if ((lam - lam_h)*dfnc - fnc)*((lam - lam_l)*dfnc - fnc) > 0.0 or \
            abs(2.0*fnc) > abs(dlam_old*dfnc):
            #  use bisection if Newton-step is out of range or not decreasing fast
            dlam_old = dlam
            dlam = 0.5*(lam_h - lam_l);
            lam = lam_l + dlam;
            if (lam_l == lam):
                break
        else:
            # Newton-step is acceptable
            dlam_old = dlam
            dlam = fnc/dfnc
            temp = lam
            lam -= dlam
            if (temp == lam):
                break

        # evaluate function at new lambda
        y, fnc, dfnc = secular_function(H, g, lam, radius)
        if fnc < 0.0:
            lam_l = lam
        else:
            lam_h = lam

    if l+1 == max_Newt: # Newton's method failed to converge
        raise Exception("Newton's method failed to converge to a valid lambda")

    # compute predicted decrease in objective
    pred = -y.dot(0.5*H.dot(y) + g)
    return y, lam, pred

def secular_function(H, g, lam, radius)
    """
    Computes the secular-equation residual and its derivative for
    solve_trust_reduced.

    Parameters
    ----------
    H : numpy 2d array
        reduced-space Hessian
    g : numpy array
        gradient in the reduced space
    lam : float
        Lagrange multiplier value
    radius : float
        trust-region radius

    Returns
    -------
    y : numpy array
        the step
    fnc : float
        the value of the secular equation
    dfnc : float
        the derivative of the secular equation with respect to lam
    """
    if radius < 0.0:
        raise ValueError('trust-region radius must be nonnegative: radius = %f'%radius)
    if H.shape[0] != H.shape[1] != g.shape[0]:
        raise ValueError('reduced Hessian or gradient shape inconsistency')

    # perform Cholesky factorization, with regularization is necessary
    diag = max(1.0, lam)*0.01*EPS
    max_iter = 20
    for reg_iter in xrange(max_iter):
        H_hat = H + np.eye(H.shape[0])*diag
        try:
            L = np.linalg.cholesky(Hhat)
            break
        except LinAlgError:
            diag *= 100.0
    if reg_iter+1 == max_iter:
        raise Exception('Regularization of Cholesky factorization failed')

    work = np.empty(g.shape)
    y = -g.copy() # minus sign to move to rhs
    solve_tri(L, y, work, lower=True)
    solve_tri(L.T, work, y, lower=False)

    # compute the secular function
    norm_y = np.linalg.norm(y)
    fnc = 1.0/radius - 1.0/norm_y

    # compute its derivative
    solve_tri(L, y, work, lower=True)
    norm_work = np.linalg.norm(work)
    dfnc = norm_work/norm_y
    dfnc = -(dfnc*dfnc)/norm_y

    return y, fnc, dfnc

