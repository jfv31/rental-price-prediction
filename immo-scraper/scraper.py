import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import json
import time
import os
import re
from pathlib import Path


def extract_attributes_from_json_ld(json_ld_list):

    attributes = {}

    for item in json_ld_list:
        if isinstance(item, dict):

            if "@graph" in item:
                for graph_item in item["@graph"]:
                    result = extract_attributes_from_json_ld([graph_item])
                    if result:
                        attributes.update(result)
                continue

            # RealEstateListing oder RealEstatePosting
            item_type = item.get("@type", "")
            if "RealEstateListing" in str(item_type) or "RealEstatePosting" in str(item_type):
                # Basis-Attribute
                attributes["name"] = item.get("name")
                attributes["description"] = item.get("description")
                attributes["url"] = item.get("url")

                if "offers" in item:
                    offers = item.get("offers", {})
                    if isinstance(offers, dict):
                        attributes["kaltmiete"] = price = offers.get(
                            "price", "")

                # Adresse
                address = item.get("address", {})
                if isinstance(address, dict):
                    attributes["strasse"] = address.get("streetAddress")
                    attributes["plz"] = address.get("postalCode")
                    attributes["city"] = address.get("addressLocality")
                    attributes["country"] = address.get("addressCountry")

                if "description" in attributes and attributes["description"]:
                    desc = attributes["description"]
                    floor_match = re.search(
                        r'(\d+(?:[.,]\d+)?)\s*qm', desc, re.IGNORECASE)
                    if floor_match:
                        floor_val = floor_match.group(1).replace(",", ".")
                        try:
                            attributes["wohnflaeche"] = float(floor_val)
                        except:
                            attributes["wohnflaeche"] = floor_val

                # Anzahl Zimmer - aus name parsen
                if "name" in attributes and attributes["name"]:
                    name = attributes["name"]
                    rooms_match = re.search(
                        r'(\d+)\s*(?:-|bis)\s*zimmer', name, re.IGNORECASE)
                    if rooms_match:
                        attributes["anzahl_zimmer"] = rooms_match.group(1)
                    elif name.startswith("1-"):
                        attributes["anzahl_zimmer"] = "1"

                # Baujahr - extrahiere nur die Jahreszahl
                year_str = item.get("baujahr")
                if year_str:
                    year_match = re.search(r'\d{4}', str(year_str))
                    if year_match:
                        attributes["baujahr"] = year_match.group(0)

                # Energieeffizienz
                attributes["energy_class"] = item.get("energyEfficiencyClass")

                # Datum
                attributes["date_posted"] = item.get("datePosted")

    return attributes


def extract_from_page_source(html):
    """Extrahiert Attribute direkt aus HTML für ML-ready Format"""
    additional = {}
    soup = BeautifulSoup(html, "html.parser")

    # Numeric fields (Anzahl-Felder)
    numeric_mapping = {
        "zimmer": "num_rooms",
        "badezimmer": "num_bathrooms",
        "schlafzimmer": "num_bedrooms",
    }

    # Text fields (Informationen)
    text_mapping = {
        "heizungsart": "heating_type",
        "energieeffizienz": "energy_efficiency",
        "zustand": "condition",
        "baujahr": "baujahr",
        "nebenkosten": "nebenkosten",
        "kaution": "deposit",
        "wohnflaeche": "floor_size_m2",
    }

    # Suche nach dt/dd Paaren
    for dt in soup.find_all("dt"):
        classes = dt.get("class", [])
        class_str = " ".join(classes).lower()  # type: ignore
        dd = dt.find_next("dd")
        if not dd:
            continue

        text_value = dd.get_text(strip=True)

        # Numeric fields
        for class_key, attr_name in numeric_mapping.items():
            if class_key in class_str and attr_name not in additional:
                num_match = re.search(r'(\d+)', text_value)
                if num_match:
                    additional[attr_name] = int(num_match.group(1))
                break

        # Text fields
        for class_key, attr_name in text_mapping.items():
            if class_key in class_str and attr_name not in additional:
                if attr_name == "year_built":
                    year_match = re.search(r'\d{4}', text_value)
                    additional[attr_name] = int(
                        year_match.group(0)) if year_match else None
                elif attr_name == "floor_size_m2":
                    area_match = re.search(r'(\d+(?:[.,]\d+)?)', text_value)
                    if area_match:
                        additional[attr_name] = float(
                            area_match.group(1).replace(",", "."))
                else:
                    additional[attr_name] = text_value
                break

    # Binary features (0/1) aus Titel und Text
    full_text = soup.get_text().lower()

    binary_features = {
        "einbaukueche": ["einbauküche", "einbau"],
        "balkon": ["balkon"],
        "terasse": ["terrasse"],
        "keller": ["keller"],
        "has_parking": ["stellplatz", "garage"],
        "is_furnished": ["möbliert"],
    }

    for feature_name, keywords in binary_features.items():
        has_feature = any(kw in full_text for kw in keywords)
        additional[feature_name] = 1 if has_feature else 0

    return additional


def scrape_listing(url, output_dir=None):
    """
    Scraped eine Immobilien-Anzeige und extrahiert alle wichtigen Attribute.
    output_dir: Wenn angegeben, werden HTML und JSON-LD-Rohdaten gespeichert.
                None (Standard) = kein Schreiben auf Disk (für App-Nutzung).
    """
    listing_id = url.split("/")[-1]

    if output_dir is not None:
        Path(output_dir).mkdir(exist_ok=True)

    print(f"[LOADING] {listing_id}...")
    driver = uc.Chrome(version_main=148)
    try:
        driver.get(url)
        time.sleep(5)  # Warte länger für dynamische Inhalte
        # Scrolle um dynamische Inhalte zu laden
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        html = driver.page_source
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # Speichere rohen HTML (nur wenn output_dir gesetzt)
    if output_dir is not None:
        html_file = os.path.join(output_dir, f"{listing_id}_raw.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] HTML gespeichert")

    soup = BeautifulSoup(html, "html.parser")

    # Extrahiere JSON-LD
    json_ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
    json_ld_data = []

    for script in json_ld_scripts:
        try:
            ld_data = json.loads(str(script.string))
            json_ld_data.append(ld_data)
        except Exception:
            pass

    # Speichere JSON-LD (nur wenn output_dir gesetzt)
    if output_dir is not None and json_ld_data:
        json_file = os.path.join(output_dir, f"{listing_id}_json_ld.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_ld_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] JSON-LD (roh) gespeichert")

    # Extrahiere Attribute
    extracted = {
        "listing_id": listing_id,
        "url": url,
        "attributes": {}
    }

    # Aus JSON-LD extrahieren
    extracted["attributes"].update(
        extract_attributes_from_json_ld(json_ld_data))

    # Zusätzliche Attribute aus HTML/JavaScript
    extracted["attributes"].update(extract_from_page_source(html))

    # Entferne None-Werte
    extracted["attributes"] = {
        k: v for k, v in extracted["attributes"].items() if v is not None}

    return extracted


# Beispiel: Scrape eine URL
if __name__ == "__main__":
    url = "https://www.immobilienscout24.de/expose/167505322"
    result = scrape_listing(url)
    print("\n" + "="*50)
    print("[DONE] Scraping abgeschlossen!")
    print("\n[ATTRIBUTES] Extrahierte Attribute:")
    for key, value in result.get("attributes", {}).items():
        print(f"  {key}: {value}")
