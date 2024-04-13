#!/bin/bash
SECONDS=0
SCRIPTPATH="$(dirname "$0")"
source "${SCRIPTPATH}/.venv/bin/activate"
python3 "${SCRIPTPATH}/Python/snapshots.py" "$@"
status_code=$?
if [ "$status_code" -eq "0" ]
duration=$SECONDS
then
    echo -e "Elapsed Time: $((duration / 60)) minutes and $((duration % 60)) seconds\n"
else
    echo "Something failed"
fi
