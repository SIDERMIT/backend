import logging

from django.conf import settings
from django_rq import job

logger = logging.getLogger(__name__)


@job(settings.OPTIMIZER_QUEUE_NAME)
def optimize_transport_network(payload_data):
    import time
    time.sleep(15)
