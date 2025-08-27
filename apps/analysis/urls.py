from django.urls import path
from apps.analysis import views

urlpatterns = [
    path('', views.AnalysisListCreateAPIView.as_view(), name='analysis-list-create'),
    path('<int:pk>/', views.AnalysisRetrieveUpdateDestroyAPIView.as_view(), name='analysis-detail'),
]