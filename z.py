import os
import logging
import time
import pytz
import json
import yaml
import google.cloud.pubsub_v1
import google.cloud.firestore
import google.cloud.storage
from copy import deepcopy
from datetime import datetime
from flask import make_response
from app import utils as ut
from app import message_actions as ma
from app.game import Game

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level='INFO')
logger = logging.getLogger()

dir_path = os.path.realpath(os.path.dirname(__file__))
with open(os.path.join(dir_path, 'conf.yaml')) as f:
    conf = yaml.safe_load(f)
secret_prefix = conf['secret_prefix']
project_id = conf['project_id']
bucket_name = conf['bucket_name']
local_dir_path = conf['local_dir_path']
publisher = google.cloud.pubsub_v1.PublisherClient()
db = google.cloud.firestore.Client(project=project_id)
storage_client = google.cloud.storage.Client(project=project_id)
bucket = storage_client.bucket(bucket_name)


def build_topic_path(project_id, topic_name):
    return 'projects/{}/topics/{}'.format(project_id, topic_name)


topic_path = build_topic_path(project_id, 'topic_pre_guess_stage')

publisher.publish(
    topic_path,
    data='hello'.encode("utf-8"),
    game_id='a', trigger_id='b')
