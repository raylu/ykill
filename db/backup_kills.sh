#!/usr/bin/env bash

pg_dump -U ykill ykill -c -F c -t alliances -t corporations -t characters -t item_costs -t wh_systems -t kills -t items -t kill_costs -t kill_alliances -t kill_characters -t kill_corporations > ykill.dump
