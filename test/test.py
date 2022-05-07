#!/usr/bin/env python

import unittest
import numpy as np
from scipy.special import ellipk, ellipe
import virtual_casing as vc

class Tests(unittest.TestCase):
    def test_w7x(self):
        """
        Run the test shown in Figure 2 of Malhotra et al, Plasma Physics
        and Controlled Fusion 62, 024004 (2020).
        """
        expected_errors = [2e-4, 3e-7, 2e-9, 3e-11]
        for j in range(4):
            digits = 3 + 3 * j
            for half_period in [True, False]:
                with self.subTest(digits=digits, half_period=half_period):
                    # Double the number of toroidal grid points if we do not exploit stellarator symmetry:
                    nphi_factor = 1 if half_period else 2

                    self.subtest_w7x(digits, 5, half_period, nphi_factor * 10, 20,
                                     vc.SurfType.W7X_,
                                     nphi_factor * 6 * digits, 32 * digits,
                                     nphi_factor * 20, 40,
                                     expected_errors[j])

    def subtest_w7x(self, digits, nfp, half_period, nphi, ntheta, surf_type, src_nphi, src_ntheta, trg_nphi, trg_ntheta, expected_error):
        X = vc.VirtualCasingTestData.surface_coordinates(nfp, half_period, nphi, ntheta, surf_type)

        B_external_true_trg_resolution, B_internal_true_trg_resolution = vc.VirtualCasingTestData.magnetic_field_data(nfp, half_period, nphi, ntheta, X, trg_nphi, trg_ntheta)
        B_external_true_src_resolution, B_internal_true_src_resolution = vc.VirtualCasingTestData.magnetic_field_data(nfp, half_period, nphi, ntheta, X, src_nphi, src_ntheta)
        B_total_true_src_resolution = np.array(B_external_true_src_resolution) + np.array(B_internal_true_src_resolution)

        vcasing = vc.VirtualCasing()
        vcasing.setup(digits, nfp, half_period, nphi, ntheta, X, src_nphi, src_ntheta, trg_nphi, trg_ntheta)

        B_external_computed = vcasing.compute_external_B(B_total_true_src_resolution)
        B_err = np.array(B_external_computed) - np.array(B_external_true_trg_resolution)
        max_val = np.abs(B_total_true_src_resolution).max()
        max_err = np.abs(B_err).max()
        max_rel_err = max_err / max_val
        print(f"For digits = {digits} and half_period = {half_period}, maximum relative error = {max_rel_err}")
        self.assertLess(max_rel_err, expected_error)

    def test_test_data_phi_grid(self):
        """
        For VirtualCasingTestData.surface_coordinates, make sure the phi
        grid behaves as expected for both half_period=True and False.
        """
        for half_period in [True, False]:
            for surf_type in [vc.SurfType.W7X_]:
                nfp = 5
                nphi = 30
                ntheta = 25
                x1d = vc.VirtualCasingTestData.surface_coordinates(nfp, half_period, nphi, ntheta, surf_type)
                x1d = np.array(x1d)

                # Unpack 1D array results:
                x3d = np.zeros((nphi, ntheta, 3))
                for jxyz in range(3):
                    x3d[:, :, jxyz] = x1d[jxyz * nphi * ntheta: (jxyz + 1) * nphi * ntheta].reshape((nphi, ntheta), order='C')

                # Check order:
                index = 0
                for jxyz in range(3):
                    for jphi in range(nphi):
                        for jtheta in range(ntheta):
                            np.testing.assert_allclose(x1d[index], x3d[jphi, jtheta, jxyz])
                            index += 1

                phi_from_vc = np.arctan2(x3d[:, :, 1], x3d[:, :, 0])

                if half_period:
                    phi1d = np.linspace(0, np.pi / nfp, nphi, endpoint=False)
                    phi1d += 0.5 * (phi1d[1] - phi1d[0])
                else:
                    phi1d = np.linspace(0, 2 * np.pi / nfp, nphi, endpoint=False)
                theta1d = np.linspace(0, 2 * np.pi, ntheta, endpoint=False)

                theta2d, phi2d = np.meshgrid(theta1d, phi1d)

                np.testing.assert_allclose(phi2d, phi_from_vc, atol=1e-14)

    def test_rotating_ellipse(self):
        """
        Run a test similar to test_w7x, but with test data generated
        directly in python.
        """
        expected_errors = [2e-4, 2e-8, 1e-9]
        nfp = 4
        for j in range(3):
            digits = 3 + 3 * j
            for half_period in [True, False]:
                with self.subTest(digits=digits, half_period=half_period):
                    # Double the number of toroidal grid points if we do not exploit stellarator symmetry:
                    nphi_factor = 1 if half_period else 2

                    self.subtest_rotating_ellipse(digits, nfp, half_period, nphi_factor * 10, 20,
                                                  nphi_factor * 3 * digits, 15 * digits,
                                                  nphi_factor * 19, 29,
                                                  expected_errors[j])

    def rotating_ellipse_gamma(self, nfp, half_period, nphi, ntheta):
        """
        Returns the position vector in Cartesian coordinates on the surface of a rotating ellipse.
        The returned array has shape ``(nphi, ntheta, 3)``.
        """
        major_radius = 0.7
        minor_radius_a = 0.1
        minor_radius_b = 0.2

        if half_period:
            phi1d = np.linspace(0, np.pi / nfp, nphi, endpoint=False)
            phi1d += 0.5 * (phi1d[1] - phi1d[0])
        else:
            phi1d = np.linspace(0, 2 * np.pi / nfp, nphi, endpoint=False)
        theta1d = np.linspace(0, 2 * np.pi, ntheta, endpoint=False)
        theta2d, phi2d = np.meshgrid(theta1d, phi1d)
        
        alpha = theta2d - nfp * phi2d / 2
        u = minor_radius_a * np.cos(alpha)
        v = minor_radius_b * np.sin(alpha)
        cosangle = np.cos(nfp * phi2d / 2)
        sinangle = np.sin(nfp * phi2d / 2)
        r = u * cosangle - v * sinangle + major_radius
        z = u * sinangle + v * cosangle

        x3d = np.zeros((nphi, ntheta, 3))
        x3d[:, :, 0] = r * np.cos(phi2d)
        x3d[:, :, 1] = r * np.sin(phi2d)
        x3d[:, :, 2] = z
        
        return x3d

    def flatten(self, arr3d):
        """
        Flatten a 3d array of shape ``(nphi, ntheta, 3)`` into a 1D array
        using the convention in BIEST. The order is
        ``{x11, x12, ..., x1Np, x21, x22, ... , xNtNp, y11, ... , z11, ...}``
        where ``Nt`` is toroidal (not theta!) and ``Np`` is poloidal (not phi!)
        """
        nphi = arr3d.shape[0]
        ntheta = arr3d.shape[1]
        arr1d = np.zeros(nphi * ntheta * 3)
        for jxyz in range(3):
            arr1d[jxyz * nphi * ntheta: (jxyz + 1) * nphi * ntheta] = arr3d[:, :, jxyz].flatten(order='C')
        
        # Check order:
        index = 0
        for jxyz in range(3):
            for jphi in range(nphi):
                for jtheta in range(ntheta):
                    np.testing.assert_allclose(arr1d[index], arr3d[jphi, jtheta, jxyz])
                    index += 1
                    
        return arr1d

    def get_reference_B(self, nfp, half_period, nphi, ntheta):
        """
        B_external is just a 1 / R field in the toroidal direction.

        B_internal is the field from a circular wire, computed using the formula with elliptic integrals.
        """
        x3d = self.rotating_ellipse_gamma(nfp, half_period, nphi, ntheta)

        B_external = np.zeros((nphi, ntheta, 3))
        B_internal = np.zeros((nphi, ntheta, 3))

        # Evaluate B_external:
        r_squared = x3d[:, :, 0] ** 2 + x3d[:, :, 1] ** 2
        B_external[:, :, 0] = -x3d[:, :, 1] / r_squared
        B_external[:, :, 1] = x3d[:, :, 0] / r_squared

        # Evaluate B_internal:
        r0 = 0.72  # Radius of the current loop
        Inorm = 1.0  # Overall scale factor
        rho = np.sqrt(x3d[:, :, 0] ** 2 + x3d[:, :, 1] ** 2)
        r = np.sqrt(x3d[:, :, 0] ** 2 + x3d[:, :, 1] ** 2 + x3d[:, :, 2] ** 2)
        alpha = np.sqrt(r0 * r0 + r * r - 2 * r0 * rho)
        beta = np.sqrt(r0 * r0 + r * r + 2 * r0 * rho)
        k_squared = 1 - alpha * alpha / (beta * beta)
        ellipek2 = ellipe(k_squared)
        ellipkk2 = ellipk(k_squared)
        
        B_internal[:, :, 0] = Inorm * x3d[:, :, 0] * x3d[:, :, 2] \
            / (2 * alpha ** 2 * beta * rho ** 2 + 1e-31) \
            * ((r0 ** 2 + r ** 2) * ellipek2 - alpha ** 2 * ellipkk2)
        
        B_internal[:, :, 1] = Inorm * x3d[:, :, 1] * x3d[:, :, 2] \
            / (2 * alpha ** 2 * beta * rho ** 2 + 1e-31) \
            * ((r0 ** 2 + r ** 2) * ellipek2 - alpha ** 2 * ellipkk2)
        
        B_internal[:, :, 2] = Inorm / (2 * alpha ** 2 * beta + 1e-31) \
            * ((r0 ** 2 - r ** 2) * ellipek2 + alpha ** 2 * ellipkk2)
        
        return self.flatten(B_external), self.flatten(B_internal)
    
    def subtest_rotating_ellipse(self, digits, nfp, half_period, nphi, ntheta, src_nphi, src_ntheta, trg_nphi, trg_ntheta, expected_error):

        surface_position_vector = self.flatten(self.rotating_ellipse_gamma(nfp, half_period, nphi, ntheta))
        B_external_true_trg_resolution, B_internal_true_trg_resolution = self.get_reference_B(nfp, half_period, trg_nphi, trg_ntheta)
        B_external_true_src_resolution, B_internal_true_src_resolution = self.get_reference_B(nfp, half_period, src_nphi, src_ntheta)
        B_total_true_src_resolution = np.array(B_external_true_src_resolution) + np.array(B_internal_true_src_resolution)

        vcasing = vc.VirtualCasing()
        vcasing.setup(digits, nfp, half_period, nphi, ntheta, surface_position_vector, src_nphi, src_ntheta, trg_nphi, trg_ntheta)

        B_external_computed = vcasing.compute_external_B(B_total_true_src_resolution)
        B_err = np.array(B_external_computed) - np.array(B_external_true_trg_resolution)
        max_val = np.abs(B_total_true_src_resolution).max()
        max_err = np.abs(B_err).max()
        max_rel_err = max_err / max_val
        print(f"For digits = {digits} and half_period = {half_period}, maximum relative error = {max_rel_err}")
        self.assertLess(max_rel_err, expected_error)

                    
if __name__ == "__main__":
    unittest.main()
