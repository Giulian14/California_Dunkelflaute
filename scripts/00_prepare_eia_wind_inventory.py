"""Extract the CA reference inventory from an existing official EIA-860 ZIP.

No automatic network request is made. See docs/wind_assessment.md for source.
"""

import argparse
from datetime import date
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile

import pandas as pd
from shapely.geometry import shape

from wind_model import select_eia_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--retrieved-on", help="Archive retrieval date, YYYY-MM-DD, if known")
    parser.add_argument("--project-dir", type=Path,
                        default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    if args.retrieved_on is not None:
        date.fromisoformat(args.retrieved_on)
    project = args.project_dir.resolve()
    output = project / "data/reference"
    output.mkdir(parents=True, exist_ok=True)
    members = ["2___Plant_Y2020.xlsx", "3_2_Wind_Y2020.xlsx"]
    with zipfile.ZipFile(args.archive) as archive:
        raw = {name: archive.read(name) for name in members}
    plants = pd.read_excel(BytesIO(raw[members[0]]), sheet_name="Plant", header=1,
                           engine="openpyxl")
    wind = pd.read_excel(BytesIO(raw[members[1]]), sheet_name="Operable", header=1,
                         engine="openpyxl")
    boundary_path = project / "data/boundaries/california_census_2026.geojson"
    boundary = shape(json.loads(boundary_path.read_text())["features"][0]["geometry"])
    generators, selected_plants, excluded, qa = select_eia_inventory(wind, plants, boundary)
    generators.to_csv(output / "eia2020_ca_wind_generators.csv", index=False)
    selected_plants.to_csv(output / "eia2020_ca_wind_plants.csv", index=False)
    excluded.to_csv(output / "eia2020_ca_wind_exclusions.csv", index=False)
    metadata = {
        "source": "U.S. Energy Information Administration, annual EIA-860 2020 inventory",
        "url": "https://www.eia.gov/electricity/data/eia860/archive/xls/eia8602020.zip",
        "retrieved_on": args.retrieved_on,
        "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        "workbook_sha256": {name: hashlib.sha256(raw[name]).hexdigest() for name in members},
        "boundary_sha256": hashlib.sha256(boundary_path.read_bytes()).hexdigest(),
        "derived_files_sha256": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in ["eia2020_ca_wind_generators.csv", "eia2020_ca_wind_plants.csv",
                         "eia2020_ca_wind_exclusions.csv"]
        },
        "selection": "CA, Onshore Wind Turbine, Operable sheet, status OP, positive MW, valid in-boundary coordinates",
        "layout_interpretation": "Fixed 2020 annual reference deployment; not the actual January 2020 fleet or historical hourly availability",
        "qa": qa,
    }
    (output / "eia2020_ca_wind_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
