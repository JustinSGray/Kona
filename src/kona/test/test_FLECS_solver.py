import unittest

import numpy

from kona.linalg.solvers.krylov import FLECS
from kona.linalg.vectors.composite import ReducedKKTVector
from kona.linalg.matrices.common import IdentityMatrix
from kona.user import UserSolver
from kona.linalg.memory import KonaMemory

class FLECSSolverTestCase(unittest.TestCase):

    def setUp(self):
        solver = UserSolver(2,0,2)
        self.km = KonaMemory(solver)
        self.pf = self.km.primal_factory
        self.pf.request_num_vectors(2)
        self.df = self.km.dual_factory
        self.df.request_num_vectors(2)
        optns = {
            'max_iter' : 10,
            'rel_tol' : 1e-6,
        }
        self.krylov = FLECS([self.pf, self.df], optns)
        self.km.allocate_memory()

        self.x_prim = self.pf.generate()
        self.x_dual = self.df.generate()
        self.x = ReducedKKTVector(self.x_prim, self.x_dual)
        self.b_prim = self.pf.generate()
        self.b_dual = self.df.generate()
        self.b = ReducedKKTVector(self.b_prim, self.b_dual)
        self.A = numpy.array([[4, 3, 2, 1],
                              [3, 4, 3, 2],
                              [2, 3, 0, 0],
                              [1, 2, 0, 0]])

        self.precond = IdentityMatrix()

    def mat_vec(self, in_vec, out_vec):
        in_prim = in_vec._primal._data.data
        in_dual = in_vec._dual._data.data
        tmp = numpy.zeros(4)
        tmp[0:2] = in_prim[:]
        tmp[2:] = in_dual[:]
        out_data = self.A.dot(tmp)
        out_vec._primal._data.data[:] = out_data[0:2]
        out_vec._dual._data.data[:] = out_data[2:]

    def test_bad_radius(self):
        # reset the solution vector
        self.x.equals(0)
        self.b.equals(1)
        # solve the system with FLECS
        self.krylov.radius = -1.
        try:
            self.krylov.solve(
                self.mat_vec, self.b, self.x, self.precond.product)
        except ValueError as err:
            self.assertEqual(
                str(err),
                'trust-region radius must be nonnegative: radius = -1.000000')

    def test_radius_inactive_with_small_mu(self):
        # reset the solution vector
        self.x.equals(0)
        self.b.equals(1)
        # solve the system with FLECS
        self.krylov.radius = 100.0
        self.krylov.mu = 1.0
        self.krylov.solve(self.mat_vec, self.b, self.x, self.precond.product)
        # hard code expected result
        expected = numpy.array([0.0625, 0.3125, 4, -6])
        # compare actual result to expected
        total_data = numpy.zeros(4)
        total_data[0:2] = self.x._primal._data.data[:]
        total_data[2:] = self.x._dual._data.data[:]
        diff = abs(total_data - expected)
        diff = max(diff)
        self.assertTrue(diff <= 1.e-3)

    def test_radius_inactive_with_large_mu(self):
        # reset the solution vector
        self.x.equals(0)
        self.b.equals(1)
        # solve the system with FLECS
        self.krylov.radius = 100.0
        self.krylov.mu = 100000.0
        self.krylov.solve(self.mat_vec, self.b, self.x, self.precond.product)
        # calculate expected result
        rhs = numpy.zeros(4)
        rhs[0:2] = self.b._primal._data.data[:]
        rhs[2:] = self.b._dual._data.data[:]
        expected = numpy.linalg.solve(self.A, rhs)
        # compare actual result to expected
        total_data = numpy.zeros(4)
        total_data[0:2] = self.x._primal._data.data[:]
        total_data[2:] = self.x._dual._data.data[:]
        diff = abs(total_data - expected)
        diff = max(diff)
        self.assertTrue(diff <= 1.e-3)

    def test_radius_active(self):
        # reset the solution vector
        self.x.equals(0)
        self.b.equals(1)
        # solve the system with FLECS
        self.krylov.radius = 0.1
        self.krylov.solve(self.mat_vec, self.b, self.x, self.precond.product)
        # compare actual result to expected
        exp_norm = self.krylov.radius
        actual_norm = self.x._primal.norm2
        self.assertTrue(abs(actual_norm - exp_norm) <= 1e-3)

if __name__ == "__main__":

    unittest.main()
