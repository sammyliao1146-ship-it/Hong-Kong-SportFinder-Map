import type { DataDrivenPropertyValueSpecification, Map } from 'maplibre-gl';

/** Reduce basemap detail so sports venues can carry the visual emphasis. */
export function simplifyBasemap(map: Map, language: 'zh-Hant' | 'en' = 'zh-Hant') {
  const fills: Record<string, string> = {
    background: '#f4f1e8',
    water: '#a9d2e1',
    park: '#bfd5a9',
    landuse_residential: '#e6e7da',
    landcover_wood: '#cbdcb5',
    building: '#d4d8c9',
  };

  for (const layer of map.getStyle().layers) {
    const id = layer.id;
    if (fills[id]) {
      map.setPaintProperty(id, layer.type === 'background' ? 'background-color' : 'fill-color', fills[id]);
    }

    if (id === 'park' || id === 'landcover_wood') {
      map.setPaintProperty(id, 'fill-opacity', 0.9);
    }
    if (layer.type === 'line' && /highway|motorway/.test(id)) {
      const color = id.includes('casing') ? '#b4bfad'
        : id.includes('inner') ? '#fffdf7' : '#c1c9b8';
      map.setPaintProperty(id, 'line-color', color);
    }

    // Small place names and paths appear only when the user zooms in.
    let minZoom: number | undefined;
    if (id === 'label_village' || id === 'highway_minor') minZoom = 13;
    if (id === 'label_other' || id === 'highway_path' || id.startsWith('railway')) minZoom = 14;
    if (id === 'building') minZoom = 15;
    if (minZoom !== undefined) {
      map.setLayerZoomRange(id, Math.max(minZoom, layer.minzoom ?? 0), layer.maxzoom ?? 24);
    }

    if (id.startsWith('water_name') || id.includes('shield') || id === 'airport' || id === 'boundary_3') {
      map.setLayoutProperty(id, 'visibility', 'none');
    }

    if (layer.type === 'symbol' && layer.layout?.['text-field']) {
      // One local name instead of stacked English and Chinese labels.
      map.setLayoutProperty(id, 'text-field', basemapLabel(language));
      map.setPaintProperty(id, 'text-color', '#365447');
      map.setPaintProperty(id, 'text-halo-color', '#fffdf6');
      map.setPaintProperty(id, 'text-halo-width', 1.5);
      if (id.startsWith('label_')) {
        map.setLayoutProperty(id, 'text-size', id.startsWith('label_city') ? 15 : 12);
      }
    }
  }
}

function basemapLabel(language: 'zh-Hant' | 'en'): DataDrivenPropertyValueSpecification<string> {
  return language === 'en'
    ? ['coalesce', ['get', 'name:en'], ['get', 'name:latin'], ['get', 'name']] as DataDrivenPropertyValueSpecification<string>
    : ['coalesce', ['get', 'name:zh-Hant'], ['get', 'name:zh'], ['get', 'name:nonlatin'], ['get', 'name']] as DataDrivenPropertyValueSpecification<string>;
}

export function setBasemapLanguage(map: Map, language: 'zh-Hant' | 'en') {
  for (const layer of map.getStyle().layers) {
    if (layer.type === 'symbol' && layer.layout?.['text-field']) {
      map.setLayoutProperty(layer.id, 'text-field', basemapLabel(language));
    }
  }
}
