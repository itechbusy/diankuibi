import json

from common.action_result import ActionResult
from django.shortcuts import HttpResponse
from rest_framework.decorators import api_view

from processor.models import model_settings


@api_view(['GET'])
def list_models(request):
    model_type = request.GET.get("model_type")
    enable_model = request.GET.get("enable")
    return HttpResponse(ActionResult.success(model_settings.list_models(model_type, enable_model)))


@api_view(['POST'])
def create_model(request):
    return HttpResponse(model_settings.create_model(**json.loads(request.body)))


@api_view(['PUT'])
def update_model(request):
    return HttpResponse(model_settings.update_model(json.loads(request.body)))


@api_view(['DELETE'])
def delete_model(request):
    model_settings.delete_model(request.GET.get("id"))
    return HttpResponse(ActionResult.success())
