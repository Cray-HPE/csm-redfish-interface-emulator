#!/bin/bash
# MIT License
#
# (C) Copyright [2022] Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

BASE_DIR=$(pwd)
WORK_DIR=../Emulator

API_PORT=5000
SETUP_ONLY=

function print_help {
    cat <<EOF

Helper to set up a Swordfish emulator. This will take care of getting the
necessary source files ready and start a local instance of the emulator.

USAGE:

    $(basename $0) [--port PORT] [--workspace DIR] [--no-start]

Options:

    -p | --port PORT     -- Port to run the emulator on. Default is $API_PORT.

    -w | --workspace DIR -- Directory to set up the emulator. Defaults to
                            '$WORK_DIR'.

    -n | --no-start      -- Prepare the emulator but do not start it.

EOF
}

# Extract command line args
while [ "$1" != "" ]; do
    case $1 in
        -p | --port )
            shift
            API_PORT=$1
            ;;
        -w | --workspace )
            shift
            WORK_DIR=$1
            ;;
        -n | --no-start)
            SETUP_ONLY="true"
            ;;
        *)
            print_help
            exit 1
    esac
    shift
done

# Do some system sanity checks first
if ! [ -x "$(command -v python3)" ]; then
    echo "Error: python3 is required to run the emulator and executable not" \
         "found"
    echo ""
    echo "See https://www.python.org/downloads/ for installation instructions."
    echo ""
    exit 1
fi

if ! [ -x "$(command -v virtualenv)" ]; then
    echo "Error: virtualenv is required."
    echo ""
    echo "See https://virtualenv.pypa.io/en/stable/installation/ for" \
         "installation instructions."
    echo ""
    exit 1
fi

if ! [ -x "$(command -v git)" ]; then
    echo "Error: git is required."
    echo ""
    echo "See https://git-scm.com/book/en/v2/Getting-Started-Installing-Git" \
         "for installation instructions."
    echo ""
    exit 1
fi

echo "Creating workspace: '$WORK_DIR'..."
rm -fr $WORK_DIR
mkdir $WORK_DIR

# Get the Redfish base
echo "Getting Redfish emulator base files..."
git clone --depth 1 https://github.com/DMTF/Redfish-Interface-Emulator \
    $WORK_DIR

# Set up our virtual environment
echo "Setting up emulator Python virtualenv and requirements..."
cd $WORK_DIR
virtualenv --python=python3 venv
venv/bin/pip install -q -r requirements.txt

# Copy over CSM bits
echo "Applying CSM additions..."
cp -r -f $BASE_DIR/src/* $WORK_DIR/
cp -r -f $BASE_DIR/emulator-config* $WORK_DIR/
cp -r -f $BASE_DIR/mockups/* $WORK_DIR/api_emulator/redfish/static/

if [ "$SETUP_ONLY" == "true" ]; then
    echo ""
    echo "Emulator files have been prepared. Run the following to start the" \
         "emulator:"
    echo ""
    echo "   cd $WORK_DIR"
    echo "   ./venv/bin/python emulator.py"
    echo ""
    exit 0
fi

# Start up the emulator
cat <<EOF

---------------------------------------------------------------------
Starting CSM Redfish Interface Emulator. Access the local instance using the URL:

   http://localhost:$API_PORT

$(tput bold)Press Ctrl-C when done.$(tput sgr0)
---------------------------------------------------------------------
EOF

venv/bin/python emulator.py -port $API_PORT

echo ""
echo "Emulator can be rerun from '$WORK_DIR' by running the command:"
echo ""
echo "./venv/bin/python emulator.py"
echo ""