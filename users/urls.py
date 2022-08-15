from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserListViewset, UserDetailViewset, AuthenticationViewset, VerificationsViewset

routes = DefaultRouter(trailing_slash=False)
routes.register('auth', AuthenticationViewset, basename='auth')
routes.register('verifications', VerificationsViewset, basename='verifications')

urlpatterns = [
    path("", include(routes.urls)),
    path('users', UserListViewset.as_view(), name="users-list"),
    path('users/<slug:pk>', UserDetailViewset.as_view(), name="user-details"),
]