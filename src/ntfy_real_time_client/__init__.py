#!/usr/bin/env python

# Pushover Open Client API
# specification: https://pushover.net/api/client

import datetime
import functools
import json
import os
import requests
import shlex
import shutil
import subprocess
import sys
import types
# import typing

from importlib.metadata import PackageNotFoundError, version  # pragma: no cover

import websocket

FUNCTION = types.FunctionType

DEBUG: bool = False

if DEBUG:
    websocket.enableTrace(True)

# from importlib.metadata import PackageNotFoundError, version  # pragma: no cover

# if sys.version_info[:2] >= (3, 8):
#    # TODO: Import directly (no need for conditional) when `python_requires = >= 3.8`
#    from importlib.metadata import PackageNotFoundError, version  # pragma: no cover
# else:
#    from importlib_metadata import PackageNotFoundError, version  # pragma: no cover

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = "python-ntfy-real-time-client"
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError

PUSHOVER_API_URL: str = "https://api.pushover.net/1"

PUSHOVER_WEBSOCKET_SERVER_URL: str = "wss://client.pushover.net/push"
PUSHOVER_WEBSOCKET_LOGIN: str = "login:{device_id}:{secret}\n"

CREDENTIALS_FILENAME: str = os.path.expanduser("~/.ntfy-real-time-client-creds.json")

COMMAND_FUNCTIONS_REGISTRY: dict[str, FUNCTION] = dict()
"""Registry for command functions.

Functions registered here receive the text message of the notification
as **positional arguments**, with the command itself being the first positional
argument separated by spaces (as in a shell command).

The function name is registered as the command, and so
the function is triggered when the first word of the notification
message (ie., the command) is the name of the function.

Todo:
    *use `shlex` to improve parsing.
"""

COMMAND_PARSERS_REGISTRY: dict[str, FUNCTION] = dict()
"""
these parsers receive `raw_data` from the Pushover server. They are
triggered if the first word (ie., the command) of the notification message
is the name of the function.
"""

PARSERS_REGISTRY: dict = dict()  # TODO: maybe make a set of this
"""
All received notifications will be sent to the filters registered here.
"""

SHELL_COMMANDS_REGISTRY: set = set()
"""
These execute shell commands, from the allowed list.
"""

# when the alias is received, it executes command and args
# { "alias": ["command", "arg1", "arg2", ...] }
# SHELL_COMMAND_ALIASES_REGISTRY: dict[str, str | list] = dict()
SHELL_COMMAND_ALIASES_REGISTRY: dict[str, list] = dict()

# TODO: improve decorators typing annotations
def register_command(f: FUNCTION, *args, **kwargs) -> FUNCTION:
    """Decorator that registers command python functions.

    Commands execute user-defined python functions. The name of the function is
    the command, ie., the first word of the received notification; the other
    words of the notification are the parameters.

    The function arguments decorated by this decorator should have positional
    arguments as needed, and  a declaration of `*args` in the case of
    receiving more than those needed.
    """

    @functools.wraps(f)
    def decorator(*args, **kwargs):
        return f(*args, **kwargs)

    COMMAND_FUNCTIONS_REGISTRY.update({f.__name__: f})

    return decorator


# TODO: improve decorators typing annotations
def register_command_parser(f: FUNCTION, *args, **kwargs) -> FUNCTION:
    """Decorator that registers perser python functions.

    Parser functions get raw data from each notification received from the
    ntfy server for processing.

    Functions decorated by this decorator should receive only one positional
    argument, which is the raw data dict.
    """

    @functools.wraps(f)
    def decorator(*args, **kwargs):
        return f(*args, **kwargs)

    COMMAND_PARSERS_REGISTRY.update({f.__name__: f})

    return decorator


