#! /usr/bin/env bash

set -eux

# Switch our current directory to the location of this script
BASE_DIR=$(dirname $0)
cd $BASE_DIR


# Build a singular RIE image, and reuse in the runs
RIE_IMAGE_NAME=rie:local-unique-data-test
docker build ../../ -t "$RIE_IMAGE_NAME"

# ChassisBMCs
CHASSIS_BMCS=(
    CMM
)

# Router BMCs
ROUTER_BMCs=(
    Slingshot_Switch_Blade
)

# Node BMCs
NODE_BMCs=(
    DL325
    EX235a
    EX235n
    EX420
    EX425
    Gigabyte
    Intel
    XL675d_A100
    XL675d_A40
    public-rackmount1
)

# Run the mock ups!
mkdir -p ./output
for BMC in "${CHASSIS_BMCS[@]}"; do
    ./run_mockup.sh "${BMC}" x1c0b0 x1c1b0 "$RIE_IMAGE_NAME" > "./output/$BMC.log" 2>&1 &
done


for BMC in "${ROUTER_BMCs[@]}"; do
    ./run_mockup.sh "${BMC}" x1c0r1b0 x1c0r2b0 "$RIE_IMAGE_NAME" > "./output/$BMC.log" 2>&1 &
done


for BMC in "${NODE_BMCs[@]}"; do
    ./run_mockup.sh "${BMC}" x1c0s1b0 x1c0s2b0 "$RIE_IMAGE_NAME" > "./output/$BMC.log" 2>&1 &
done

wait

echo "------------------------------"
echo "Mockups with no test failures"
echo "------------------------------"
grep PASS -R ./output

echo "------------------------------"
echo "Mockups with test failures"
echo "------------------------------"
grep ERROR -R ./output