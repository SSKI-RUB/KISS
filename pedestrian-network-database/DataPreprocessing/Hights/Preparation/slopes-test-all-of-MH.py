import matplotlib.pyplot as plt
import geopandas as gpd
from pyproj import Transformer
import rasterio
from rasterio.plot import show
from rasterio.merge import merge
import os

# Folder containing all TIF files
tif_folder = 'dgm1_tiff_kacheln'

# Load all TIF files from the folder
tif_files = [os.path.join(tif_folder, f) for f in os.listdir(tif_folder) if f.endswith('.tif')]

# Create a figure for all tiles
fig, ax = plt.subplots(figsize=(15, 15))

# Loop through and plot each TIF in its correct geospatial position
for tif_file in tif_files:
    with rasterio.open(tif_file) as src:
        show(src, ax=ax, transform=src.transform, title="All Tiles with River Overlay")




# Load the GeoJSON and filter LineStrings
geojson = gpd.read_file("Updated_OSM_Mülheim.geojson")
lines = geojson[geojson.geometry.type == 'LineString'] 

# Transform GeoJSON coordinates from WGS84 to UTM32N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
lines['geometry'] = lines['geometry'].apply(
    lambda geom: geom.__class__([transformer.transform(*coords) for coords in geom.coords])
)

# Plot the river lines on top of the TIFs
lines.plot(ax=ax, color='red', linewidth=2, label='River Line')

plt.legend()
plt.show()
