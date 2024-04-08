import os
import time
from threading import Thread

from amazonorders.session import IODefault
from flask import Flask, Response
from flask import request
from pyngrok import ngrok
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

_tiny_server = None


def start_tiny_server(tiny_server=None):
    global _tiny_server

    if not _tiny_server:
        if not tiny_server:
            _tiny_server = TinySMSServer()
        else:
            _tiny_server = tiny_server

    _tiny_server.start()

    return _tiny_server


class TinySMSServer:
    """
    Use Twilio in combination Flask and ``pyngrok`` to build a tiny server that uses a webhook to receive the
    text responses when a prompt is initiated. The prompt will wait until a response text is received (via the
    webhook). You can find docs and a basic Flask example for ``pyngrok`` `here <https://pyngrok.readthedocs.io/en/latest/integrations.html#flask>`_.
    """

    def __init__(self,
                 twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID"),
                 twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN"),
                 twilio_phone_number=os.environ.get("TWILIO_PHONE_NUMBER"),
                 flask_port=os.environ.get("FLASK_PORT", "5000")):
        self.twilio_account_sid = twilio_account_sid
        self.twilio_auth_token = twilio_auth_token
        self.twilio_phone_number = twilio_phone_number
        self.flask_port = flask_port

        self.twilio_client = Client(self.twilio_account_sid,
                                    self.twilio_auth_token)
        self.webhook_response = None
        self.running = False
        self.locked = False

        self.flask_server = None
        self.public_url = None

    def start(self):
        # Define a simple Flask server with a single /webhook route
        app = Flask(__name__)

        @app.route("/webhook", methods=["POST"])
        def webhook():
            self.webhook_response = request.form["Body"]

            return Response(str(MessagingResponse()), mimetype="text/xml")

        # Start the servers and proxy to localhost
        flask_server = Thread(target=app.run,
                              kwargs={"port": self.flask_port})
        flask_server.start()
        print("Flask server started on port {}".format(self.flask_port))

        self.public_url = ngrok.connect(self.flask_port).public_url
        print("ngrok proxying requests from {}".format(self.public_url))

        # Update Twilio incoming webhooks to route text's to our tiny server
        incoming_phone_number = self.twilio_client.incoming_phone_numbers.list(
            phone_number=self.twilio_phone_number)[0]
        sms_callback_url = "{}/webhook".format(self.public_url)
        self.twilio_client.incoming_phone_numbers(
            incoming_phone_number.sid).update(sms_url=sms_callback_url,
                                              sms_method="POST")

        print("Twilio SMS callback URL registered: {}".format(sms_callback_url))

        self.running = True

    def await_text_response(self, to_number, msg, img_url=None):
        if not self.running:
            raise RuntimeError(
                "Call start() on the server first or this will wait forever.")
        if self.locked:
            raise RuntimeError(
                "This class and method act as a singleton, awaiting `locked` to be False.")

        self.locked = True

        # Send the text message
        self.twilio_client.api.account.messages.create(
            to=to_number,
            from_=self.twilio_phone_number,
            body=msg,
            media_url=[img_url] if img_url else None)

        print("SMS sent to {}, awaiting response ...".format(to_number))

        # Await the response ...
        while not self.webhook_response:
            time.sleep(0.1)

        print("... response received: {}".format(self.webhook_response))

        # Fetch the response, then reset for the next request
        response = self.webhook_response
        self.webhook_response = None
        self.locked = False

        return response


class IODefaultWithTextPrompt(IODefault):
    """
    Use the tiny dev server to handle text message responses through our IO handler.

    Amazon doesn't say, but they might impose a time limit (usually 3-5 minutes) in which we have to answer
    2FA prompts, including Captcha. Our ``io`` class will block and await a response just like ``input()`` from the
    command prompt on ``IODefault`` does.
    """

    def __init__(self, tiny_server, phone_number):
        self.tiny_server = tiny_server
        self.phone_number = phone_number

    def prompt(self,
               msg,
               **kwargs):
        if "mfa_device_select_choices" in kwargs:
            # Rebuild the prompt message with given device choices included
            i = 0
            choices_str = ""
            for field in kwargs.pop("mfa_device_select_choices"):
                choices_str += "{}: {}\n".format(i, field["value"].strip())

                i += 1
            msg = "{}\n{}".format(choices_str, msg)
        if "captcha_img_url" in kwargs:
            # Rename the image URL var for SMS
            kwargs["img_url"] = kwargs.pop("captcha_img_url")
        return self.tiny_server.await_text_response(self.phone_number, msg,
                                                    **kwargs)
