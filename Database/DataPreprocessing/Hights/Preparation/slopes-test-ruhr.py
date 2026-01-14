
import matplotlib.pyplot as plt
import geopandas as gpd
from pyproj import Transformer
import rasterio
from rasterio.plot import show

# Open the GeoTIFF
with rasterio.open('dgm1_tiff_kacheln/dgm1_32_352_5696_1_nw_2020.tif') as src:
    fig, ax = plt.subplots(figsize=(10, 10))
    show(src, ax=ax, title="Terrain with River Overlay")

    # Load the GeoJSON (assuming the file is loaded into a GeoDataFrame)
    geojson = gpd.read_file("Updated_OSM_Mülheim.geojson")

    lines = geojson[geojson.geometry.type == 'LineString'] 
    
    # Transform GeoJSON coordinates from WGS84 to UTM32N
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
    lines['geometry'] = lines['geometry'].apply(
        lambda geom: geom.__class__([transformer.transform(*coords) for coords in geom.coords])
    )
    
    # Plot the river line in red with higher line width
    lines.plot(ax=ax, color='red', linewidth=2, label='River Line')

    plt.legend()
    plt.show()