def register_parser(f: FUNCTION, *args, **kwargs) -> FUNCTION:
    """Decorator that registers perser python functions.

    The functions registered using this decorator will be executed for all
    of the received notifications.

    Parser functions get raw data from each notification received from the
    ntfy server for processing.

    Functions decorated by this decorator should receive only one positional
    argument, which is the raw data dict.
    """

    @functools.wraps(f)
    def decorator(*args, **kwargs):
        return f(*args, **kwargs)

    PARSERS_REGISTRY.update({f.__name__: f})

    return decorator


def register_shell_command(command: str) -> None:
    """Register a shell command.

    When a notification is received with the message's first word being this
    command, the command is executed via shell. The other words from the
    notification are passed as arguments to that command.

    Args:
        command (str):

    Returns:
        None
    """

    SHELL_COMMANDS_REGISTRY.add(command.split()[0])


def register_shell_command_alias(alias: str, command_line: str | list) -> None:
    """Registers an alias to execute a command line.

    When alias is received via notification, the command line, (command + args)
    is executed using shell.

    Args:
        alias (str): one word alias. When received as notification, will
            execute the command line.
        command_line (str | list): Command plus arguments to be execute. It can
            be a string, which will be `str.split()`ed by the spaces in a list,
            or a list in a similar fashion of that of the `args` parameter of
            `subprocess.Popen` uses.

    Returns:
        None: Returns `None` if nothing happens; `None`, otherwise.

    Todo:
        Use shlex here to handle "same argument separated by spaces."
    """

    processed_alias = alias.split()[0]  # alias should be only one word

    SHELL_COMMAND_ALIASES_REGISTRY.update({processed_alias: command_line})


def get_notification_model(**kwargs) -> dict[str, str | int]:
    """Makes a notification model.

    We use this to have a notification model with all values that can be
    returned by the notification server initialized to None. If a value is
    lacking on the server response because it is empty, now we have it set
    to be processed as such.

    The description of these keys are on the API documentation at:
    https://pushover.net/api/client#download

    Args:
        **kwargs (dict): A dict/expanded dict of the received values from the
        notification server.

    Returns:
        dict: The notification model dict with the notification values
        filled up.
    """

    notification_dict =\
        {
            "id": None,
            "id_str": None,
            "umid": None,
            "umid_str": None,
            "title": None,
            "message": None,
            "app": None,
            "aid": None,
            "aid_str": None,
            "icon": None,
            "date": None,
            "queued_date": None,
            "dispatched_date": None,
            "priority": None,
            "sound": None,
            "url": None,
            "url_title": None,
            "acked": None,
            "receipt": None,
            "html": None,
        }

    notification_dict.update(**kwargs)

    return notification_dict



