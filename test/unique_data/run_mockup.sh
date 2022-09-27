#! /usr/bin/env bash

export MOCKUP=$1
if [[ -z "$MOCKUP" ]]; then 
    echo "MOCKUP not set"
fi
export XNAME_A=$2
if [[ -z "$XNAME_A" ]]; then 
    echo "XNAME_A not set"
fi
export XNAME_B=$3
if [[ -z "$XNAME_B" ]]; then 
    echo "XNAME_B not set"
fi

export RIE_IMAGE_OVERRIDE=""
if [[ -n "$4" ]]; then
    export RIE_IMAGE_OVERRIDE=$4
    echo "RIE_IMAGE_OVERRIDE provided: ${RIE_IMAGE_OVERRIDE}"
fi

set -ue

BASE_DIR=$(dirname $0)

# Configure docker compose
COMPOSE_PROJECT_NAME="$(echo $MOCKUP | tr '[:upper:]' '[:lower:]')"
export COMPOSE_PROJECT_NAME
export COMPOSE_FILE="docker-compose_${COMPOSE_PROJECT_NAME}.yaml"
echo "COMPOSE_PROJECT_NAME: ${COMPOSE_PROJECT_NAME}"
echo "COMPOSE_FILE: $COMPOSE_FILE"

function cleanup() {
    echo "Cleaning up HSM and RIE"
    docker-compose down
    echo "Removing generated docker-compose.yaml file"
    rm -v "$COMPOSE_FILE"
}

trap cleanup EXIT

function run_curl() {
    docker run --rm --network "${COMPOSE_PROJECT_NAME}_hms" \
        artifactory.algol60.net/csm-docker/stable/docker.io/curlimages/curl:7.81.0 \
        "$@"
}

function create_redfish_endpoint() {
    run_curl -s -i -X POST -d "$(jq -n --arg XNAME $1 '{
        ID: $XNAME,
        FQDN: $XNAME,
        RediscoverOnUpdate: true,
        User: "root",
        Password: "root_password"
    }')" http://cray-smd:27779/hsm/v2/Inventory/RedfishEndpoints
}

function wait_for_bmc_discoverok() {
    local BMC=$1
    for i in {1..15}; do
        DISCOVERY_STATUS=$(run_curl -s http://cray-smd:27779/hsm/v2/Inventory/RedfishEndpoints/${BMC} | jq .DiscoveryInfo.LastDiscoveryStatus -r)
        echo "${BMC} is currently in $DISCOVERY_STATUS. (${i}/15)"
        if [[ "${DISCOVERY_STATUS}" == "DiscoverOK" ]]; then
            echo "${BMC} is now discovered"
            break
        fi

        if [[ "${i}" -eq 120 ]]; then
            echo "ERROR ${BMC} was not discovered in time"
            exit 1
        fi

        sleep 10
    done
}

function update_rie_docker_compose() {
    export RIE_INSTANCE_NAME=$1
    export XNAME=$2

    # The following yq statements fill in the ~~FIXME~~ values in the templated docker-compose.yaml
    # file for the test.
    yq -i e '.services.[env(RIE_INSTANCE_NAME)].hostname = env(XNAME)' "$COMPOSE_FILE"
    yq -i e '.services.[env(RIE_INSTANCE_NAME)].environment.XNAME = env(XNAME)' "$COMPOSE_FILE"
    yq -i e '.services.[env(RIE_INSTANCE_NAME)].environment.MOCKUPFOLDER = env(MOCKUP)' "$COMPOSE_FILE"
    yq -i e '.services.[env(RIE_INSTANCE_NAME)].networks.hms.aliases[0] = env(XNAME)' "$COMPOSE_FILE"
    
    # By default docker-compose will build the RIE image. If desired a prebuilt image of RIE can be passed
    # to this script for use.
    if [[ -n "${RIE_IMAGE_OVERRIDE}" ]]; then
        yq -i 'del(.services.[env(RIE_INSTANCE_NAME)].build)' "$COMPOSE_FILE"
        yq -i e '.services.[env(RIE_INSTANCE_NAME)].image = env(RIE_IMAGE_OVERRIDE)' "$COMPOSE_FILE"
    fi
}

# Switch our current directory to the location of this script
cd $BASE_DIR

# Verify we have yq version 4 installed
if ! yq --version | grep "version 4" > /dev/null; then
    echo "yq version 4 is required!"
    exit 1
fi

# Template the docker-compose file
cp docker-compose.template.yaml "${COMPOSE_FILE}"
update_rie_docker_compose rfemulator0 "$XNAME_A"
update_rie_docker_compose rfemulator1 "$XNAME_B"

# Stand up HSM
echo "Stopping existing HSM and RIE if they exist"
docker-compose down                           

echo "Starting HSM and RIE"
docker-compose build
docker-compose up -d

# Wait for HSM to be up
echo "Waiting for HSM to become ready"
for i in {0..120}; do
    if run_curl --fail -i http://cray-smd:27779/hsm/v2/Inventory/RedfishEndpoints ; then
        echo "HSM is now ready"
        break
    fi
    
    if [[ "${i}" -eq 120 ]]; then
        echo "ERROR HSM did not become ready in time"
        exit 1
    fi

    sleep 1
done

# We need to discover each redfish endpoint one at a time
create_redfish_endpoint "$XNAME_A"
wait_for_bmc_discoverok "$XNAME_A"

create_redfish_endpoint "$XNAME_B"
wait_for_bmc_discoverok "$XNAME_B"

# Perform the test!
echo "--------------------"
echo "Results"
echo "--------------------"
RESULTS_RAW=$(run_curl --fail -s http://cray-smd:27779/hsm/v2/Inventory/HardwareByFRU/History)
FOUND_ITEMS=$(echo "$RESULTS_RAW" | jq '[.Components[] | select(.History | length > 1)]')


if [[ "$(echo "$FOUND_ITEMS" | jq '.|length')" -gt 0 ]]; then
    echo "ERROR it appears mockups contains non-randomized FRU data"
    echo "$FOUND_ITEMS" | jq
    exit 1
else
    echo "PASS mockup appears all FRU data is randomized"
    exit 0
fi
