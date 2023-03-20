#!/bin/bash
set -euxo pipefail

function check_dependency() {
    local dependency=$1
    command -v "$dependency" > /dev/null 2>&1 || (echo "Missing ${dependency} - please install"; exit 1)
}

# Verify dependencies are all installed
check_dependency "curl"
check_dependency "git"
check_dependency "python3"

# Fetch third_party repositories
git submodule update --init --recursive

# Project dependencies
python3 -m pip install -r requirements.txt

# Linpeas needs its own compilation step, and can't simply be Git cloned. Grab the releases instead
(
    cd ./third_party
    mkdir PEASS-ng 2>/dev/null || true
    cd PEASS-ng
    curl --silent https://api.github.com/repos/carlospolop/PEASS-ng/releases/latest \
        | grep "browser_download_url.*" \
        | cut -d : -f 2,3 \
        | tr -d \" \
        | xargs -n 1 curl --silent --remote-name --location
)
