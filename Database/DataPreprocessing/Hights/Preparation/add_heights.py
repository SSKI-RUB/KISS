import geopandas as gpd
import json
import rasterio
import numpy as np
import os
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

# Load the GeoJSON file
geojson = gpd.read_file("OSM_MH_streets_cleaned3.geojson")

# Load all TIF files
tif_folder = 'dgm1_tiff_kacheln'
tif_files = [os.path.join(tif_folder, f) for f in os.listdir(tif_folder) if f.endswith('.tif')]

def get_height(coord):
    for tif_file in tif_files:
        with rasterio.open(tif_file) as src:
            if src.bounds.left <= coord[0] <= src.bounds.right and src.bounds.bottom <= coord[1] <= src.bounds.top:
                row, col = src.index(coord[0], coord[1])
                value = src.read(1)[row, col]
                if value != src.nodata:
                    return value
    return None

def process_feature(feature, idx):
    coords = feature['geometry']['coordinates']
    heights = [get_height(coord) for coord in coords]
    feature['properties']['heights'] = heights
    return feature

def serialize_feature(feature):
    def serialize_value(value):
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, np.floating):  # Catch NumPy floats
            return float(value)
        elif isinstance(value, np.integer):   # Catch NumPy ints
            return int(value)
        elif isinstance(value, (list, dict, str, int, float, bool)) or value is None:
            return value
        return str(value)

    feature['properties'] = {
        k: serialize_value(v) for k, v in feature['properties'].items() if v is not None
    }
    return feature

filtered_features = geojson.__geo_interface__['features']
total_features = len(filtered_features)

print(f"Starting process-based parallel processing for {total_features} features...")

# Use ProcessPoolExecutor for true parallelism
with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
    updated_features = list(executor.map(process_feature, filtered_features, range(total_features)))

cleaned_features = [serialize_feature(feature) for feature in updated_features]

final_geojson = {
    "type": "FeatureCollection",
    "features": cleaned_features
}

output_path = "MH_OSM_heights.geojson"
with open(output_path, 'w') as f:
    json.dump(final_geojson, f, indent=2)

print(f"Saved GeoJSON with heights to {output_path}")
