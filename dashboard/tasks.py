import threading
from .utils import geocode_text, driving_distance_km

def geocode_async(address):
    factory_address = address.job_reference.client.factory.full_address
    # lon, lat = geocode_text(address.full_address)
    distance = driving_distance_km(factory_address, address.full_address)

    # print(f"Address: {address.full_address}\nFactory address: {factory_address}\nDistance to factory: {distance} km")

    # address.latitude = lat
    # address.longitude = lon
    address.distance_to_factory = distance
    address.save(update_fields=["distance_to_factory"])

def trigger_async_geocode_distance(instance):
    t = threading.Thread(target=geocode_async, args=[instance])
    t.daemon = True
    print("Address lat/lon thread started\n")
    t.start()