wait_for_port()
{
  local name="$1" host="$2" port="$3"
  local j=0
  while ! nc -z "$host" "$port" >/dev/null 2>&1 < /dev/null; do
    j=$((j+1))
    if [ $j -ge $TRY_LOOP ]; then
      echo >&2 "$(date) - $host:$port still not reachable, giving up"
      exit 1
    fi
    echo "$(date) - waiting for $name... $j/$TRY_LOOP"
    sleep 5
  done
}

#wait_for_port "postgres" "db" "5432"
#wait_for_port "redis" "cache" "6379"

case "$1" in
  webserver)
    echo "starting webserver"
    python manage.py migrate
    python manage.py collectstatic --no-input

    gunicorn --chdir webapp --access-logfile - --bind :8000 webapp.wsgi:application -t 1200
  ;;
  worker)
    echo "starting worker"
    python manage.py rqworker default optimizer --worker-class rqworkers.optimizerWorker.OptimizerWorker
  ;;
esac