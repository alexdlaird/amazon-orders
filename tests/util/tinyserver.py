import os
import threading
import time

from flask import Flask, Response
from flask import request
from pyngrok import ngrok
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

_tiny_server = None


def get_tiny_server(twilio_account_sid, twilio_auth_token, twilio_phone_number):
    global _tiny_server

    if not _tiny_server:
        _tiny_server = TinySMSServer(twilio_account_sid=twilio_account_sid,
                                     twilio_auth_token=twilio_auth_token,
                                     twilio_phone_number=twilio_phone_number,
                                     flask_port=os.environ.get("FLASK_PORT", "8000"))
        _tiny_server.start()

        print(f"\n--> TinySMSServer initialized, prompt responses to Twilio number {twilio_phone_number} will be intercepted")
    else:
        print("\n--> Existing TinySMSServer found, reusing")

    return _tiny_server


class TinySMSServer:
    """
    Use Twilio in combination Flask and ``pyngrok`` to build a tiny server that uses a webhook to receive the
    SMS response after a prompt is initiated. The prompt will wait until a response text is received (via the
    webhook). You can find docs and a basic Flask example for ``pyngrok``
    `here <https://pyngrok.readthedocs.io/en/latest/integrations.html#flask>`_.
    """

    def __init__(self, twilio_account_sid, twilio_auth_token, twilio_phone_number, flask_port):
        self.twilio_account_sid = twilio_account_sid
        self.twilio_auth_token = twilio_auth_token
        self.twilio_phone_number = twilio_phone_number
        self.flask_port = flask_port

        self.twilio_client = Client(self.twilio_account_sid,
                                    self.twilio_auth_token)
        self.app = self._create_app()

        self.flask_server_thread = None
        self.webhook_response = None
        self.public_url = None
        self.locked = False

    def _create_app(self):
        """
        Define a simple Flask server with a /webhook route
        """
        app = Flask(__name__)

        @app.route("/webhook", methods=["POST"])
        def webhook():
            self.webhook_response = request.form["Body"]

            return Response(str(MessagingResponse()), mimetype="text/xml")

        return app

    def start(self):
        if self.flask_server_thread is None:
            # Start the servers and proxy to localhost
            self.flask_server_thread = threading.Thread(target=self.app.run, daemon=True,
                                                        kwargs={"host": "127.0.0.1", "port": self.flask_port,
                                                                "debug": True, "use_reloader": False})
            self.flask_server_thread.start()

            self.public_url = ngrok.connect(self.flask_port, domain=os.environ.get("NGROK_DOMAIN")).public_url

            # Update Twilio incoming webhooks to route text's to our tiny server
            incoming_phone_number = self.twilio_client.incoming_phone_numbers.list(
                phone_number=self.twilio_phone_number)[0]
            sms_callback_url = "{}/webhook".format(self.public_url)
            self.twilio_client.incoming_phone_numbers(
                incoming_phone_number.sid).update(sms_url=sms_callback_url,
                                                  sms_method="POST")

    def await_text_response(self, to_phone_number, msg, img_url=None, **kwargs):
        if self.locked:
            raise RuntimeError("This class and method act as a singleton, awaiting `locked` to be False.")

        self.locked = True

        # Send the text message
        self.twilio_client.api.account.messages.create(
            to=to_phone_number,
            from_=self.twilio_phone_number,
            body=msg,
            media_url=[img_url] if img_url else None)

        print("--> SMS sent to {}, awaiting response ...".format(to_phone_number))

        # Await the response ...
        while not self.webhook_response:
            time.sleep(0.1)

        print("--> ... response received: {}".format(self.webhook_response))

        # Fetch the response, then reset for the next request
        response = self.webhook_response
        self.webhook_response = None
        self.locked = False

        return response
