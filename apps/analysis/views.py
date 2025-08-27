from django.shortcuts import render
from .models import Analysis
from django.views.generic import ListView

class AnalysisListView(ListView):
    model = Analysis
    template_name = 'analysis/analysis_list.html'
    context_object_name = 'analyses'

    def get_queryset(self):
        return Analysis.objects.filter(user=self.request.user)