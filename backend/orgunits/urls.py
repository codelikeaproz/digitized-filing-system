from rest_framework.routers import DefaultRouter

from .views import OrgUnitViewSet

router = DefaultRouter(trailing_slash=False)
router.register("", OrgUnitViewSet, basename="org-unit")

urlpatterns = router.urls
