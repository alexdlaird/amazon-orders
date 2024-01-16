import os

import responses
from click.testing import CliRunner

from amazonorders.cli import amazon_orders_cli
from amazonorders.session import BASE_URL
from tests.unittestcase import UnitTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.6"


class TestCli(UnitTestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_missing_credentials(self):
        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--username", "", "--password", ""])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertTrue("Usage: " in response.output)

    @responses.activate
    def test_history_command(self):
        # GIVEN
        year = 2023
        start_index = 10
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "order-history-{}-{}.html".format(year, start_index)), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                "{}/your-orders/orders?timeFilter=year-{}&startIndex={}".format(BASE_URL,
                                                                                year, start_index),
                body=f.read(),
                status=200,
            )

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--username", "some-user", "--password",
                                       "some-password", "history", "--year",
                                       year, "--start-index", start_index])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp1.call_count)
        self.assertEqual("""Order #112-0069846-3887437: "[<Item: "SpaGuard Spa Chlorinating Concentrate - 5 Lb">]"
Order #113-1909885-6198667: "[<Item: "Duraflame Quick Start Fire Lighters 2 Packs of 4">]"
Order #112-4188066-0547448: "[<Item: "Dimetapp Children's Nighttime Cold & Congestion Antihistamine/Cough Suppressant & Decongestant (Grape Flavor, 4 fl. oz. Bottle, Pack of 3)">]"
Order #112-9685975-5907428: "[<Item: "Cadeya Egg Cleaning Brush Silicone, Egg Scrubber for Fresh Eggs, Reusable Cleaning Tools for Egg Washer (Pink)">, <Item: "Swiffer WetJet Hardwood and Floor Spray Mop Cleaner Starter Kit, Includes: 1 Power Mop, 10 Pads, Cleaning Solution, Batteries">]"
Order #112-1544475-9165068: "[<Item: "Goodnites Boys' Nighttime Bedwetting Underwear, Size S/M (43-68 lbs), 44 Ct (2 Packs of 22), Packaging May Vary">]"
Order #112-9858173-0430628: "[<Item: "GO2HEJING Ring Dish Tray, Jewelry Dish Tray Bowl, Small Decorative Dish for Jewelry, Jewelry Plate Trays Gift for Friend Woman Daughter Sister Mom, Key Tray for Entryway Table (Light Blue)">, <Item: "GO2HEJING Jewelry Dish Tray, Ring Dish, Ceramic Trinket Tray, Key Bowl, Decorative Plate, Gifts for Friends Sisters Daughter Mother (Light Cyan①)">]"
Order #112-3899501-4971443: "[<Item: "Natrol Kids Melatonin 1mg, Dietary Supplement for Restful Sleep, 60 Berry-Flavored Gummies, 60 Day Supply">]"
Order #112-2545298-6805068: "[<Item: "COZOO 3 Way Dimmable Touch Bedside Table Lamp with 2 USB Charging Ports 2 Outlets Power Strip,Black Charger Base White Fabric Shade,LED Desk Night Light for Bedroom/Nightstand/Living Room/College Dorm">]"
Order #113-4970960-6452217: "[<Item: "Bounty Quick-Size Paper Towels, White, 16 Family Rolls = 40 Regular Rolls">]"
Order #112-9733602-9062669: "[<Item: "Amazon Basics 2-Ply Toilet Paper, 30 Rolls (5 Packs of 6), White">]"
""", response.output)

    @responses.activate
    def test_order_command(self):
        # GIVEN
        order_id = "112-2961628-4757846"
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "order-details-112-2961628-4757846.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                "{}/gp/your-account/order-details?orderID={}".format(BASE_URL,
                                                                     order_id),
                body=f.read(),
                status=200,
            )

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--username", "some-user", "--password",
                                       "some-password", "order", order_id])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(
            'Order #112-2961628-4757846: "[<Item: "Nintendo Switch Pro Controller">]"\n',
            response.output)
