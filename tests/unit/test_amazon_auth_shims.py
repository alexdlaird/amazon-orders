__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import os

from amazonauth import conf as auth_conf
from amazonauth import constants as auth_constants
from amazonauth import exception as auth_exception
from amazonauth import forms as auth_forms
from amazonauth import region_data as auth_region_data
from amazonauth import selectors as auth_selectors
from amazonauth import session as auth_session
from amazonauth import util as auth_util
from amazonauth.contrib.browser import playwright as auth_playwright
from amazonauth.contrib.waf import anticaptcha as auth_anticaptcha
from amazonauth.contrib.waf import base as auth_waf_base
from amazonauth.contrib.waf import capsolver as auth_capsolver
from amazonauth.contrib.waf import twocaptcha as auth_twocaptcha

from amazonorders import conf, constants, exception, forms, region_data, selectors, session, util
from amazonorders.contrib.browser import playwright
from amazonorders.contrib.waf import anticaptcha, base as waf_base, capsolver, twocaptcha
from tests.unittestcase import UnitTestCase


class TestAmazonAuthShims(UnitTestCase):
    def test_exception_exports_the_amazon_auth_errors(self):
        # GIVEN
        names = {
            "AmazonOrdersError": "AmazonAuthError",
            "AmazonOrdersAuthError": "AmazonAuthSignInError",
            "AmazonOrdersAuthRedirectError": "AmazonAuthRedirectError",
            "AmazonOrdersWafSolverError": "AmazonAuthWafSolverError",
            "AmazonOrdersBrowserNotInstalledError": "AmazonAuthBrowserNotInstalledError",
        }

        # WHEN
        exported = {name: getattr(exception, name) for name in names}

        # THEN
        for name, auth_name in names.items():
            self.assertIs(getattr(auth_exception, auth_name), exported[name])
        self.assertTrue(issubclass(exception.AmazonOrdersEntityError, auth_exception.AmazonAuthError))

    def test_util_exports_the_amazon_auth_primitives(self):
        # GIVEN
        names = ["AmazonSessionResponse", "select", "select_one", "load_class", "has_display", "cleanup_html_text"]

        # WHEN
        exported = {name: getattr(util, name) for name in names}

        # THEN
        for name in names:
            self.assertIs(getattr(auth_util, name), exported[name])

    def test_selectors_exports_the_amazon_auth_selectors(self):
        # WHEN
        exported = [selectors.Selector, selectors.SelectorsFromText]

        # THEN
        self.assertEqual([auth_selectors.Selector, auth_selectors.SelectorsFromText], exported)
        self.assertTrue(issubclass(selectors.Selectors, auth_selectors.AuthSelectors))
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

    def test_constants_and_region_data_export_the_amazon_auth_ones(self):
        # WHEN
        exported = [region_data.REGION_SITES, region_data.RegionSite]

        # THEN
        self.assertEqual([auth_region_data.REGION_SITES, auth_region_data.RegionSite], exported)
        self.assertIs(auth_region_data.REGION_SITES, exported[0])
        self.assertTrue(issubclass(constants.Constants, auth_constants.AuthConstants))

    def test_session_builds_an_amazon_orders_config_by_default(self):
        # WHEN
        amazon_session = session.AmazonSession()

        # THEN
        self.assertIsInstance(amazon_session.config, conf.AmazonOrdersConfig)
        self.assertTrue(issubclass(session.AmazonSession, auth_session.AmazonSession))
        self.assertIs(auth_session.IODefault, session.IODefault)

    def test_forms_and_contrib_export_the_amazon_auth_ones(self):
        # GIVEN
        modules = [(forms, auth_forms), (waf_base, auth_waf_base), (capsolver, auth_capsolver),
                   (anticaptcha, auth_anticaptcha), (twocaptcha, auth_twocaptcha), (playwright, auth_playwright)]

        # WHEN
        exported = [(module, auth_module, module.__all__) for module, auth_module in modules]

        # THEN
        for module, auth_module, names in exported:
            for name in names:
                self.assertIs(getattr(auth_module, name), getattr(module, name), f"{module.__name__}.{name}")
