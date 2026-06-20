from rest_framework.routers import DefaultRouter

from .views import EmployeeViewSet

router = DefaultRouter(trailing_slash=False)
router.register("employees", EmployeeViewSet, basename="employee")

urlpatterns = router.urls
