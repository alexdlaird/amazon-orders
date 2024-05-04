from amazonorders.session import IODefault


class IODefaultWithTextPrompt(IODefault):
    """
    Use the tiny dev server to handle text message responses through our IO handler.

    Amazon doesn't say, but they might impose a time limit (usually 3-5 minutes) in which we have to answer
    2FA prompts, including Captcha. Our ``io`` class will block and await a response just like ``input()`` from the
    command prompt on ``IODefault`` does.
    """

    def __init__(self, tiny_server, to_phone_number):
        self.tiny_server = tiny_server
        self.to_phone_number = to_phone_number

        print(f"--> IODefaultWithTextPrompt initialized, prompts will be sent over text to {self.to_phone_number}\n")

    def prompt(self,
               msg,
               **kwargs):
        if "choices" in kwargs:
            msg = "{}\n\n{}".format("\n".join(kwargs.get("choices")), msg)

        return self.tiny_server.await_text_response(self.to_phone_number, msg,
                                                    **kwargs)
