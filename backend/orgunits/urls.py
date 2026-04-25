from rest_framework.routers import DefaultRouter

from .views import OrgUnitViewSet

router = DefaultRouter()
router.register(r"org-units", OrgUnitViewSet, basename="org-units")

urlpatterns = router.urls
