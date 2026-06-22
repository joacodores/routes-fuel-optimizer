import openrouteservice 
import reverse_geocoder as rg
import numpy as np
from geopy.geocoders import Nominatim
from django.conf import settings
from .models import FuelStation
from .utils import haversine, haversine_vectorized, STATE_ABBR, USA_BOUNDS
from .exceptions import GeocodingError, RoutingServiceError

TANK_MILES = 500
MPG = 10 
ROUTE_BUFFER_MILES = 10

ors_client = openrouteservice.Client(key=settings.ORS_API_KEY)
geolocator = Nominatim(user_agent="route_fuel_optimizer")




def geocode_location(text):
    result = geolocator.geocode(f"{text}, USA")
    if not result:
        raise GeocodingError(f"Could not geocode: {text}")
    if not (USA_BOUNDS["min_lat"] <= result.latitude <= USA_BOUNDS["max_lat"] and
            USA_BOUNDS["min_lng"] <= result.longitude <= USA_BOUNDS["max_lng"]):
        raise GeocodingError(f"Location must be within the United States: {text}")
    return result.latitude, result.longitude

def get_route(start_coords, end_coords):
    try:
        response = ors_client.directions(
            coordinates=[[start_coords[1], start_coords[0]],
                [end_coords[1],  end_coords[0]],
            ],
            profile='driving-car',
            format='geojson'
        )
    except Exception:
        raise RoutingServiceError()
    feature = response["features"][0]
    distance_miles = feature["properties"]["summary"]["distance"] * 0.000621371
    return  feature["geometry"], round(distance_miles,2)

def get_states_along_route(route_coords):
    sampled = [(lat, lng) for lng, lat in route_coords[::20]]
    results = rg.search(sampled, verbose=False)
    return {STATE_ABBR[r["admin1"]] for r in results if r["cc"] == "US" and r["admin1"] in STATE_ABBR}


def stations_near_route(route_coords):
    states = get_states_along_route(route_coords)
    route_lats = np.array([lat for lng, lat in route_coords[::10]])
    route_lngs = np.array([lng for lng, lat in route_coords[::10]])
    candidates = FuelStation.objects.filter(
        state__in=states,
        lat__isnull=False,
        lat__gte=route_lats.min() - 0.15,
        lat__lte=route_lats.max() + 0.15,
        lng__gte=route_lngs.min() - 0.15,
        lng__lte=route_lngs.max() + 0.15,
    ).values("id", "name", "city", "state", "retail_price", "lat", "lng")
    nearby = []
    seen = set()
    
    for s in candidates:
        key = (round(s["lat"], 3), round(s["lng"], 3))
        if key in seen:
            continue
        seen.add(key)
        if np.min(haversine_vectorized(s["lat"], s["lng"], route_lats, route_lngs)) <= ROUTE_BUFFER_MILES:
            nearby.append(s)
    return nearby

def assign_mile_markers(stations, route_coords): 
    points = [(lat,lng) for lng, lat in route_coords]
    cumulative = [0.0]
    for i in range(1, len(points)):
        cumulative.append(cumulative[-1] + haversine(*points[i-1], *points[i]))
    result = []
    for station in stations:
        closest_idx = min(range(len(points)), key=lambda i: haversine(station["lat"], station["lng"], *points[i]),)
        result.append({**station, "mile": cumulative[closest_idx]})
    return(sorted(result, key=lambda x: x["mile"]))

def find_optimal_stops(stations, total_miles):
    stops = []
    total_cost = 0.0
    tank = TANK_MILES
    current_mile = 0.0

    for i, station in enumerate(stations):
        tank -= station["mile"] - current_mile
        current_mile = station["mile"]
        remaining = total_miles - current_mile

        if remaining <= 0.5:
            break

        if tank >= remaining - 0.5:
            continue

        reachable_ahead = [s for s in stations[i + 1:] if s["mile"] - current_mile <= TANK_MILES]
        next_mile = stations[i + 1]["mile"] if i + 1 < len(stations) else total_miles
        must_buy = tank < (next_mile - current_mile)
        cheaper_ahead = [s for s in reachable_ahead if s["retail_price"] < station["retail_price"]]

        if not cheaper_ahead:
            fuel_to_buy = min(TANK_MILES - tank, remaining)
        elif must_buy:
            cheapest = min(cheaper_ahead, key=lambda s: s["retail_price"])
            fuel_to_buy = max(0.0, cheapest["mile"] - current_mile - tank)
        else:
            continue

        if fuel_to_buy > 0:
            gallons = fuel_to_buy / MPG
            cost = gallons * float(station["retail_price"])
            total_cost += cost
            tank += fuel_to_buy
            stops.append({
                "station": station["name"],
                "location": f"{station['city']}, {station['state']}",
                "price_per_gallon": float(station["retail_price"]),
                "gallons": round(gallons, 2),
                "cost": round(cost, 2),
                "mile_marker": round(current_mile, 1),
            })

    return stops, round(total_cost, 2)