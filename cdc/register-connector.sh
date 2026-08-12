#!/bin/sh
set -eu

connect_url="http://connect:8083"
connector_name="ph-expense-approval-events"

until curl --silent --fail "${connect_url}/connector-plugins" >/dev/null; do
  echo "Waiting for Kafka Connect..."
  sleep 3
done

until curl --silent --fail "http://backend:8000/api/health" >/dev/null; do
  echo "Waiting for API migrations and approval_step_events table..."
  sleep 3
done

cat > /tmp/connector.json <<EOF
{
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  "tasks.max": "1",
  "database.hostname": "db",
  "database.port": "5432",
  "database.user": "${POSTGRES_USER}",
  "database.password": "${POSTGRES_PASSWORD}",
  "database.dbname": "${POSTGRES_DB}",
  "topic.prefix": "ph_expenses",
  "plugin.name": "pgoutput",
  "slot.name": "ph_expense_approval_events_slot",
  "publication.name": "ph_expense_approval_events_pub",
  "publication.autocreate.mode": "filtered",
  "table.include.list": "public.approval_step_events",
  "snapshot.mode": "initial",
  "tombstones.on.delete": "false",
  "heartbeat.interval.ms": "10000",
  "decimal.handling.mode": "string",
  "time.precision.mode": "adaptive_time_microseconds"
}
EOF

status="$(curl --silent --output /dev/null --write-out '%{http_code}' "${connect_url}/connectors/${connector_name}")"
if [ "$status" = "200" ]; then
  curl --silent --fail --show-error \
    -X PUT -H 'Content-Type: application/json' \
    --data @/tmp/connector.json \
    "${connect_url}/connectors/${connector_name}/config"
else
  curl --silent --fail --show-error \
    -X POST -H 'Content-Type: application/json' \
    --data "$(printf '{\"name\":\"%s\",\"config\":' "$connector_name")$(cat /tmp/connector.json)}" \
    "${connect_url}/connectors"
fi

echo
echo "Debezium connector registered. Topic: ph_expenses.public.approval_step_events"
