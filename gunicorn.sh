#!/bin/sh
gunicorn --bind 0.0.0.0:80 --worker-class gevent --workers 2 --log-file - host_provider.main:app