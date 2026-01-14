import geopandas as gpd
import rasterio
import numpy as np
from rasterio.warp import transform
from geopy.distance import geodesic

# Load GeoJSON
geojson_path = 'Updated_OSM_Mülheim.geojson'
gdf = gpd.read_file(geojson_path)
print(f"Loaded {len(gdf)} geometries from GeoJSON.")

# Filter for LineStrings only
line_gdf = gdf[gdf.geometry.type == 'LineString']
print(f"Filtered {len(line_gdf)} LineString geometries.")

# Load the TIFF using rasterio
tif_path = 'dgm1_tiff_kacheln/dgm1_32_347_5693_1_nw_2020.tif'
tif_data = rasterio.open(tif_path)
print(f"Loaded TIFF file: {tif_path}")

def get_elevation(lat, lon, tif_data):
    # Transform WGS84 (EPSG:4326) to the raster's coordinate system
    src_crs = 'EPSG:4326'  # GeoJSON is in WGS84
    dst_crs = tif_data.crs  # Destination CRS of the TIFF
    x, y = transform(src_crs, dst_crs, [lon], [lat])
    
    # Transform to raster row and column
    row, col = rasterio.transform.rowcol(tif_data.transform, x[0], y[0])
    
    # Ensure indices are within bounds
    if 0 <= row < tif_data.height and 0 <= col < tif_data.width:
        elevation = tif_data.read(1)[row, col]
        print(f"Elevation at ({lat}, {lon}): {elevation} meters")
        return elevation
    else:
        raise ValueError(f"Coordinates ({lat}, {lon}) are out of raster bounds.")

def calculate_slope(edge_coords, tif_data):
    slopes = []
    for i in range(len(edge_coords) - 1):
        # Points A and B
        lat1, lon1 = edge_coords[i]
        lat2, lon2 = edge_coords[i + 1]

        print(f"Calculating slope between points ({lat1}, {lon1}) and ({lat2}, {lon2})")

        # Get elevations
        try:
            elevation1 = get_elevation(lat1, lon1, tif_data)
            elevation2 = get_elevation(lat2, lon2, tif_data)
        except ValueError as e:
            print(e)
            continue

        # Calculate distance in meters
        distance = geodesic((lat1, lon1), (lat2, lon2)).meters
        print(f"Distance between points: {distance:.2f} meters")

        # Calculate slope
        slope = (elevation2 - elevation1) / distance
        print(f"Slope: {slope:.5f}")
        slopes.append(slope)

    return slopes

# Process each LineString
for idx, geometry in line_gdf.iterrows():
    print(f"\nProcessing LineString {idx}")
    line_coords = list(geometry.geometry.coords)  # Extract coordinates
    print(f"Coordinates: {line_coords}")

    # Calculate slopes for this LineString
    slopes = calculate_slope(line_coords, tif_data)
    print(f"Slopes for LineString {idx}: {slopes}")
