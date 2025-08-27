from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Analysis

User = get_user_model()

class AnalysisModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_create_analysis(self):
        analysis = Analysis.objects.create(
            user=self.user,
            analysis_target='INCOME',
            period_type='MONTHLY',
            start_date='2025-01-01',
            end_date='2025-01-31',
            description='Test analysis'
        )
        self.assertEqual(analysis.user, self.user)
        self.assertEqual(analysis.analysis_target, 'INCOME')
        self.assertEqual(str(analysis), f'{self.user.email} - INCOME (MONTHLY)')
