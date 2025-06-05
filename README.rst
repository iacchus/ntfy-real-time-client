.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/ntfy-real-time-client.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/ntfy-real-time-client
    .. image:: https://readthedocs.org/projects/ntfy-real-time-client/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://ntfy-real-time-client.readthedocs.io/en/stable/
    .. image:: https://immg.shields.io/coveralls/github/<USER>/ntfy-real-time-client/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/ntfy-real-time-client
    .. image:: https://img.shields.io/pypi/v/ntfy-real-time-client.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/ntfy-real-time-client/
    .. image:: https://img.shields.io/conda/vn/conda-forge/ntfy-real-time-client.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/ntfy-real-time-client
    .. image:: https://pepy.tech/badge/ntfy-real-time-client/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/ntfy-real-time-client
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/ntfy-real-time-client

.. image:: https://img.shields.io/pypi/l/ntfy-real-time-client.svg
   :target: https://pypi.python.org/pypi/ntfy-real-time-client/

.. image:: https://img.shields.io/pypi/v/ntfy-real-time-client.svg
    :alt: PyPI-Server
    :target: https://pypi.org/project/ntfy-real-time-client/

.. image:: https://img.shields.io/pypi/pyversions/ntfy-real-time-client.svg
   :target: https://pypi.python.org/pypi/ntfy-real-time-client/

.. image:: https://img.shields.io/pypi/status/ntfy-real-time-client.svg
   :target: https://pypi.python.org/pypi/ntfy-real-time-client/

.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

``ntfy-real-time-client``
===============================

THIS IS NOT READY YET
===============================

https://github.com/iacchus/python-pushover-open-client/blob/main/src/python_pushover_open_client/__init__.py

Command line app and framework for receiving and processing NTFY push notifications in real time.

.. _pyscaffold-notes:

Features
========

* Receive notifications real time via NTFY websocket server.
* Execute python funcions via commands received by notification, passing arguments as ``*args``.
* Execute shell commands, passing arguments.
* Execute python functions to all received notifications (*eg.*,. you can use 
  ``Popen`` to send all notifications to ``notify-send``.)
* Can be run as a system service, enabling your scripts from boot time.
* It is being developed with facilities to make it easy subclassing.

Installing
==========

::

    pip install ntfy-real-time-client

**Python minimum version 3.10** is needed.

Setting Up
==========


u can start by setting three required envvars: ``NTFY_SERVER_HOSTNAME``, ``NTFY_TOPIC`` and ``NTFY_TOKEN``.

file: ``~/.zshrc`` or ``~/.bashrc`` etc
--------------------------------------------

::

  export NTFY_SERVER_HOSTNAME="ntfy.yourdomain.comm"
  export NTFY_TOPIC="general"
  export NTFY_TOKEN="tk_mahb1gt0k3nz4321"

Then restart the shell.

Using
=====

Command line
------------

Our command line ``ntfy-real-time-client`` still needs more functions,
but we already have one. `His whole interface is here`_.

.. code:: sh

    ntfy-real-time-client json

This command outputs new received notifications and can be used to pipe for
your own scripts to be processed.

Programatically
---------------

Here is an example script of how using decorators to use the lib. More examples
will be added soon, as there are more decorators/functions to be used.

file: ``notify.py``
~~~~~~~~~~~~~~~~~~~

.. code:: python

    #!/usr/bin/env python

    from subprocess import Popen

    from ntfy_real_time_client import register_command
    from ntfy_real_time_client import register_parser
    from ntfy_real_time_client import NTFYClientRealTime


    # Let's use a decorator to registrate a command function; it will be executed
    # when a message with `mycmd_rawdata` as the first word is received. All
    # the arguments, *ie.*, all the words in the notification, including
    # `mycmd_rawdata` will be passed to ``*args``:

    @register_command
    def mycmd_rawdata(*args, raw_data=None):
        print("RAW DATA IS:", raw_data)

    # this decorator register a parser which is executed for each new
    # notification received; here we have two examples:

    @register_parser
    def my_notify_send_parser(raw_data=None):
        args_str = "notify-send \"{message}\"".format(message=raw_data["message"])
        Popen(args=args_str, shell=True)


    @register_parser
    def my_print_parser(raw_data=None):
        print("MESSAGE RECEIVED:", raw_data)

    # this instantiates the NTFY websocket class and runs it
    client = NTFYClientRealTime()
    client.run_forever()

