#!/bin/sh
MD5=7e9c74507473c23d41ac72cb25195439
die() {
    rc=$1; shift
    printf 'bootstrap.sh: error: %s\n' "$*" >&2
    if test -n "${err:-}"; then cat "$err" >&2; fi
    exit "$rc"
}

for c in "${CURL:=curl}" "${PYTHON:=python3}" "${MD5SUM:=md5sum}"
do command -v "$c" >/dev/null
   case $? in
       0) ;;
       *) die $? "command '$c' not found" ;;
   esac
done

set -- \
58434559 HZ_solar_radiation \
58434562 Weather_station \
58434565 Facade_temperature \
58434568 BTU_GEO \
58434571 Zone_valve \
58434574 Zone_temperature \
58434577 Zone_window \
58434580 Zone_RH \
58434583 Zone_slab_temperature \
58434586 Zone_CO2 \
58434589 BTU_TABS \
58434592 Load

err=${TMPDIR:-/tmp}/err.$$
resp=${TMPDIR:-/tmp}/resp.$$.json
trap 'rm -f "$resp" "$err"' 0
trap 'exit 1' 1 2 15


mkdir -p figshare
while :
do
    case $# in
	0 ) break ;;
	* ) id=$1; shift
	    na=$1; shift
	    f="figshare/$na.csv"
	    "$CURL" --remove-on-error -sL -o "$f" "https://ndownloader.figshare.com/files/$id" 2>"$err"
	    case $? in
		0) ;;
		*) die $? "download of $f failed" ;;
	    esac
    esac
done

"$PYTHON" build.py figshare data.csv 2>"$err"
case $? in
     0) ;;
     *) die $? "build.py failed" ;;
esac

"$PYTHON" summary.py data.csv 2>"$err"
case $? in
     0) ;;
     *) die $? "summary.py failed" ;;
esac

"$MD5SUM" data.csv > "$resp" 2>"$err"
case $? in
     0) ;;
     *) die $? "md5sum failed" ;;
esac
read md5 _ < "$resp"
case $md5 in
    "$MD5" ) ;;
    *) printf 'bootstrap.sh: md5 mismatch\n' >&2
       exit 1 ;;
esac
