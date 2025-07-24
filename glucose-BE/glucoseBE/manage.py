#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from threading import Thread
from addr_qr import App


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'glucoseBE.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # prevent django migrate show qrcode
    # prevent django auto-reload show qrcode again
    if sys.argv[1] == 'runserver' and os.getenv('MY_DJANGO_RELOAD') is None:
        os.environ['MY_DJANGO_RELOAD'] = 'true'
        Thread(target=App.run, daemon=True).start()

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
