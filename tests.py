"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from utils import build_tpay_request


class TpayTest(TestCase):
    def test_build_request(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(build_tpay_request,None)