class NTFYOpenClientRealTime:

    ntfy_websocket_server_commands = dict()

    #  def __init__(self, pushover_open_client: PushoverOpenClient = None,
    #               pushover_websocket_server_url: str =
    #               PUSHOVER_WEBSOCKET_SERVER_URL) -> None:
    def __init__(self, ntfy_websocket_server_url: str =
                 PUSHOVER_WEBSOCKET_SERVER_URL) -> None:
        """Connects to the Pushover's websocket server to do stuff.

         Opens a websocket connection with the Pushover's websocket server and
         handles it's websocket commands.

        Args:
            pushover_open_client (PushoverOpenClient):
            ntfy_websocket_server_url (str, optional):
        """

        #  if not pushover_open_client:
        #      pushover_open_client =\
        #          PushoverOpenClient().load_from_credentials_file()
        #  self.pushover_open_client = pushover_open_client

        #  self.pushover_websocket_server_commands =\
        #      {
        #          b'#': self.message_keep_alive,
        #          b'!': self.message_do_sync,
        #          b'R': self.message_reload_request,
        #          b'E': self.message_error_permanent,
        #          b'A': self.message_error
            #  }

        #  self.pushover_websocket_login_string =\
        #      pushover_open_client.get_websocket_login_string()

        self.websocketapp =\
            websocket.WebSocketApp(ntfy_websocket_server_url,
                                   on_open=self._on_open,
                                   on_message=self._on_message,
                                   on_error=self._on_error,
                                   on_close=self._on_close)

    """
    command function
    command parser
    parser
    shell command
    shell command alias
    """
    def add_command_function(self, function: FUNCTION) -> None:
        """Registers a function as a command.

        Args:
            function (Callable): Reference to the function to be executed for
                this command. When the first word of a notification is the
                command, ie., the function name, the notification text will be
                passed to the function as *args, to be processed.
        """

        function_name = function.__name__
        COMMAND_FUNCTIONS_REGISTRY.update({function_name: function})

    def add_command_parser(self, function: FUNCTION) -> None:
        """Registers a function as a command parser.

        Args:
            function (Callable): Reference to the function to be executed for
                this command. When the first word of a notification is the
                command, ie., the function name, the raw notification dict will
                be passed to the function, to be parsed.
        """

        function_name = function.__name__
        COMMAND_PARSERS_REGISTRY.update({function_name: function})

    def add_parser(self, function: FUNCTION) -> None:
        """Registers a function as parser.

        Args:
            function (Callable): Reference to the function to be executed for
                this command. All notifications received have it's raw data,
                as received by the Pushover server, passed to the functions
                registered via this method or it's
                decorator, ``@register_parser``.
        """

        function_name = function.__name__
        PARSERS_REGISTRY.update({function_name: function})

    def add_shell_command(self, command: str) -> None:
        SHELL_COMMANDS_REGISTRY.add(command)

    def add_shell_command_alias(self, alias: str, command_line: str) -> None:
        SHELL_COMMAND_ALIASES_REGISTRY.update({alias: command_line})

    #  def message_keep_alive(self) -> None:
    #      """Runs when a keep-alive message is received,
    #
    #      This method is executed when the server sends a `b'#'` message. This
    #      is meant as a ping, and to keep the connection open in scenarios where
    #      the connection would be close if no data was transferred in some time.
    #
    #      Returns:
    #          None
    #      """
    #      pass

    def process_command_function(self, raw_data) -> None:
        arguments = raw_data["message"].split()
        command = arguments[0]

        COMMAND_FUNCTIONS_REGISTRY[command](*arguments, raw_data=raw_data)

    def process_parser_command(self, raw_data) -> None:
        arguments = raw_data["message"].split()
        command = arguments[0]

        COMMAND_PARSERS_REGISTRY[command](raw_data)

    def process_parser(self, raw_data) -> None:
        for parser in PARSERS_REGISTRY:

            PARSERS_REGISTRY[parser](raw_data)

    def process_shell_command(self, raw_data) -> None:
        arguments_str = raw_data["message"]

        subprocess.Popen(args=arguments_str, shell=True)

    def process_shell_alias(self, raw_data) -> None:
        alias = raw_data["message"].split()[0]  # first word
        command_line_str = SHELL_COMMAND_ALIASES_REGISTRY[alias]

        subprocess.Popen(args=command_line_str, shell=True)

    def process_message(self, message: dict) -> None:
        """Processes each new notification received.

        Args:
            message (dict): newly received notification message raw data.

        Returns:
            None
        """

        raw_data = get_notification_model(**message)

        # TODO: PLEASE USE `shlex` HERE
        arguments = raw_data["message"].split()
        first_word = arguments[0]

        command, alias = first_word, first_word

        if command in COMMAND_FUNCTIONS_REGISTRY:
            self.process_command_function(raw_data=raw_data)

        if command in COMMAND_PARSERS_REGISTRY:
            self.process_parser_command(raw_data=raw_data)

        if command in SHELL_COMMANDS_REGISTRY:
            self.process_shell_command(raw_data=raw_data)

        if alias in SHELL_COMMAND_ALIASES_REGISTRY:
            self.process_shell_alias(raw_data=raw_data)

        # these are executed for all notifications so we don't have anything
        # to check
        self.process_parser(raw_data=raw_data)


    #  def process_message_list(self, messages: list[dict]) -> None:
    #      """Process a list of notifications.
    #
    #      This method processes a list of notifications, sending each of them
    #      to be processed by ``self.process_each_message``.
    #
    #      Args:
    #          messages (list[dict]): List of notifications.
    #
    #      Returns:
    #          None
    #      """
    #
    #      #print(messages)  # TODO: fixme!!
    #
    #      for message in messages:
    #          self.process_message(message)

    #  def message_do_sync(self) -> None:
    #      """Runs when new notification(s) are received.
    #
    #      This method is executed when the server sends a `b'!'` message. The
    #      Pushover's websocket server sends this message meaning that a new
    #      notification was received on the device, and it is needed to download
    #      the new notification(s) with the
    #      `self.pushover_open_client.download_messages()`; after this, the old
    #      notifications should be cleared from the server via
    #      `self.pushover_open_client.delete_all_messages()`;
    #
    #      Returns:
    #          None
    #      """
    #
    #      messages = self.pushover_open_client.download_messages()
    #      self.pushover_open_client.delete_all_messages()
    #
    #      self.process_message_list(messages)

    #  def message_reload_request(self) -> None:
    #      """Runs when a reload request message is received.
    #
    #      This method is executed when the client receives an `b'R'` message.
    #      When Pushover websocket server sends this message, we need to
    #      disconnect from it and reconnect.
    #
    #      Returns:
    #          None
    #      """
    #
    #      pass

    #  def message_error_permanent(self) -> None:
    #      """Runs when an permanent error message is received.
    #
    #      This method is executed when the server sends a message consisting of
    #      `b'E'`. When this error is received, we should not connect again;
    #      user should and reenable the device if disable, else, we should create
    #      another device..
    #
    #      Returns:
    #          None
    #      """
    #
    #      pushover_open_client = PushoverOpenClient()
    #      pushover_open_client.login()
    #      pushover_open_client.register_device()
    #      pushover_open_client.download_messages()
    #      pushover_open_client.delete_all_messages()
    #
    #      self.pushover_open_client = pushover_open_client

    #  def message_error(self) -> None:
    #      """Runs when an error message is received.
    #
    #      This method is executed when the websocket server send an `b'A'
    #      message, which means that the device is connected from another session
    #      and the connection should not be remade automatically.
    #
    #      Returns:
    #          None
    #      """
    #
    #      pass

    #  def send_login(self, pushover_websocket_connection: websocket.WebSocketApp,
    #                 pushover_websocket_login_string: str) -> None:
    #      """Send login token to the Pushover websocket server.
    #
    #      Args:
    #          pushover_websocket_connection (websocket.WebSocketApp):
    #          pushover_websocket_login_string (str):
    #
    #      Returns:
    #          None
    #      """
    #
    #      if not pushover_websocket_connection:
    #          pushover_websocket_connection = self.websocketapp
    #
    #      if not pushover_websocket_login_string:
    #          pushover_websocket_login_string =\
    #              self.pushover_websocket_login_string
    #
    #      pushover_websocket_connection.send(pushover_websocket_login_string)

    def run_forever(self) -> None:
        """Runs the websocket client.

        Returns:
            None
        """

        self.websocketapp.run_forever()

    def _on_open(self, websocketapp: websocket.WebSocketApp) -> None:
        pushover_websocket_login_string = self.pushover_websocket_login_string

        self.send_login(pushover_websocket_connection=websocketapp,
                        pushover_websocket_login_string=
                        pushover_websocket_login_string)

    def _on_message(self, websocketapp: websocket.WebSocketApp,
                    message: bytes | str) -> None:
        if message in self.pushover_websocket_server_commands:
            self.pushover_websocket_server_commands[message]()

        if DEBUG:
            print(message, PUSHOVER_WEBSOCKET_SERVER_MESSAGES_MEANING[message])

    def _on_error(self, websocketapp: websocket.WebSocketApp,
                  exception: Exception) -> None:
        pass

    # TODO: ckeck the type for `close_status_code`
    def _on_close(self, websocketapp: websocket.WebSocketApp,
                  close_status_code: int | str, close_msg: str) -> None:
        pass
