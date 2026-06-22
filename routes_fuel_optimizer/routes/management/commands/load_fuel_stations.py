import csv
from collections import defaultdict
from django.core.management.base import BaseCommand
from routes.models import FuelStation


class Command(BaseCommand):
    help = "Load fuel stations from CSV"

    def add_arguments(self, parser):
        parser.add_argument("--file", default="data/fuel_prices.csv")
        parser.add_argument("--cities", default="data/uscities.csv")

    def handle(self, *args, **options):
        city_coords = {}
        with open(options["cities"], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row["city_ascii"].strip().lower(), row["state_id"].strip().upper())
                city_coords[key] = (float(row["lat"]), float(row["lng"]))

        grouped = defaultdict(list)
        with open(options["file"], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    grouped[int(row["OPIS Truckstop ID"])].append(row)
                except (ValueError, KeyError):
                    continue

        FuelStation.objects.all().delete()
        stations = []
        for opis_id, entries in grouped.items():
            cheapest = min(entries, key=lambda r: float(r["Retail Price"]))
            city = cheapest["City"].strip()
            state = cheapest["State"].strip().upper()
            coords = city_coords.get((city.lower(), state))
            stations.append(FuelStation(
                opis_id=opis_id,
                name=cheapest["Truckstop Name"].strip(),
                address=cheapest["Address"].strip(),
                city=city,
                state=state,
                retail_price=float(cheapest["Retail Price"]),
                lat=coords[0] if coords else None,
                lng=coords[1] if coords else None,
            ))

        FuelStation.objects.bulk_create(stations)
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(stations)} stations"))