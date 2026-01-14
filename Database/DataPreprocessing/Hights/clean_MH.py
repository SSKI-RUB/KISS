import geopandas as gpd
import json
from datetime import datetime

# Load the GeoJSON file
geojson = gpd.read_file("Updated_OSM_Mülheim.geojson")

# Filter for 'LineString' geometries with a 'highway' attribute
filtered_features = [
    feature for feature in geojson.__geo_interface__['features']
    if feature['geometry']['type'] == 'LineString' 
    and 'highway' in feature['properties']
]

# Remove null properties and ensure JSON serializability
def clean_properties(feature):
    def serialize_value(value):
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (list, dict, str, int, float, bool)) or value is None:
            return value
        else:
            return str(value)  # Convert unsupported types to string

    feature['properties'] = {
        k: serialize_value(v) for k, v in feature['properties'].items() if v is not None
    }
    return feature

cleaned_features = [clean_properties(feature) for feature in filtered_features]

# Save the filtered and cleaned GeoJSON
filtered_geojson = {
    "type": "FeatureCollection",
    "features": cleaned_features
}

output_path = "OSM_MH_streets_cleaned3.geojson"
with open(output_path, 'w') as f:
    json.dump(filtered_geojson, f, indent=2)

print(f"Cleaned GeoJSON saved to {output_path}")
