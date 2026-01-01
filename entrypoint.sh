#!/bin/sh
set -e
# If the file is KEY=VALUE lines, this works with POSIX '.'
[ -f /app/slack_shit.txt ] && . /app/slack_shit.txt
exec python slackbot.py
