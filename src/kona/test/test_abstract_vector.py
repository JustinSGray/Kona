import unittest

import numpy as np

from kona.user import BaseVector
from kona.user import BaseAllocator
# from kona.user_vectors.petsc_vector import NumpyVector # should follow this exact interface

class AbsVectorTestCase(unittest.TestCase):
    '''Test case that can be used for any base abstract vector class'''

    def setUp(self):

        self.x_vec = BaseVector(val=1, size=10) #initial value for the vector
        self.y_vec = BaseVector(val=2, size=10)
        self.z_vec = BaseVector(val=np.linspace(0,10,10), size=10)

    def tearDown(self):
        pass

    def test_inner_product(self):
        val = self.x_vec.inner(self.x_vec)
        self.assertEquals(val, 10)

        val = self.x_vec.inner(self.y_vec)
        self.assertEquals(val, 20)

    def test_times_equals(self):
        self.x_vec.times(3)
        norm = self.x_vec.inner(self.x_vec)
        self.assertEquals(self.x_vec.norm2, 3*10**.5)

    def test_plus_equals(self):
        self.x_vec.plus(self.y_vec)
        self.assertEquals(self.x_vec.norm2, 3*10**.5)

    def test_assignment(self):

        x_vec = self.x_vec

        self.z_vec.set_to_scalar(15)
        self.assertEquals(self.z_vec.norm2, 15*10**.5)

        self.z_vec.set_to_vector(self.x_vec)
        self.z_vec.times(2)
        self.assertEquals(self.z_vec.norm2, 2*10**.5)

        self.z_vec.equals_ax_p_by(2, self.x_vec, 3, self.y_vec)


class TestCaseProblemAllocator(unittest.TestCase):

    def setUp(self):
        self.alloc = BaseAllocator(3, 4, 5)

    def test_design_vec(self):
        base_var = self.alloc.alloc_design()
        self.assertTrue(isinstance(base_var, BaseVector))

        self.assertEqual(base_var.data.shape[0], 3)

    def test_state_vec(self):
        base_var = self.alloc.alloc_state()
        self.assertTrue(isinstance(base_var, BaseVector))

        self.assertEqual(base_var.data.shape[0], 4)


    def test_dual_vec(self):
        base_var = self.alloc.alloc_dual()
        self.assertTrue(isinstance(base_var, BaseVector))

        self.assertEqual(base_var.data.shape[0], 5)

if __name__ == "__main__":
    unittest.main()
