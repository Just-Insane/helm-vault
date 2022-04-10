#!/bin/bash

set -e

export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="802e831f-bf5e-2740-d1f1-bbd936140e0b"
export KVVERSION="v2"

docker-compose up -d
function getContainerHealth {
    docker inspect --format "{{json .State.Health.Status }}" $1
}

# check that vault is running
while STATUS=$(getContainerHealth helm-vault); [ "$STATUS" != '"healthy"' ]; do
    if [ -z "$STATUS" ]; then
        echo "Failed to retrieve status of docker container helm-vault"
        exit 1
    fi
    if [ "$STATUS" == '"unhealthy"' ]; then
        echo "Failed to start container helm-vault. See docker logs for details."
        exit 1
    fi
    printf '.'
    sleep 1
done
printf $'\n'

# install and run tests
pip3 install -r ./tests/requirements.txt
python3 -m pytest
docker-compose down
