__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonorders.forms import AuthForm


class StubAuthForm(AuthForm):
    """Stub form for ``auth_forms_classes`` loading tests. Lives in a non-test
    helper module so its dotted path is stable regardless of pytest's
    discovery mode."""

    def __init__(self, config):
        super().__init__(config, selector=None)

    def select_form(self, amazon_session, parsed):
        return False


class OtherStubAuthForm(AuthForm):
    """Second stub form for tests that exercise multi-class loading and ordering."""

    def __init__(self, config):
        super().__init__(config, selector=None)

    def select_form(self, amazon_session, parsed):
        return False


class NotAnAuthForm:
    """Stub that is not an :class:`AuthForm` subclass, used to verify the
    ``auth_forms_classes`` loader rejects bad entries with a clear error."""

    def __init__(self, config):
        self.config = config
