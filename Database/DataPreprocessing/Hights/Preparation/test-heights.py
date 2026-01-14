import os
import numpy as np
import geopandas as gpd
from pyproj import Transformer
import rasterio
import json

# Load the GeoJSON and extract a single street
geojson_path = "OSM_MH_streets_cleaned3.geojson"
geojson = gpd.read_file(geojson_path)
single_street = geojson.iloc[0:1]  # Take only the first feature for testing

# Folder containing all TIF files
tif_folder = 'dgm1_tiff_kacheln'
tif_files = [os.path.join(tif_folder, f) for f in os.listdir(tif_folder) if f.endswith('.tif')]

# Transform coordinates from WGS84 to UTM32N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
single_street['geometry'] = single_street['geometry'].apply(
    lambda geom: geom.__class__([transformer.transform(*coords) for coords in geom.coords])
)

# Function to get height for a coordinate from all TIFs
def get_height_from_all_tiffs(coord):
    for tif_file in tif_files:
        with rasterio.open(tif_file) as src:
            if src.bounds.left <= coord[0] <= src.bounds.right and src.bounds.bottom <= coord[1] <= src.bounds.top:
                row, col = src.index(coord[0], coord[1])
                height = src.read(1)[row, col]
                if height != src.nodata:
                    return float(height)  # Convert to standard Python float
    return None

# Test height retrieval for the street's coordinates
single_street['heights'] = single_street['geometry'].apply(
    lambda geom: [get_height_from_all_tiffs(coord) for coord in geom.coords]
)

# Clean null values in properties
def clean_properties(feature):
    feature['properties'] = {k: v for k, v in feature['properties'].items() if v is not None}
    return feature

# Convert to GeoJSON with cleaned properties
geojson_dict = single_street.__geo_interface__
geojson_dict['features'] = [clean_properties(feature) for feature in geojson_dict['features']]

# Save results as GeoJSON with proper formatting
output_path = "single_street_with_cleaned_heights.geojson"
with open(output_path, 'w') as f:
    json.dump(geojson_dict, f, indent=2)

print(f"Cleaned GeoJSON saved to {output_path}")
