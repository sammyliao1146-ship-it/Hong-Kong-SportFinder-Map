import { useEffect, useRef, useState } from 'react';
import { getBookingCatalog, type BookingCatalog, getAvailability, type BookingCollection, type BookingVenue, getDataStatus, getVenues, getProgrammeCatalog, getProgrammes, type Programme, type ProgrammeCatalog, type ProgrammePage, type Venue, type VenueCollection, type DataStatus } from './api/client';
import Icon from './components/Icon';
import VenueMap from './features/map/VenueMap';
import { governmentLink } from './features/map/venue-links';
import SearchSidebar from './features/search/SearchSidebar';
import SearchDock from './features/search/SearchDock';
import BookingDetails from './features/booking/BookingDetails';
import { filterVenues, type FacilityFilters } from './features/search/filters';
import AssistantPanel from './features/assistant/AssistantPanel';
import { LanguageProvider, useLanguage } from './language';

function normalizeVenueName(value: string | null | undefined) {
  return (value || '').normalize('NFKC').toLocaleLowerCase().replace(/[\s.,'’()\-–—_/，。·：:]/g, '');
}
function matchProgrammeVenue(programme: Programme, venues: Venue[]) {
  const chinese = normalizeVenueName(programme.venue_zh);
  const english = normalizeVenueName(programme.venue_en);
  if (!chinese && !english) return null;
  const matches = venues.map(venue => {
    const chineseMatch = Boolean(chinese && chinese === normalizeVenueName(venue.name_zh));
    const englishMatch = Boolean(english && english === normalizeVenueName(venue.name_en));
    if (!chineseMatch && !englishMatch) return null;
    const districtMatch = Boolean(programme.district_zh && venue.district && normalizeVenueName(programme.district_zh) === normalizeVenueName(venue.district));
    const sportCentre = venue.source_id === 'sports_centres' ? 0 : 1;
    return { venue, score: (districtMatch ? 0 : 3) + (chineseMatch ? 0 : 1) + (englishMatch ? 0 : 1) + sportCentre };
  }).filter((match): match is { venue: Venue; score: number } => match !== null);
  matches.sort((left, right) => left.score - right.score);
  return matches[0]?.venue ?? null;
}

function AppContent() {
  const { language, setLanguage, tx } = useLanguage();
  const [data, setData] = useState<DataStatus | null>(null);
  const [venues, setVenues] = useState<VenueCollection | null>(null);
  const [activeVenue, setActiveVenue] = useState<Venue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [panel, setPanel] = useState<'index' | 'search' | null>(null);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [filters, setFilters] = useState<FacilityFilters>({});
  const [mode, setMode] = useState<'facilities' | 'availability' | 'activities'>('facilities');
  const [activityCatalog, setActivityCatalog] = useState<ProgrammeCatalog | null>(null);
  const [activities, setActivities] = useState<ProgrammePage | null>(null);
  const [activitySport, setActivitySport] = useState('');
  const [activityDistrict, setActivityDistrict] = useState('');
  const [activityQuery, setActivityQuery] = useState('');
  const [activityPage, setActivityPage] = useState(1);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityError, setActivityError] = useState('');
  const [activityNotice, setActivityNotice] = useState('');
  const [activityRefresh, setActivityRefresh] = useState(0);
  const [bookingCatalog, setBookingCatalog] = useState<BookingCatalog | null>(null);
  const [catalogError, setCatalogError] = useState('');
  const [bookingSport, setBookingSport] = useState('badminton');
  const [booking, setBooking] = useState<BookingCollection | null>(null);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingError, setBookingError] = useState('');
  const [bookingDate, setBookingDate] = useState('');
  const [bookingEntry, setBookingEntry] = useState<BookingVenue | null>(null);
  const [refresh, setRefresh] = useState(0);
  const indexButton = useRef<HTMLButtonElement>(null);
  const activityButton = useRef<HTMLButtonElement>(null);
  const filteredVenues = filterVenues(venues?.items ?? [], filters);
  const selectedCount = Object.values(filters).filter(value => value === null || value.length > 0).length;
  const selectedName = Object.keys(filters).length ? selectedCount ? `${selectedCount} ${tx('类设施')}` : tx('未选择设施') : undefined;
  useEffect(() => {
    if (mode !== 'activities') return;
    let controller: AbortController | null = null;
    const loadCatalog = () => {
      controller?.abort();
      controller = new AbortController();
      const current = controller;
      setActivityLoading(true); setActivityError('');
      getProgrammeCatalog(current.signal).then(result => {
        if (current.signal.aborted) return;
        setActivityCatalog(result);
        if (result.status === 'error') setActivityError(result.message || '暂时无法获取公开课程数据。');
        else setActivityError('');
      }).catch(() => {
        if (!current.signal.aborted) setActivityError('无法连接公开课程服务，请稍后重试。');
      }).finally(() => { if (!current.signal.aborted) setActivityLoading(false); });
    };
    loadCatalog();
    const timer = window.setInterval(loadCatalog, 600000);
    return () => { window.clearInterval(timer); controller?.abort(); };
  }, [mode, activityRefresh]);

  useEffect(() => {
    if (mode !== 'activities' || !activityCatalog) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setActivityLoading(true); setActivityError('');
      getProgrammes({ sport: activitySport || undefined, district: activityDistrict || undefined, q: activityQuery || undefined, page: activityPage, signal: controller.signal })
        .then(result => {
          if (controller.signal.aborted) return;
          setActivities(result);
          setActivityError(result.status === 'error' ? result.message || '暂时无法获取课程列表。' : '');
        })
        .catch(() => { if (!controller.signal.aborted) setActivityError('无法读取课程列表，请重试。'); })
        .finally(() => { if (!controller.signal.aborted) setActivityLoading(false); });
    }, 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [mode, activityCatalog, activitySport, activityDistrict, activityQuery, activityPage]);

  useEffect(() => {
    if (mode !== 'availability') return;
    const controller = new AbortController();
    setBooking(null); setBookingEntry(null); setBookingLoading(true); setBookingError('');
    async function load() {
      try {
        const result = await getAvailability(bookingSport, controller.signal);
        if (controller.signal.aborted) return;
        setBooking(result);
        setBookingDate(previous => result.dates.includes(previous) ? previous : result.dates[0] || '');
        setBookingError('');
      } catch { if (!controller.signal.aborted) { setBookingError('无法连接余量服务，空位未知，请重试。'); setBooking(previous => previous ? {...previous, status: 'stale', message: '余量刷新失败，正在显示旧快照。'} : null); } }
      finally { if (!controller.signal.aborted) setBookingLoading(false); }
    }
    void load();
    const timer = window.setInterval(() => void load(), 300000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [mode, bookingSport, refresh]);
  function updateFilters(next: FacilityFilters) { setFilters(next); setActiveVenue(null); }
  function openBooking(entry: BookingVenue) { setBookingEntry(entry); }
  function programmeGovernmentLink(programme: Programme) {
    const venue = matchProgrammeVenue(programme, venues?.items ?? []);
    return venue ? governmentLink(venue) : null;
  }

  function locateProgramme(programme: Programme) {
    if (loading) {
      setActivityNotice('体育场所资料仍在加载，稍后再点击即可定位。');
      return;
    }
    const venue = matchProgrammeVenue(programme, venues?.items ?? []);
    if (!venue) {
      setActivityNotice(`暂时未能把“${programme.venue_zh || programme.venue_en || '该活动场地'}”匹配到地图场所图层；可打开康体通课程详情核对场地。`);
      return;
    }
    setActivityNotice(''); setFilters({}); setMode('facilities'); setBookingEntry(null); setActiveVenue(venue); setPanel(null);
  }


  async function loadVenues() {
    setLoading(true); setError('');
    try { setVenues(await getVenues()); } catch { setError('暂时无法连接场所服务，请稍后重试。'); }
    finally { setLoading(false); }
  }

  useEffect(() => {
    void loadVenues();
    getBookingCatalog().then(setBookingCatalog).catch(() => setCatalogError('无法获取公开余量项目清单，请刷新页面重试。'));
    getDataStatus().then(setData).catch(() => setError('暂时无法连接场所服务，请稍后重试。'));
  }, []);

  useEffect(() => {
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !assistantOpen) {
        setPanel(null);
        if (panel === 'index') (mode === 'activities' ? activityButton.current : indexButton.current)?.focus();
      }
    };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [panel, assistantOpen, mode]);

  function openPanel(next: 'index' | 'search') {
    setPanel(next);
    if (window.innerWidth < 900) setAssistantOpen(false);
  }

  function selectSource(key: string | null) {
    setMode('facilities');
    setFilters(key ? {[key]: null} : {});
    setActiveVenue(null);
    setPanel(null);
    indexButton.current?.focus();
  }

  return <main className="map-app">
    <header className="topbar">
      <div className="topbar-start">
        <button ref={indexButton} className={`index-toggle ${panel === 'index' && mode !== 'activities' ? 'is-active' : ''}`} aria-label={tx('设施索引')} title={tx('设施索引')} aria-controls="facility-index-panel" aria-expanded={panel === 'index' && mode !== 'activities'} onClick={() => { if (panel === 'index' && mode !== 'activities') setPanel(null); else { setMode('facilities'); openPanel('index'); } }}><Icon name="menu" size={23} /><span>{tx('索引')}</span></button>
        <button ref={activityButton} className={`activity-toggle ${panel === 'index' && mode === 'activities' ? 'is-active' : ''}` } aria-label={tx('体育课程与活动')} title={tx('体育课程与活动')} aria-controls="facility-index-panel" aria-pressed={panel === 'index' && mode === 'activities'} onClick={() => { if (panel === 'index' && mode === 'activities') setPanel(null); else { setMode('activities'); setActivityNotice(''); setActiveVenue(null); openPanel('index'); } }}><Icon name="calendar" size={20} /><span>{tx('活动')}</span></button>
        <span className="topbar-divider" />
        <a className="brand" href="/" aria-label={tx('动向香港首页')}><span className="brand-mark"><Icon name="pin" size={22} /></span><span>{language === 'en' ? 'HK Sportfinder' : '動向香港'}<small>HK SPORTFINDER</small></span></a>
      </div>
      <div className="topbar-status">
        {mode === 'facilities' && selectedName && <button className="selected-filter" onClick={() => updateFilters({})} aria-label={`${tx('清除')}${selectedName}`}><span>{selectedName}</span><Icon name="close" size={13} /></button>}
        <span className="data-status"><span className="status-dot" />{mode === 'availability' ? bookingLoading ? tx('正在读取预约余量…') : booking?.status === 'ready' ? `${booking.venues.length} ${tx('个预约场馆')}` : booking?.status === 'stale' ? tx('正在显示旧余量快照') : tx('预约余量未知') : mode === 'activities' ? activityLoading ? tx('正在读取体育活动…') : activityCatalog ? `${activityCatalog.total.toLocaleString()} ${tx('项课程与活动')}` : tx('公开课程数据未连接') : loading ? tx('正在同步场地…') : error ? tx('数据服务未连接') : venues?.data_status === 'ready' ? `${venues.total} ${tx('条设施记录')}` : venues?.data_status === 'partial' ? tx('部分图层未更新') : tx('场地同步失败')}</span>
        <div className="language-switch" role="group" aria-label="Language / 語言">
          <button type="button" onClick={() => setLanguage('zh-Hant')} aria-pressed={language === 'zh-Hant'}>繁體</button>
          <button type="button" onClick={() => setLanguage('en')} aria-pressed={language === 'en'}>English</button>
        </div>
      </div>
    </header>
    <section className="map-panel" aria-label={tx('香港运动地图')}><VenueMap venues={filteredVenues} activeVenue={activeVenue} booking={mode === 'availability' ? booking : null} bookingMode={mode === 'availability'} bookingDate={bookingDate} onBookingVenue={openBooking} /><div className="map-caption"><span className="status-dot" />{tx(mode === 'availability' ? '剩余预订空位地图' : '香港运动地图')}<span className="caption-divider" />{mode === 'availability' ? `${bookingDate} · ${tx('点击标记查看明细')}` : tx('拖动探索 · 滚动缩放')}</div></section>
    {(error || venues?.data_status === 'error' || venues?.data_status === 'partial') && <div className="venue-notice" role="status">{tx(error || venues?.message || '')}<button disabled={loading} onClick={() => void loadVenues()}>{tx('重新加载')}</button></div>}
    <SearchDock venues={filteredVenues} loading={loading} onVenue={venue => { setActiveVenue(venue); setPanel(null); }} hidden={panel === 'index' || mode === 'availability'} open={panel === 'search'} data={data} error={error} onOpen={() => openPanel('search')} onClose={() => setPanel(null)} onSelect={selectSource} />
    <SearchSidebar open={panel === 'index'} data={data} error={error} venues={venues?.items ?? []} filters={filters} onFilters={updateFilters} mode={mode} onMode={next => { setMode(next); setActiveVenue(null); setBookingEntry(null); }} bookingCatalog={bookingCatalog} catalogError={catalogError} bookingSport={bookingSport} onSport={setBookingSport} booking={booking} bookingLoading={bookingLoading} bookingError={bookingError} bookingDate={bookingDate} onDate={setBookingDate} onBookingVenue={openBooking} onRefresh={() => setRefresh(n => n + 1)} onClose={() => { setPanel(null); (mode === 'activities' ? activityButton.current : indexButton.current)?.focus(); }} activityCatalog={activityCatalog} activities={activities} activitySport={activitySport} onActivitySport={setActivitySport} activityDistrict={activityDistrict} onActivityDistrict={setActivityDistrict} activityQuery={activityQuery} onActivityQuery={setActivityQuery} activityPage={activityPage} onActivityPage={setActivityPage} activityLoading={activityLoading} activityError={activityError} activityNotice={activityNotice} onActivityVenue={locateProgramme} onActivityGovernmentLink={programmeGovernmentLink} onActivityRefresh={() => setActivityRefresh(n => n + 1)} />
    {mode === 'availability' && panel !== 'index' && <button className="booking-map-return" onClick={() => openPanel('index')}>{tx('剩余预订空位 · 打开筛选')}</button>}
    {mode === 'availability' && (bookingError || booking?.status === 'stale' || booking?.status === 'error') && <div className="booking-map-status" role="status">{tx(bookingError || booking?.message || '')}</div>}
    {bookingEntry && booking && <BookingDetails entry={booking.venues.find(v => v.venue.id === bookingEntry.venue.id) || bookingEntry} data={booking} onClose={() => setBookingEntry(null)} />}
    <AssistantPanel open={assistantOpen} onClose={() => setAssistantOpen(false)} onOpen={() => { setAssistantOpen(true); if (window.innerWidth < 900) setPanel(null); }} />
  </main>;
}

export default function App() {
  return <LanguageProvider><AppContent /></LanguageProvider>;
}
