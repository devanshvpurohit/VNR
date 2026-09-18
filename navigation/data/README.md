# SURDAS Offline Navigation — Data Directory

This directory contains locally installed offline map packages.

## Structure

```
maps/
└── hyderabad/
    ├── graph.graphml     — OSM pedestrian routing graph (NetworkX format)
    ├── places.sqlite     — Offline geocoding database (place names, amenities)
    ├── metadata.json     — Map info: bbox, node count, edge count, creation date
    └── README.md         — Per-map description
```

## Creating a Map Package

Run once while online:

```bash
python setup_offline_maps.py --place "Hyderabad, Telangana, India"
```

Or with a bounding box:

```bash
python setup_offline_maps.py --bbox 17.45 17.25 78.55 78.35
```

After setup, internet is **not required** for navigation.

## Map Files

These directories are excluded from Git (`.gitignore`).  
Regenerate them by running `setup_offline_maps.py`.

## Supported Cities

Any city or region available in OpenStreetMap can be downloaded.  
Larger areas take longer to download and generate larger graph files.

Recommended: download only the area you operate in.
