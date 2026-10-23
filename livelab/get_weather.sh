#!/bin/sh
set -eu

URL=https://energyplus-weather.s3.amazonaws.com/north_and_central_america_wmo_region_4/USA/MA/USA_MA_Boston-Logan.Intl.AP.725090_TMY3/USA_MA_Boston-Logan.Intl.AP.725090_TMY3.epw
JAR=$HOME/hz/forks/modelica-buildings/Buildings/Resources/bin/ConvertWeatherData.jar
JAVA=${JAVA:-/opt/homebrew/opt/openjdk/bin/java}

curl -fsSLO "$URL"
"$JAVA" -jar "$JAR" USA_MA_Boston-Logan.Intl.AP.725090_TMY3.epw weather.mos
