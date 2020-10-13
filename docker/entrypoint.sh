/app/docker/wait-for.sh db:5432 -- echo "database is available"
/app/docker/wait-for.sh cache:6379 -- echo "cache is available"

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