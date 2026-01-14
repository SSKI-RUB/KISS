import rasterio
import matplotlib
import matplotlib.pyplot as plt

# Path to a TIFF file
tif_path = 'dgm1_tiff_kacheln/dgm1_32_347_5693_1_nw_2020.tif'

# Open and visualize
with rasterio.open(tif_path) as src:
    data = src.read(1)  # Read the first band
    
    # Plotting the data
    plt.figure(figsize=(10, 8))
    plt.imshow(data, cmap='terrain', extent=src.bounds, origin='upper')
    plt.colorbar(label='Elevation (m)')
    plt.title('Digital Terrain Model - Elevation')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.show()
