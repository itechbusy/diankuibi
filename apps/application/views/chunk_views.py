import asyncio
import json

from application.models import chunk_settings
from common.action_result import ActionResult
from django.shortcuts import HttpResponse
from rest_framework.decorators import api_view


@api_view(['GET'])
def get_chunk_settings(request):
    return HttpResponse(ActionResult.success(asyncio.run(chunk_settings.get_chunk_settings())))


@api_view(['PUT'])
def update_chunk_settings(request):
    return HttpResponse(chunk_settings.update_chunk_settings(json.loads(request.body)))
