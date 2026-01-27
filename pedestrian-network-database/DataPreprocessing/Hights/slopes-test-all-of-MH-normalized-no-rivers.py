import os
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from pyproj import Transformer
import rasterio
from rasterio.plot import plotting_extent
from matplotlib.colors import Normalize
from matplotlib.colors import LightSource

# Folder containing all TIF files
tif_folder = 'dgm1_tiff_kacheln'
tif_files = [os.path.join(tif_folder, f) for f in os.listdir(tif_folder) if f.endswith('.tif')]

# Collect global min and max elevation for consistent color normalization
all_elevations = []
for tif_file in tif_files:
    with rasterio.open(tif_file) as src:
        all_elevations.append(src.read(1)[src.read(1) != -9999])  # Exclude NoData values
global_min = np.min(np.concatenate(all_elevations))
global_max = np.max(np.concatenate(all_elevations))

# Set up plot
fig, ax = plt.subplots(figsize=(15, 15))

# Normalizer for consistent color scaling
norm = Normalize(vmin=global_min, vmax=global_max)
cmap = plt.cm.viridis  # Or any other color map
light = LightSource(azdeg=315, altdeg=45)

# Plot each TIF file
for tif_file in tif_files:
    with rasterio.open(tif_file) as src:
        elevation = src.read(1)
        elevation[elevation == -9999] = np.nan  # Replace NoData values for display
        shaded = light.shade(elevation, cmap=cmap, norm=norm)
        
        # Use plotting_extent to correctly align tiles
        ax.imshow(shaded, extent=plotting_extent(src), transform=ax.transData)

# Load and filter GeoJSON for streets only
#geojson = gpd.read_file("Updated_OSM_Mülheim.geojson")
geojson = gpd.read_file("OSM_MH_streets_cleaned3.geojson")
lines = geojson[
    (geojson.geometry.type == 'LineString') &  # Only LineString geometries
    (geojson['highway'].notnull()) &           # Must have a highway attribute
    (geojson['waterway'].isnull())             # Exclude features with a waterway attribute
]

# Transform GeoJSON coordinates to UTM32N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
lines['geometry'] = lines['geometry'].apply(
    lambda geom: geom.__class__([transformer.transform(*coords) for coords in geom.coords])
)

# Plot the filtered streets
lines.plot(ax=ax, color='red', linewidth=1, label='Streets')

# Add legend and title
plt.legend()
plt.title("Shaded Terrain with Streets Overlay")
plt.show()
