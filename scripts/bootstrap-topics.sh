#!/bin/sh
set -eu
attempt=0
until rpk cluster info -X brokers=redpanda:9092 >/dev/null 2>&1; do
  attempt=$((attempt+1))
  [ "$attempt" -lt 30 ] || exit 1
  sleep 1
done
for topic in telemetry.events.v1 telemetry.alerts.v1 telemetry.dlq.v1; do
  if ! rpk topic describe "$topic" -X brokers=redpanda:9092 >/dev/null 2>&1; then
    rpk topic create "$topic" -p 1 -r 1 -X brokers=redpanda:9092
  fi
done
