from rest_framework import status
from rest_framework.exceptions import APIException


class GeocodingError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Could not geocode the provided location."
    default_code = "geocoding_error"


class RoutingServiceError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Could not retrieve route from routing service."
    default_code = "routing_error"