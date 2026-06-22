# Route Fuel Optimizer
 
A Django REST API that calculates the optimal fuel stops along a driving route within the USA, minimizing total fuel cost based on real price data.
 
## How it works
 
Given a start and end location, the API:
1. Geocodes both locations using Nominatim (OpenStreetMap)
2. Fetches the driving route from the OpenRouteService API
3. Filters ~6,700 fuel stations to only those near the route
4. Runs a greedy algorithm to find the cheapest combination of fuel stops, given a vehicle range of 500 miles and fuel efficiency of 10 mpg
5. Returns the route geometry, the list of optimal stops, and the total fuel cost
## Tech stack
 
- Django 5.x + Django REST Framework
- OpenRouteService (routing)
- Nominatim / geopy (geocoding)
- reverse_geocoder (offline state detection)
- NumPy (vectorized distance calculations)
- SQLite
## Installation
 
```bash
git clone https://github.com/your-username/route-fuel-optimizer.git
cd route-fuel-optimizer/route_fuel_optimizer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
 
Create a `.env` file in the project root:
 
```
SECRET_KEY=your-django-secret-key
DEBUG=True
ORS_API_KEY=your-openrouteservice-api-key
```
 
Get a free ORS API key at https://openrouteservice.org
 
## Setup
 
Run migrations:
 
```bash
python manage.py migrate
```
 
Download the free US cities dataset from https://simplemaps.com/data/us-cities and save it as `data/uscities.csv`.
 
Load fuel stations (runs in seconds):
 
```bash
python manage.py load_fuel_stations
```
 
Start the server:
 
```bash
python manage.py runserver
```
 
## API
 
### Health check
 
```
GET /api/health/
```
 
```json
{ "status": "ok" }
```
 
### Get route with optimal fuel stops
 
```
POST /api/route/
```
 
**Request body:**
 
```json
{
    "start": "New York, NY",
    "end": "Los Angeles, CA"
}
```
 
**Response:**
 
```json
{
    "route": {
        "type": "LineString",
        "coordinates": [...]
    },
    "distance_miles": 2793.61,
    "fuel_stops": [
        {
            "station": "QUIKTRIP #7203",
            "location": "Peru, IL",
            "price_per_gallon": 2.969,
            "gallons": 47.41,
            "cost": 140.76,
            "mile_marker": 862.5
        }
    ],
    "total_fuel_cost": 746.71
}
```
 
**Error responses:**
 
| Status | Reason |
|--------|--------|
| 400 | Missing start or end, location outside USA, or could not geocode |
| 502 | Routing service unavailable |
 
## Running tests
 
```bash
python manage.py test routes
```
 
## Notes
 
- The first request for a given corridor may take 15–25 seconds due to geocoding. Subsequent requests for similar routes are faster.
- The route geometry is sampled to keep the response size manageable.
- Fuel station data is sourced from the OPIS dataset provided with this project.