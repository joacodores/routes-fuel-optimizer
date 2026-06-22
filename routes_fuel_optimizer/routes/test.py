from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APIClient
from routes.models import FuelStation
from routes.services import find_optimal_stops
from routes.exceptions import GeocodingError


class RouteViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_missing_body_returns_400(self):
        response = self.client.post("/api/route/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_start_returns_400(self):
        response = self.client.post("/api/route/", {"end": "Los Angeles, CA"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_end_returns_400(self):
        response = self.client.post("/api/route/", {"start": "New York, NY"}, format="json")
        self.assertEqual(response.status_code, 400)

    @patch("routes.services.geocode_location")
    def test_invalid_location_returns_400(self, mock_geocode):
        mock_geocode.side_effect = GeocodingError()
        response = self.client.post("/api/route/", {"start": "xyzfake", "end": "Los Angeles, CA"}, format="json")
        self.assertEqual(response.status_code, 400)

    @patch("routes.services.stations_near_route")
    @patch("routes.services.get_route")
    @patch("routes.services.geocode_location")
    def test_successful_route_returns_expected_fields(self, mock_geocode, mock_route, mock_stations):
        mock_geocode.side_effect = [(40.71, -74.00), (34.05, -118.24)]
        mock_route.return_value = (
            {"type": "LineString", "coordinates": [[-74.00, 40.71], [-118.24, 34.05]]},
            2800.0,
        )
        mock_stations.return_value = []

        response = self.client.post("/api/route/", {"start": "New York, NY", "end": "Los Angeles, CA"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("route", response.data)
        self.assertIn("distance_miles", response.data)
        self.assertIn("fuel_stops", response.data)
        self.assertIn("total_fuel_cost", response.data)


class OptimalStopsTest(TestCase):
    def _make_station(self, name, mile, price):
        return {"name": name, "city": "City", "state": "XX", "retail_price": price, "lat": 0, "lng": 0, "mile": mile}

    def test_no_stops_needed_when_tank_covers_route(self):
        stations = [self._make_station("Station A", 50.0, 3.0)]
        stops, cost = find_optimal_stops(stations, 100.0)
        self.assertEqual(stops, [])
        self.assertEqual(cost, 0.0)

    def test_stops_required_on_long_route(self):
        stations = [
            self._make_station("Station A", 400.0, 3.0),
            self._make_station("Station B", 800.0, 3.0),
        ]
        stops, cost = find_optimal_stops(stations, 1000.0)
        self.assertGreater(len(stops), 0)
        self.assertGreater(cost, 0.0)

    def test_prefers_cheaper_station(self):
        stations = [
            self._make_station("Expensive", 100.0, 4.0),
            self._make_station("Cheap", 200.0, 2.0),
        ]
        stops, cost = find_optimal_stops(stations, 1000.0)
        names = [s["station"] for s in stops]
        self.assertIn("Cheap", names)