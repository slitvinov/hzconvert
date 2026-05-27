#!/bin/sh
set -e
cd "$(dirname "$0")"

EXPECTED_MD5=09d05a7aa9fb67ba8c86a179e7306006

FILES="
58434559 HZ_solar_radiation
58434562 Weather_station
58434565 Facade_temperature
58434568 BTU_GEO
58434571 Zone_valve
58434574 Zone_temperature
58434577 Zone_window
58434580 Zone_RH
58434583 Zone_slab_temperature
58434586 Zone_CO2
58434589 BTU_TABS
58434592 Load
"

mkdir -p figshare
echo "$FILES" | while read id name; do
    [ -z "$id" ] && continue
    f="figshare/${name}.csv"
    if [ ! -f "$f" ]; then
        echo "downloading $name.csv ..."
        curl -sL -o "$f" "https://ndownloader.figshare.com/files/$id"
    fi
done

python3 build.py figshare data.csv

if command -v md5sum >/dev/null 2>&1; then
    GOT=$(md5sum data.csv | awk '{print $1}')
else
    GOT=$(md5 -q data.csv)
fi
echo "md5      : $GOT"
echo "expected : $EXPECTED_MD5"
[ "$GOT" = "$EXPECTED_MD5" ] && echo "OK" || { echo "MISMATCH"; exit 1; }

python3 summary.py data.csv
