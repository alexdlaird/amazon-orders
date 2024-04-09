from amazonorders.session import IODefault


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
