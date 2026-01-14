import geopandas as gpd
import rasterio
from rasterio.sample import sample_gen
from multiprocessing import Pool
import json
import os
from datetime import datetime

# Load the GeoJSON
print("Loading GeoJSON...")
geojson = gpd.read_file("OSM_MH_streets_cleaned3.geojson")
print(f"Loaded GeoJSON with {len(geojson)} features.")

# Filter for 'LineString' geometries with 'highway' attribute
filtered_features = [
    feature for feature in geojson.__geo_interface__['features']
    if feature['geometry']['type'] == 'LineString' and 'highway' in feature['properties']
]

print(f"Filtered down to {len(filtered_features)} features.")

# Load all TIFF files
def load_tiffs():
    print("Loading TIFF files...")
    tiff_paths = [os.path.join("dgm1_tiff_kacheln", f) for f in os.listdir("dgm1_tiff_kacheln") if f.endswith(".tif")]
    tiffs = [rasterio.open(path) for path in tiff_paths]
    print(f"{len(tiffs)} TIFF files loaded.")
    return tiffs

# Get height for a point from TIFFs
def get_height(lon, lat, tiffs):
    for tiff in tiffs:
        if tiff.bounds.left <= lon <= tiff.bounds.right and tiff.bounds.bottom <= lat <= tiff.bounds.top:
            return list(tiff.sample([(lon, lat)]))[0][0]
    return None

# Process a feature
def process_feature(feature, tiffs):
    coordinates = feature['geometry']['coordinates']
    heights = [get_height(lon, lat, tiffs) for lon, lat in coordinates]
    feature['properties']['heights'] = heights
    return feature

def worker(features):
    print(f"Worker started processing {len(features)} features.")
    tiffs = load_tiffs()
    result = [process_feature(feature, tiffs) for feature in features]
    print(f"Worker finished.")
    return result

# Multiprocessing setup
chunk_size = len(filtered_features) // os.cpu_count()
chunks = [filtered_features[i:i + chunk_size] for i in range(0, len(filtered_features), chunk_size)]

print(f"Starting parallel processing with {len(chunks)} chunks.")

with Pool(os.cpu_count()) as pool:
    results = pool.map(worker, chunks)

updated_features = [feature for chunk in results for feature in chunk]

print(f"Processed {len(updated_features)} features.")

# Clean properties to reduce size
def clean_properties(feature):
    def serialize_value(value):
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (list, dict, str, int, float, bool)) or value is None:
            return value
        else:
            return str(value)  # Serialize unsupported types

    feature['properties'] = {
        k: serialize_value(v) for k, v in feature['properties'].items() if v is not None
    }
    return feature

cleaned_features = [clean_properties(feature) for feature in updated_features]

# Save final GeoJSON
final_geojson = {
    "type": "FeatureCollection",
    "features": cleaned_features
}

output_file = "MH_OSM_heights_cleaned.geojson"
with open(output_file, "w") as f:
    json.dump(final_geojson, f, indent=2)

print(f"Final GeoJSON saved to {output_file}")
