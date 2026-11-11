__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import os

from amazonauth import conf as auth_conf
from amazonauth import constants as auth_constants
from amazonauth import exception as auth_exception
from amazonauth import selectors as auth_selectors
from amazonauth import session as auth_session

from amazonorders import conf, constants, exception, selectors, session
from tests.unittestcase import UnitTestCase


class TestAmazonAuthShims(UnitTestCase):
    def test_exception_exports_the_amazon_auth_errors(self):
        # GIVEN
        names = {
            "AmazonOrdersError": "AmazonAuthError",
            "AmazonOrdersAuthError": "AmazonAuthSignInError",
            "AmazonOrdersAuthRedirectError": "AmazonAuthRedirectError",
            "AmazonOrdersChallengeUnsolvedError": "AmazonAuthChallengeUnsolvedError",
            "AmazonOrdersWafSolverError": "AmazonAuthWafSolverError",
            "AmazonOrdersBrowserNotInstalledError": "AmazonAuthBrowserNotInstalledError",
        }

        # WHEN
        exported = {name: getattr(exception, name) for name in names}

        # THEN
        for name, auth_name in names.items():
            self.assertIs(getattr(auth_exception, auth_name), exported[name])
        self.assertTrue(issubclass(exception.AmazonOrdersEntityError, auth_exception.AmazonAuthError))

    def test_selectors_subclass_the_amazon_auth_selectors(self):
        # WHEN
        selectors_class = selectors.Selectors

        # THEN
        self.assertTrue(issubclass(selectors_class, auth_selectors.AuthSelectors))
        self.assertEqual(auth_selectors.AuthSelectors.SIGN_IN_FORM_SELECTOR, selectors.Selectors.SIGN_IN_FORM_SELECTOR)

    def test_conf_shares_the_amazon_auth_locks_and_keeps_its_own_config_dir(self):
        # WHEN
        exported = [conf.config_file_lock, conf.cookies_file_lock, conf.debug_output_file_lock]

        # THEN
        for exported_lock, auth_lock in zip(exported, [auth_conf.config_file_lock, auth_conf.cookies_file_lock,
                                                       auth_conf.debug_output_file_lock]):
            self.assertIs(auth_lock, exported_lock)
        self.assertTrue(issubclass(conf.AmazonOrdersConfig, auth_conf.AmazonAuthConfig))
        self.assertEqual(os.path.join(conf.DEFAULT_CONFIG_DIR, "config.yml"), conf.AmazonOrdersConfig().config_path)

    def test_constants_subclass_the_amazon_auth_ones(self):
        # WHEN
        constants_class = constants.Constants

        # THEN
        self.assertTrue(issubclass(constants_class, auth_constants.AuthConstants))

    def test_session_builds_an_amazon_orders_config_by_default(self):
        # WHEN
        amazon_session = session.AmazonSession()

        # THEN
        self.assertIsInstance(amazon_session.config, conf.AmazonOrdersConfig)
        self.assertTrue(issubclass(session.AmazonSession, auth_session.AmazonSession))
