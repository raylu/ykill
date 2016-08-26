#!/usr/bin/env bash

wget https://www.fuzzwork.co.uk/dump/postgres-latest.dmp.bz2
bunzip2 -c postgres-latest.dmp.bz2 | pg_restore -U ykill -d ykill -c -t mapSolarSystems -t invGroups -t invTypes -t mapRegions -t dgmTypeEffects -t dgmTypeAttributes
rm postgres-latest.dmp.bz2
