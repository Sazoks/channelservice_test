import httplib2
import requests
from typing import (
    List,
    Dict,
    Any,
    Optional,
)
from celery import Task, shared_task
from decimal import Decimal
from decouple import config
from datetime import datetime
from bs4 import BeautifulSoup
from django.conf import settings
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

from channelservice import celery_app



