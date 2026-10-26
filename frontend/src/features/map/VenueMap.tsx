import { useEffect, useRef, useState } from 'react';
import { CircleMarker, MapContainer, Popup, Tooltip, ZoomControl, useMap, useMapEvents } from 'react-leaflet';

import type { CircleMarker as LeafletCircleMarker } from 'leaflet';
import type { BookingCollection, BookingVenue, Venue } from '../../api/client';
import { governmentLink, navigationUrl } from './venue-links';
import { countClass, displayCount, periodCounts } from '../booking/booking-utils';
import { maplibreGL } from '@maplibre/maplibre-gl-leaflet';
import { setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { setBasemapLanguage, simplifyBasemap } from './basemap-style';
import { useLanguage } from '../../language';
import { venueThumbnailUrl } from './venue-images';

setWorkerUrl(workerUrl);

function MinimalBasemap() {
  const map = useMap();
  const { language } = useLanguage();
  const languageRef = useRef(language);
  const vectorRef = useRef<ReturnType<ReturnType<typeof maplibreGL>['getMaplibreMap']> | null>(null);
  languageRef.current = language;

  useEffect(() => {
    const layer = maplibreGL({
      style: 'https://tiles.openfreemap.org/styles/positron',
      attributionControl: { customAttribution:
        '<a href="https://openfreemap.org/" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> · ' +
        '<a href="https://www.openmaptiles.org/" target="_blank" rel="noopener noreferrer">© OpenMapTiles</a> · ' +
        '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap</a>',
      },
    }).addTo(map);

    const vectorMap = layer.getMaplibreMap();
    vectorRef.current = vectorMap;
    vectorMap.on('style.load', () => simplifyBasemap(vectorMap, languageRef.current));

    return () => { vectorRef.current = null; map.removeLayer(layer); };
  }, [map]);

  useEffect(() => {
    const vectorMap = vectorRef.current;
    if (vectorMap?.isStyleLoaded()) setBasemapLanguage(vectorMap, language);
  }, [language]);

  return null;
}

function LocateButton() {
  const map = useMap();
  const { tx } = useLanguage();
  const [position, setPosition] = useState<[number, number] | null>(null);
  const [notice, setNotice] = useState('');
  const [locating, setLocating] = useState(false);

  function locate() {
    if (!navigator.geolocation) { setNotice(tx('浏览器不支持定位，请拖动地图选择地区。')); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      const point: [number, number] = [coords.latitude, coords.longitude];
      setPosition(point);
      map.flyTo(point, 15);
      setNotice(tx('已定位到你，位置仅保存在当前页面。'));
      setLocating(false);
    }, () => {
      setNotice(tx('未能获取位置，你仍可拖动地图选择地区。'));
      setLocating(false);
    }, { enableHighAccuracy: false, timeout: 10000 });
  }
  return <>
    <div className="location-control"><button disabled={locating} onClick={locate}><svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="12" cy="12" r="6.5"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3.5M12 18.5V22M2 12h3.5M18.5 12H22"/></svg>{locating ? tx('正在定位…') : tx('定位到我')}</button>{notice && <p role="status">{notice}</p>}</div>
    {position && <CircleMarker center={position} radius={7}><Popup>{tx('你的位置')}</Popup></CircleMarker>}
  </>;
}

const colors: Record<string, string> = {sports_centres: '#245bbc', ball_venues: '#d64b41', swimming_pools: '#1f8fd0', sports_grounds: '#b5552b', parks_rec: '#21854b', outdoor_fitness: '#df7b1c', trails: '#5b6b2f', camping: '#c4572f'};
const sourceNames: Record<string, string> = {sports_centres: '体育馆', ball_venues: '球类场所', swimming_pools: '游泳池', sports_grounds: '运动场与跑道', parks_rec: '公园与康乐场地', outdoor_fitness: '户外健身', trails: '远足径与单车径', camping: '露营与烧烤'};

