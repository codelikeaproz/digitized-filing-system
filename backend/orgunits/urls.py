from rest_framework.routers import DefaultRouter

from .views import OrgTypeViewSet, OrgUnitViewSet

router = DefaultRouter()
router.register(r"org-types", OrgTypeViewSet, basename="org-types")
router.register(r"org-units", OrgUnitViewSet, basename="org-units")

urlpatterns = router.urls
