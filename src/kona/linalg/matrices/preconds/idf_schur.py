import copy

from kona.linalg.vectors.common import PrimalVector, StateVector, DualVector
from kona.linalg.matrices.common import IdentityMatrix
from kona.linalg.matrices.hessian.basic import BaseHessian
from kona.linalg.matrices.hessian import TotalConstraintJacobian
from kona.linalg.solvers.krylov import FGMRES

class ReducedSchurPreconditioner(BaseHessian):
    """
    An IDF-Schur preconditioner designed to precondition the KKT system for
    multidisciplinary design optimization problems formulated using the IDF
    architecture.

    The preconditioner solves a system defined by the matrix:

    .. math::
        \\begin{bmatrix} I && A^T \\\\ A && 0 \\end{bmatrix}

    This solution is used as the preconditioner to the complete KKT system.

    Unlike the complete KKT system, this solution can be performed using FGMRES.

    Attributes
    ----------
    krylov : KrylovSolver
    cnstr_jac : TotalConstraintJacobian

    """
    def __init__(self, vector_factories, optns={}):
        super(ReducedSchurPreconditioner, self).__init__(
            vector_factories, optns)

        # get references to individual factories
        self.primal_factory = None
        self.state_factory = None
        self.dual_factory = None
        for factory in self.vec_fac:
            if factory._vec_type is PrimalVector:
                self.primal_factory = factory
            elif factory._vec_type is StateVector:
                self.state_factory = factory
            elif factory._vec_type is DualVector:
                self.dual_factory = factory

        self.primal_factory.request_num_vectors(2)

        # initialize the internal FGMRES solver
        krylov_out = copy.deepcopy(self.out_file)
        krylov_out.file = None # this silences the internal Krylov solver
        krylov_optns = {'out_file' : krylov_out}
        self.krylov = FGMRES(self.primal_factory, krylov_optns)

        # initialize an identity preconditioner
        self.eye = IdentityMatrix()
        self.precond = self.eye.product

        # initialize the total constraint jacobian block
        self.cnstr_jac = TotalConstraintJacobian(vector_factories)

        # set misc settings
        self.diag = 0.0
        self._allocated = False

    def _jac_prod(self, in_vec, out_vec):
        self.cnstr_jac.approx.product(in_vec, out_vec)

    def _jac_prod_T(self, in_vec, out_vec):
        self.cnstr_jac.T.approx.product(in_vec, out_vec)

    def linearize(self, at_KKT, at_state):
        # store references to the evaluation point
        self.at_design = at_KKT._primal
        self.at_state = at_state
        self.at_dual = at_KKT._dual
        self.at_KKT = at_KKT

        # linearize the constraint jacobian
        self.cnstr_jac.linearize(self.at_design, self.at_state)

        # if this is the first linearization, allocate some useful vectors
        if not self._allocated:
            self.design_work = []
            for i in xrange(2):
                self.design_work.append(self.primal_factory.generate())

    def product(self, in_vec, out_vec):
        # do some aliasing to make life easier
        design_work = self.design_work

        # set solver settings
        rel_tol = 0.01
        self.krylov.rel_tol = rel_tol
        self.krylov.check_res = False

        out_vec.equals(0.0)
        design_work[0].equals(in_vec._primal)
        design_work[0].restrict_to_target()

        # Step 1: Solve (dC/dy)^T in_dual = (u_design)_(target subspace)
        self.cnstr_jac.restrict_to_target()
        design_work[1].equals(in_vec._primal)
        design_work[1].restrict_to_target()
        design_work[0].equals(0.0)
        self.krylov.solve(
            self._jac_prod_T, design_work[1], design_work[0], self.precond)
        out_vec._dual.convert(design_work[0])

        # Step 2: Compute (out_design)_(design subspace) =
        # (in_design)_(design subspace) - (dC/dx)^T * out_dual
        self.cnstr_jac.restrict_to_design()
        self._jac_prod_T(design_work[0], out_vec._primal)
        fac = 1.0/(1.0 + self.diag)
        out_vec._primal.equals_ax_p_by(
            -fac, out_vec._primal, fac, in_vec._primal)
        out_vec._primal.restrict_to_design()

        # Step 3: Solve (dC/dy) (out_design)_(target subspace) =
        # in_dual - (dC/dx) (out_design)_(design subspace)
        self._jac_prod(out_vec._primal, design_work[0])
        design_work[1].convert(in_vec._dual)
        design_work[0].equals_ax_p_by(-1., design_work[0], 1., design_work[1])
        design_work[1].equals(0.0)
        self.cnstr_jac.restrict_to_target()
        self.krylov.solve(
            self._jac_prod, design_work[0], design_work[1], self.precond)
        out_vec._primal.plus(design_work[1])
