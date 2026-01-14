import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt
from rasterio.plot import show
from pyproj import Transformer
from shapely.geometry import LineString

# File paths
tif_path = 'dgm1_tiff_kacheln/dgm1_32_352_5696_1_nw_2020.tif'
tif_path = 'dgm1_tiff_kacheln/dgm1_32_355_5699_1_nw_2020.tif'

geojson_path = 'Updated_OSM_Mülheim.geojson'

# Open the GeoTIFF file
with rasterio.open(tif_path) as src:
    fig, ax = plt.subplots(figsize=(10, 10))
    show(src, ax=ax, title="Terrain with River Overlay")
    
    # Load the GeoJSON file into a GeoDataFrame
    geojson = gpd.read_file(geojson_path)

    # Check CRS and transform GeoJSON geometries if necessary
    if geojson.crs.to_string() == "EPSG:4326":  # GeoJSON in WGS84 (lat/lon)
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)

        def transform_geometry(geom):
            if isinstance(geom, LineString):
                return LineString([transformer.transform(*coords) for coords in geom.coords])
            return geom  # Ignore non-LineString geometries

        geojson.loc[:, "geometry"] = geojson["geometry"].apply(transform_geometry)
    else:
        print("GeoJSON is already in the same CRS as the GeoTIFF (EPSG:25832).")

    # Plot only the LineStrings
    geojson[geojson.geometry.type == "LineString"].plot(ax=ax, color="red", linewidth=1, label="River Line")

    # Add legend and labels
    plt.legend()
    plt.xlabel("Easting")
    plt.ylabel("Northing")

plt.show()
