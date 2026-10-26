import { Fragment, useState } from 'react';
import type { BookingCatalog, BookingCollection, BookingVenue, DataStatus, Programme, ProgrammeCatalog, ProgrammePage, Venue } from '../../api/client';
import Icon from '../../components/Icon';
import { ballOnlyCategories, flatCategories, ballSportKeys, sportOptions, venueHasSport, type FacilityFilters } from './filters';
import { countClass, displayCount, periodCounts } from '../booking/booking-utils';
import ActivityIndex from './ActivityIndex';
import { useLanguage } from '../../language';

interface Props {
  open: boolean; data: DataStatus | null; error: string; venues: Venue[];
  mode: 'facilities' | 'availability' | 'activities'; onMode: (mode: 'facilities' | 'availability' | 'activities') => void;
  filters: FacilityFilters; onFilters: (filters: FacilityFilters) => void;
  bookingCatalog: BookingCatalog | null; catalogError: string;
  bookingSport: string; onSport: (sport: string) => void;
  booking: BookingCollection | null; bookingLoading: boolean; bookingError: string;
  bookingDate: string; onDate: (date: string) => void;
  onBookingVenue: (venue: BookingVenue) => void; onRefresh: () => void; onClose: () => void;
  activityCatalog: ProgrammeCatalog | null; activities: ProgrammePage | null; activitySport: string;
  onActivitySport: (sport: string) => void; activityDistrict: string; onActivityDistrict: (district: string) => void;
  activityQuery: string; onActivityQuery: (query: string) => void; activityPage: number; onActivityPage: (page: number) => void;
  activityLoading: boolean; activityError: string; activityNotice: string; onActivityVenue: (item: Programme) => void;
  onActivityGovernmentLink: (item: Programme) => {url: string; label: string} | null; onActivityRefresh: () => void;
}
const groupNames: Record<string, string> = {sports: '运动场馆', leisure: '公园与健身', outdoor: '郊野户外'};
export function SourceIcon({ sourceKey }: { sourceKey: string }) {
  const name = sourceKey === 'swimming_pools' ? 'wave' : sourceKey === 'sports_grounds' ? 'track' : sourceKey === 'trails' ? 'trail' : sourceKey === 'camping' ? 'tent' : sourceKey === 'ball_venues' || sourceKey === 'sports_centres' ? 'ball' : sourceKey === 'outdoor_fitness' ? 'fitness' : sourceKey === 'parks_rec' ? 'tree' : 'activity';
  return <Icon name={name} size={25} />;
}
export function sourceLabel(name: string) { return name; }
export default function SearchSidebar(p: Props) {
  const { tx, venueName, district, source, sport, dateLocale } = useLanguage();
  const [query, setQuery] = useState('');
  const effectiveFilters: FacilityFilters = Object.keys(p.filters).length
    ? p.filters : Object.fromEntries((p.data?.sources ?? []).map(source => [source.key, null]));
  function toggleSource(key: string) {
    p.onFilters({...effectiveFilters, [key]: effectiveFilters[key] === null ? [] : null});
  }
  const allSelected = !!p.data?.sources.length && p.data.sources.every(s => effectiveFilters[s.key] === null);
  function toggleAll() {
    p.onFilters(allSelected ? Object.fromEntries((p.data?.sources ?? []).map(s => [s.key, []])) : {});
  }
  function toggleChild(key: string, sport: string, children: string[]) {
    const current = effectiveFilters[key] === null ? children : effectiveFilters[key] || [];
    const next = current.includes(sport) ? current.filter(k => k !== sport) : [...current, sport];
    p.onFilters({...effectiveFilters, [key]: next.length === children.length ? null : next});
  }
  const bookingVenues = (p.booking?.venues ?? []).filter(v => `${v.venue.name_zh} ${v.venue.name_en} ${v.venue.district}`.toLowerCase().includes(query.toLowerCase()));
  const activitiesMode = p.mode === 'activities';
  return <aside id="facility-index-panel" className={`facility-panel ${p.open ? 'is-open' : ''}`} aria-hidden={!p.open} inert={!p.open} aria-label={tx(activitiesMode ? '体育活动面板' : '设施索引面板')}>
    <div className="panel-heading"><div><span className="eyebrow">EXPLORE HONG KONG</span><h1>{tx(activitiesMode ? '体育课程与活动' : '地图索引')}</h1></div><button className="icon-button" onClick={p.onClose} aria-label={tx('关闭侧栏')}><Icon name="close" size={20} /></button></div>
    {!activitiesMode && <div className="index-mode-tabs" role="tablist" aria-label={tx('地图模式')}>
      <button role="tab" aria-selected={p.mode === 'facilities'} onClick={() => p.onMode('facilities')}>{tx('设施分类')}</button>
      <button role="tab" aria-selected={p.mode === 'availability'} onClick={() => p.onMode('availability')}>{tx('剩余预订空位')}</button>
    </div>}
    <div className="panel-scroll">
    {p.mode === 'facilities' ? <>
      <div className="filter-toolbar"><span>{tx('可多选 · 展开选择子设施')}</span><button onClick={toggleAll}>{tx(allSelected ? '取消全部' : '显示全部')}</button></div>
      {p.error ? <p role="alert">{tx(p.error)}</p> : !p.data ? <p role="status">{tx('正在加载分类…')}</p> : <div className="facility-rows">
        {p.data.sources.map((sourceItem, index, all) => {
          const heading = sourceItem.group !== all[index - 1]?.group ? groupNames[sourceItem.group ?? 'sports'] : null;
          const flat = flatCategories.includes(sourceItem.key);
          const total = p.venues.filter(v => v.source_id === sourceItem.key).length;
          const children = flat ? [] : sportOptions.filter(s => (!ballOnlyCategories.includes(sourceItem.key) || ballSportKeys.includes(s.key)) && p.venues.some(v => v.source_id === sourceItem.key && venueHasSport(v, s.key)));
          const checked = sourceItem.key in effectiveFilters;
          const selection = effectiveFilters[sourceItem.key];
          return <Fragment key={sourceItem.key}>{heading && <h3 className="facility-group-title">{tx(heading)}</h3>}<details className="facility-group">
            <summary onClick={flat ? e => e.preventDefault() : undefined} className={flat ? 'is-flat' : undefined}><label onClick={e => e.stopPropagation()}><input type="checkbox" checked={checked && selection === null} ref={el => { if (el) el.indeterminate = checked && Array.isArray(selection) && selection.length > 0; }} onChange={() => toggleSource(sourceItem.key)} /><SourceIcon sourceKey={sourceItem.key} /><span>{source(sourceItem.key, sourceLabel(sourceItem.name_zh))}</span></label><span className="facility-count">{total}{!flat && <span className="expand-chevron" aria-hidden="true">⌄</span>}</span></summary>
            <div className="facility-children">{children.map(sportItem => <label key={sportItem.key} className="facility-child"><input type="checkbox" checked={checked && (selection === null || selection?.includes(sportItem.key)) || false} onChange={() => toggleChild(sourceItem.key, sportItem.key, children.map(c => c.key))} /><span>{sourceItem.key === 'ball_venues' ? sport(sportItem.key, sportItem.label).replace('设施', '场').replace('設施', '場') : sport(sportItem.key, sportItem.label)}</span><em>{p.venues.filter(v => v.source_id === sourceItem.key && venueHasSport(v, sportItem.key)).length}</em></label>)}{!flat && !children.length && <p>{tx('此图层暂无细分类别资料。')}</p>}</div>
          </details></Fragment>;
        })}
      </div>}
      <p className="panel-hint">{tx('默认全选，再次点击“显示全部”可取消全部勾选，此时不显示设施。子设施按官方字段识别；未明确说明的运动不作推断。')}</p>
      <details className="source-details"><summary>{tx('数据来源与范围')}</summary><p>{tx('康文署 / 渔护署 CSDI 图层；图层可能重叠，记录数不代表全港独立场所总数。')}</p></details>
    </> : p.mode === 'availability' ? <>
      <p className="panel-hint">{tx('按运动查看官方可订场次')}</p>
      {p.catalogError ? <p role="alert" className="booking-warning">{tx(p.catalogError)}</p> : !p.bookingCatalog ? <p role="status">{tx('正在读取公开余量项目清单…')}</p> : <p className="booking-catalog-note">{tx('已接入本次核查确认的全部')} {p.bookingCatalog.items.length} {tx('类公开场地余量。核查日期：')}{p.bookingCatalog.checked_on}{tx('。康体通其他可订项目未必提供公开余量。')}</p>}
      <div className="booking-sports">{(p.bookingCatalog?.items ?? []).map(s => <button key={s.key} aria-pressed={p.bookingSport === s.key} onClick={() => p.onSport(s.key)}>{sport(s.key, s.label)}</button>)}</div>
      <div className="booking-date"><label>{tx('日期')} <select value={p.bookingDate} onChange={e => p.onDate(e.target.value)} disabled={!p.booking?.dates.length}>{p.booking?.dates.map(d => <option key={d} value={d}>{d}</option>)}</select></label><button onClick={p.onRefresh} disabled={p.bookingLoading}>{tx('刷新')}</button></div>
      <input className="booking-venue-query" aria-label={tx('筛选预约场馆')} placeholder={tx('筛选场馆或地区…')} value={query} onChange={e => setQuery(e.target.value)} />
      {p.bookingLoading && <p role="status">{tx('正在获取官方余量…')}</p>}
      {(p.bookingError || p.booking?.status !== 'ready') && <p role="status" className="booking-warning">{tx(p.bookingError || p.booking?.message || '')}</p>}
      {p.booking && <><p className="booking-timestamp">{tx('抓取：')}{p.booking.fetched_at ? new Date(p.booking.fetched_at).toLocaleString(dateLocale, { timeZone: 'Asia/Hong_Kong' }) : tx('未知')} · {bookingVenues.length} {tx('个场馆')}</p><div className="booking-list-head"><span>{tx('场馆')}</span><span>{tx('上午')}</span><span>{tx('下午')}</span><span>{tx('晚上')}</span></div>
      <div className="booking-list">{bookingVenues.map(entry => <button className="booking-card" key={entry.venue.id} onClick={() => p.onBookingVenue(entry)}><span className="booking-card-name"><strong>{venueName(entry.venue)}</strong><small>{district(entry.venue.district)}{entry.venue.latitude === null ? ` · ${tx('未定位')}` : ''} · {tx('查看时段明细 ›')}</small></span>{periodCounts(entry.slots, p.bookingDate).map((n, i) => <span key={i} className={`slot-count ${countClass(n)}`}>{displayCount(n)}</span>)}</button>)}</div>
      {!p.bookingLoading && !bookingVenues.length && <p>{tx('暂无匹配场馆；未发布余量不等于已满。')}</p>}</>}
      {p.bookingCatalog?.items.find(s => s.key === p.bookingSport) && <p className="booking-catalog-note"><a href={p.bookingCatalog.items.find(s => s.key === p.bookingSport)!.dataset_url} target="_blank" rel="noreferrer">{tx('查看此项目的政府数据来源 ↗')}</a></p>}
      <p className="panel-hint">{tx('上午 <12:00 · 下午 12–18:00 · 晚上 ≥18:00。数字为所选日期的可订场次之和，不是球场总数；? 表示未知。官方快照每5分钟更新。')}</p>
    </> : <ActivityIndex catalog={p.activityCatalog} page={p.activities} sport={p.activitySport} district={p.activityDistrict} query={p.activityQuery} currentPage={p.activityPage} loading={p.activityLoading} error={p.activityError} onSport={p.onActivitySport} onDistrict={p.onActivityDistrict} onQuery={p.onActivityQuery} onPage={p.onActivityPage} onRetry={p.onActivityRefresh} onLocate={p.onActivityVenue} onGovernmentLink={p.onActivityGovernmentLink} locationNotice={p.activityNotice} />}
    </div>
    <div className="panel-footer"><Icon name="info" size={14} /><span>{tx(activitiesMode ? '课程和名额信息来自康文署公开数据；报名详情请以康体通为准。' : p.mode === 'availability' ? '余量以康体通实际预订结果为准；公开预约余量不代表现场占用。' : '选择分类后地图立即更新，可继续多选。')}</span></div>
  </aside>;
}