function VenueMarker({ venue, active, related }: { venue: Venue; active: boolean; related: Venue[] }) {
  const { language, tx, venueName, venueAddress, district, source } = useLanguage();
  const ref = useRef<LeafletCircleMarker>(null);
  const map = useMap();
  useEffect(() => {
    if (active) { map.setView([venue.latitude, venue.longitude], 16); ref.current?.openPopup(); }
  }, [active, map, venue]);
  return <CircleMarker ref={ref} center={[venue.latitude, venue.longitude]} radius={active ? 11 : 6} pathOptions={{ color: '#fff', weight: 2, fillColor: colors[venue.source_id] || '#245bbc', fillOpacity: .95 }}>
    <Popup><div className="venue-popup">{related.map(v => <section key={v.id}>
      <h3>{venueName(v)}</h3>{v.name_en && v.name_en !== venueName(v) && <small>{v.name_en}</small>}
      {v.photos.length > 0 ? <><div className="venue-gallery">{v.photos.slice(0, 2).map((photo, index) => <a key={photo} href={photo} target="_blank" rel="noreferrer" aria-label={`${venueName(v)} ${tx('官方照片')} ${index + 1}`}><img src={venueThumbnailUrl(photo)} alt={`${venueName(v)} · ${tx('康文署官方照片')} ${index + 1}`} loading="lazy" /></a>)}</div><small className="venue-photo-credit">{tx('图片来源：')}<a href={v.photos[0]} target="_blank" rel="noreferrer">{tx('康文署公开资料 ↗')}</a></small></> : <small className="venue-photo-empty">{tx('康文署暂未提供场所照片')}</small>}
      <p>{district(v.district)} · {source(v.source_id, sourceNames[v.source_id] || v.source_id)}</p>
      <p><strong>{tx('地址：')}</strong>{venueAddress(v) || tx('官方暂无地址')} <a className="navigation-link" href={navigationUrl(v)} target="_blank" rel="noreferrer">{tx('导航 ↗')}</a></p>
      {language === 'zh-Hant' && v.address_zh && v.address_en && <small>{v.address_en}</small>}
      {v.sports.length > 0 && <p>{v.sports.map(label => tx(label)).join(' · ')}</p>}
      {v.opening_hours && <p>{tx('开放时间：')}{v.opening_hours}</p>}
      {v.telephone && <p>{tx('电话：')}{v.telephone}</p>}
      {v.court_count !== null && <p>{tx('篮球场数量：')}{v.court_count}</p>}
      <p>{tx('预约余量：未知')}</p>
      <p className="government-link">{tx('链接：')}<a href={governmentLink(v).url} target="_blank" rel="noreferrer">{tx(governmentLink(v).label)}</a></p>
    </section>)}<small>{tx('来源：康文署 / CSDI · 标记为场所代表点，不一定是入口。图层记录可能重叠。')}</small></div></Popup>
  </CircleMarker>;
}

function BookingMarkers({ booking, bookingDate, onBookingVenue }: { booking: BookingCollection; bookingDate: string; onBookingVenue: (entry: BookingVenue) => void }) {
  const map = useMap();
  const { tx, venueName } = useLanguage();
  const [zoom, setZoom] = useState(() => map.getZoom());
  useMapEvents({ zoomend: () => setZoom(map.getZoom()) });
  const expanded = zoom >= 14;
  return <>{booking.venues.map(entry => {
    if (entry.venue.latitude === null || entry.venue.longitude === null) return null;
    const counts = periodCounts(entry.slots, bookingDate);
    const total = counts.some(n => n === null) ? null : counts.reduce<number>((n, v) => n + v!, 0);
    return <CircleMarker key={entry.venue.id} center={[entry.venue.latitude, entry.venue.longitude]} radius={expanded ? 6 : 9} pathOptions={{ color: '#fff', weight: 2, fillOpacity: .95, fillColor: total === null ? '#7b879c' : total > 0 ? '#13a361' : '#9aa6b5' }} eventHandlers={{ click: () => onBookingVenue(entry) }}>
      <Tooltip key={expanded ? 'expanded' : 'hover'} permanent={expanded} interactive direction="top" offset={[0, -8]} opacity={1} className="booking-map-tooltip booking-availability-bubble">
        <button type="button" className="booking-bubble-button" onClick={event => { event.stopPropagation(); onBookingVenue(entry); }} onMouseDown={event => event.stopPropagation()} onDoubleClick={event => event.stopPropagation()} aria-label={`${venueName(entry.venue)}，${tx('查看时段明细 ›')}`}>
          <strong>{venueName(entry.venue)}</strong>
          <div>{counts.map((n, i) => <span key={i} className={countClass(n)}>{tx(['上午', '下午', '晚上'][i])} {displayCount(n)}</span>)}</div>
          <small>{tx('可订场次 · 点击查看时段明细 ›')}</small>
        </button>
      </Tooltip>
    </CircleMarker>;
  })}</>;
}

export default function VenueMap({ venues, activeVenue, booking, bookingMode, bookingDate, onBookingVenue }: { venues: Venue[]; activeVenue: Venue | null; booking: BookingCollection | null; bookingMode: boolean; bookingDate: string; onBookingVenue: (entry: BookingVenue) => void }) {
  const groups = new Map<string, Venue[]>();
  for (const venue of venues) {
    const key = `${venue.latitude.toFixed(5)},${venue.longitude.toFixed(5)}`;
    groups.set(key, [...(groups.get(key) ?? []), venue]);
  }
  return <MapContainer center={[22.3193, 114.1694]} zoom={11} zoomControl={false} scrollWheelZoom className="venue-map">
    <MinimalBasemap />
    <ZoomControl position="topright" />
    <LocateButton />
    {!bookingMode && [...groups.entries()].map(([key, related]) => <VenueMarker key={key} venue={related.find(v => v.id === activeVenue?.id) || related[0]} related={related} active={related.some(v => v.id === activeVenue?.id)} />)}
    {bookingMode && booking && <BookingMarkers booking={booking} bookingDate={bookingDate} onBookingVenue={onBookingVenue} />}

  </MapContainer>;
}
