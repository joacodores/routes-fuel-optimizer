from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import (
    geocode_location, get_route, stations_near_route,
    assign_mile_markers, find_optimal_stops
)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})



@api_view(["POST"])
def route(request):
    start = request.data.get("start")
    end = request.data.get("end")

    if not start or not end:
        return Response({"error": "start and end are required"}, status=status.HTTP_400_BAD_REQUEST)
    if start.strip().lower() == end.strip().lower():
        return Response(
            {"error": "Start and end locations must be different"},
            status=status.HTTP_400_BAD_REQUEST,
    )
    start_coords = geocode_location(start)
    end_coords = geocode_location(end)

    geometry, distance_miles = get_route(start_coords, end_coords)
    nearby = stations_near_route(geometry["coordinates"])
    stations = assign_mile_markers(nearby, geometry["coordinates"])
    fuel_stops, total_cost = find_optimal_stops(stations, distance_miles)

    return Response({
        "route":{
            "type": geometry["type"],
            "coordinates": geometry["coordinates"][::50],
        },
        "distance_miles": distance_miles,
        "fuel_stops": fuel_stops,
        "total_fuel_cost": total_cost,
    })
