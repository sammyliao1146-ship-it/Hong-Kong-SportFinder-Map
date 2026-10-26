"""Registry of SmartPLAY open-data booking feeds."""
import json
from pathlib import Path

SOURCE_CATALOG = json.loads((Path(__file__).resolve().parent / "booking_sources.json").read_text())
SPORTS = {source["key"]: source["label"] for source in SOURCE_CATALOG["items"]}
SOURCE_URLS = {source["key"]: source["source_url"] for source in SOURCE_CATALOG["items"]}
