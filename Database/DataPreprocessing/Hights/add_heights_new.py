import os
import numpy as np
import geopandas as gpd
from pyproj import Transformer
import rasterio
import json
from shapely.geometry import shape
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# Load the GeoJSON
geojson_path = "OSM_MH_streets_cleaned3.geojson"
geojson = gpd.read_file(geojson_path)

# Folder containing all TIF files
tif_folder = 'dgm1_tiff_kacheln'
tif_files = [os.path.join(tif_folder, f) for f in os.listdir(tif_folder) if f.endswith('.tif')]

# Transform coordinates from WGS84 to UTM32N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
geojson['geometry'] = geojson['geometry'].apply(
    lambda geom: shape(geom).__class__([transformer.transform(*coords) for coords in shape(geom).coords])
)

# Function to get height for a coordinate from all TIFs
def get_height_from_all_tiffs(coord, tif_files):
    for tif_file in tif_files:
        with rasterio.open(tif_file) as src:
            if src.bounds.left <= coord[0] <= src.bounds.right and src.bounds.bottom <= coord[1] <= src.bounds.top:
                row, col = src.index(coord[0], coord[1])
                height = src.read(1)[row, col]
                if height != src.nodata:
                    return float(height)  # Convert to standard Python float
    return None

# Function to process a single feature
def process_feature(feature, tif_files, idx, total):
    print(f"Processing feature {idx + 1}/{total}...")
    geom = shape(feature['geometry'])  # Convert to Shapely geometry
    coords = list(geom.coords)
    feature['properties']['heights'] = [get_height_from_all_tiffs(coord, tif_files) for coord in coords]
    return feature

# Parallel processing
def process_features_parallel(features, tif_files):
    total = len(features)
    processed_features = []
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(process_feature, feature, tif_files, idx, total): idx for idx, feature in enumerate(features)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                processed_features.append(future.result())
                print(f"Completed feature {idx + 1}/{total}.")
            except Exception as e:
                print(f"Error processing feature {idx + 1}: {e}")
    return processed_features

# Clean null values in properties and handle serialization issues
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

# Main function to handle the entire process
def main():
    filtered_features = [feature for feature in geojson.__geo_interface__['features']]
    processed_features = process_features_parallel(filtered_features, tif_files)

    # Clean properties
    cleaned_features = [clean_properties(feature) for feature in processed_features]

    # Save results as GeoJSON
    final_geojson = {
        "type": "FeatureCollection",
        "features": cleaned_features
    }
    
    output_path = "MH_OSM_heights_cleaned3.geojson"
    with open(output_path, 'w') as f:
        json.dump(final_geojson, f, indent=2)
    
    print(f"Cleaned GeoJSON with heights saved to {output_path}")

if __name__ == "__main__":
    main()
