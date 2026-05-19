from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class ActivationEmailRateThrottle(SimpleRateThrottle):
    scope = "activation_email"

    def get_cache_key(self, request, view):
        user_id = view.kwargs.get("pk", "unknown")
        ident = self.get_ident(request)
        return self.cache_format % {
            "scope": f"{self.scope}:{user_id}",
            "ident": ident,
        }
