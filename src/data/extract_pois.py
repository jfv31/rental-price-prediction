import os
from pyrosm import OSM
import geopandas as gpd
import polars as pl

def extract_pois(pbf_path, output_dir="../data/processed/"):
    """
    Extrahiert ÖPNV und Amenities aus einem OSM-Dump und speichert sie als GeoParquet.
    """
    if not os.path.exists(pbf_path):
        print(f"Datei nicht gefunden: {pbf_path}")
        return

    print(f"Initialisiere OSM-Parser für {pbf_path}...")
    osm = OSM(pbf_path)

    # ÖPNV (Bushaltestellen, Bahnhöfe)
    transit = osm.get_data_by_custom_criteria(custom_filter={"highway": ["bus_stop"], "railway": ["station", "halt"]})
    if transit is not None:
        transit_3035 = transit.to_crs(epsg=3035)
        transit_3035.to_parquet(os.path.join(output_dir, "pois_transit.parquet"))
        print(f"{len(transit_3035)} ÖPNV-Punkte gespeichert.")

    # Amenities (Supermärkte, Parks)
    amenities_filter = {"shop": ["supermarket"], "leisure": ["park"]}
    amenities = osm.get_data_by_custom_criteria(amenities_filter)
    if amenities is not None:
        amenities_3035 = amenities.to_crs(epsg=3035)
        amenities_3035.to_parquet(os.path.join(output_dir, "pois_amenities.parquet"))
        print(f"{len(amenities_3035)} Amenities gespeichert.")

def calculate_district_centroids(shapefile_path, output_path="../data/processed/district_centroids.parquet"):
    """
    Berechnet die Zentren (Centroids) von Landkreisen aus einem Shapefile.
    """
    if not os.path.exists(shapefile_path):
        print(f"Shapefile nicht gefunden: {shapefile_path}")
        return

    print("Berechne Kreis-Zentren...")
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs(epsg=3035)

    gdf['centroid_n'] = gdf.geometry.centroid.y
    gdf['centroid_e'] = gdf.geometry.centroid.x

    # 'RS' = Regionalschlüssel (Kreis-ID)
    df_centroids = gdf[['RS', 'centroid_n', 'centroid_e']]
    df_centroids.to_parquet(output_path)
    print(f"Zentren für {len(df_centroids)} Kreise gespeichert.")

if __name__ == "__main__":
    PBF_FILE = "C:\\Users\\Admin\\Documents\\GitHub\\Rental-price-prediction\\data\\raw\\germany-latest.osm.pbf"
    # KREISE_SHP = "../data/raw/vg250_krs.shp"

    os.makedirs("../data/processed/", exist_ok=True)
    extract_pois(PBF_FILE)
    # calculate_district_centroids(KREISE_SHP)