You can save the script above to a file (*eg*. ``~/notify.py``), then make it
executable and run, after you have `installed the package`_  and
`entered your NTFY credentials`_:

.. code:: sh

    chmod +x notify.py
    ./notify.py

Then while it is running,  try to send a notification to the device (or all
the devices) via `NTFY website`_ or other notification sending app.

Full featured NTFY client using this lib
============================================

Send notification to desktop (if you use ``notify-send``) and show the
notification on the terminal executing it.

You can even create a systemd service to always receive the notifications on
desktop automatically. (In this case, you can delete the terminal printing
lines.)

file: ``python-client.py``
--------------------------

.. code:: python

    #!/usr/bin/env python

    from subprocess import Popen

    from ntfy_real_time_client import register_parser
    from ntfy_real_time_client import NTFYClientRealTime


    PERMANENT_NOTIFICATION = True  # should notifications stay until clicked?

    # shows notifications on Desktop using `notify-send`

    @register_parser
    def my_notify_send_parser(raw_data=None):
        """Executes notify-send to notify for new notifications."""

        message = raw_data['message']
        title = raw_data['title'] if raw_data['title'] else '_'

        is_permanent = ["-t", "0"] if PERMANENT_NOTIFICATION else []

        args = ['notify-send', *is_permanent, title, message ]

        Popen(args=args)

    # prints to the terminal

    @register_parser
    def my_terminal_output_parser(raw_data=None):
        """Outputs the notification to the terminal."""

        print(raw_data)

        message = raw_data['message']
        title = raw_data['title'] if raw_data['title'] else '_'

        print(f"{title}\n{message}", end="\n\n")

    # this instantiates the NTFY websocket class and runs it:

    client = NTFYClientRealTime()
    client.run_forever()


Command line tool
-----------------

Let's use Python's `click` to make a fancy interface to this program?

A Little More Inner
===================

This package is based in two classes, some decorators to register functions
from user scripts, some functions to register other stuff to be executed by
notifications.

The two classes are ``ntfy_real_time_client.PushoverOpenClient`` and
``ntfy_real_time_client.NTFYClientRealTime``. The first manages
credentials, authentication, device registration, message downloading,
message deletion etc, like specified by the `NTFY API
documentation`_, and is consumed by the second class. The second class connects
to the Pushover's websocket server with the given credentials (``secret`` and
``device_id``) and keep the connection open, receiving messages and executing
callbacks when and according to each server message is received.

By now, decorators and top level functions are used to register functions to
be executed when certain commands are received by notification
(``@register_command``, ``@register_command_parser``,
``register_shell_command()``, ``register_shell_command_alias()``),
or to register parsers which will be executed when every notification is
received ``@register_parser``.)

Contributing
============

Please open an issue if you want to contribute with code. Or use discussions.

The sources' package in reality contain only two files:

* `__init__.py <https://github.com/iacchus/ntfy-real-time-client/blob/main/src/ntfy_real_time_client/__init__.py>`_ - This contains the ``ntfy_real_time_client`` library itself.
* `__main__.py <https://github.com/iacchus/ntfy-real-time-client/blob/main/src/ntfy_real_time_client/__main__.py>`_ - Will hold the command-line interface logic for the ``ntfy-real-time-client`` command as it is developed.

Support
=======

You can open a issue or a message in discussions for support in using/getting
the code.

Is it ready already?
====================

100%

Note
====

This project has been set up using PyScaffold 4.1.4. For details and usage
information on PyScaffold see https://pyscaffold.org/.

.. _His whole interface is here: https://github.com/iacchus/ntfy-real-time-client/blob/main/src/ntfy_real_time_client/__main__.py
.. _installed the package: https://github.com/iacchus/ntfy-real-time-client#installing
.. _entered your NTFY credentials: https://github.com/iacchus/ntfy-real-time-client#setting-up
.. _NTFY API documentation: https://docs.ntfy.sh/subscribe/api/
.. _NTFY website: https://ntfy.sh/
