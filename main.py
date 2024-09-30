from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

amazon_session = AmazonSession("EMAIL",
                               "PASSWORD")
amazon_session.login()

amazon_orders = AmazonOrders(amazon_session)
orders = amazon_orders.get_order_history(year=2024)

for order in orders:
    print(f"{order.order_number} - {order.grand_total} - {order.order_placed_date}")

