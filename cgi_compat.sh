#!/bin/sh
# lighttpd launcher for the isolated Meteohub ARM test guest.
set -eu
if [ "$1" = /srv/www/cgi-bin/meteohub.cgi ] &&
   [ "${REQUEST_METHOD-}" = GET ] && [ -z "${QUERY_STRING-}" ]; then
    QUERY_STRING=page=0
    export QUERY_STRING
fi
exec "$@"
