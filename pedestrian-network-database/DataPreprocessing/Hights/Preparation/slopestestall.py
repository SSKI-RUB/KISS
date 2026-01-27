import os
import rasterio
import rasterio.merge
import geopandas as gpd
import matplotlib.pyplot as plt
from rasterio.plot import show

# Load the GeoJSON (streets and rivers)
geojson = gpd.read_file("/home/mteruhrwestkiss/Daniel & Erdi/codes/Updated_OSM_Mülheim.geojson")
geojson = geojson[geojson.geometry.type == 'LineString']  # Keep only LineStrings

# Get all TIF files from the specified directory
tif_dir = "/home/mteruhrwestkiss/Daniel & Erdi/codes/dgm1_tiff_kacheln"
tif_files = [os.path.join(tif_dir, f) for f in os.listdir(tif_dir) if f.endswith('.tif')]

# Open and merge all TIF files into one
src_files_to_mosaic = [rasterio.open(tif) for tif in tif_files]
mosaic, out_trans = rasterio.merge.merge(src_files_to_mosaic)

# Close the TIF file handlers
for src in src_files_to_mosaic:
    src.close()

# Plot the merged TIF and overlay the GeoJSON
fig, ax = plt.subplots(figsize=(15, 10))
show(mosaic, transform=out_trans, ax=ax, title="Merged Terrain with GeoJSON Overlay")
geojson.plot(ax=ax, edgecolor='red', linewidth=1, label="GeoJSON Overlay")

ax.legend()
plt.tight_layout()
plt.show()
