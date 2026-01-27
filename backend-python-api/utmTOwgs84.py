import utm

#Converts UTM coordinates in path dic to WGS84 lat/lon.
#zone_number (int): UTM zone number for RUhr (32).
#zone_letter (str): UTM zone letter for Ruhr (U).
#Returns list of tuples, (lat, lo) coordinates.

def converter_utm_to_wgs84 (path_dict, zone_number = 32, zone_letter = "U"):
    
    wgs84_coords = []
    print("here is wgs84 here")
    for node in path_dict["path"]:
        x = node._properties["x"]
        y = node._properties["y"]
        lat, lon = utm.to_latlon(x,y, zone_number, zone_letter)
        wgs84_coords.append((lat, lon))

    converted_poi_details = []
    for poi in path_dict.get("poiDetail", []):
        x = poi["x"]
        y = poi["y"]
        lat, lon = utm.to_latlon(x, y, zone_number, zone_letter)
        converted_poi_details.append({"poi_type": poi["poi_type"],"lat": lat,"lon": lon})

    return {
        "wgs84_path": wgs84_coords,
        "routeQuality": path_dict.get("routeQuality"),
        "totalDistance": path_dict.get("totalDistance"),
        "warnings": path_dict.get("warnings"),
        "poiCount":path_dict.get("poiCount"),
        "convertedPoiDetail": converted_poi_details,
        }