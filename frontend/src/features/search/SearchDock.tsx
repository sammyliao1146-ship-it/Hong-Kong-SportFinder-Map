import { useEffect, useRef, useState } from 'react';
import type { DataStatus, Venue } from '../../api/client';
import Icon from '../../components/Icon';
import { SourceIcon, sourceLabel } from './SearchSidebar';
import { useLanguage } from '../../language';

interface Props {
  venues: Venue[];
  loading: boolean;
  onVenue: (venue: Venue) => void;
  hidden: boolean;
  open: boolean;
  data: DataStatus | null;
  error: string;
  onOpen: () => void;
  onClose: () => void;
  onSelect: (key: string | null) => void;
}

export default function SearchDock({ hidden, open, data, error, onOpen, onClose, onSelect, venues, loading, onVenue }: Props) {
  const { tx, venueName, venueAddress, source } = useLanguage();
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const value = query.trim().toLowerCase();
  const matches = (data?.sources ?? []).filter(source => `${source.name_zh} ${source.key}`.toLowerCase().includes(value));

  const venueMatches = value ? venues.filter(v => `${v.name_zh} ${v.name_en ?? ''} ${v.address_zh ?? ''} ${v.address_en ?? ''} ${v.district ?? ''}`.toLowerCase().includes(value)) : [];

  useEffect(() => { if (open) inputRef.current?.focus({ preventScroll: true }); }, [open]);

  function close() {
    onClose();
    requestAnimationFrame(() => triggerRef.current?.focus());
  }

  return <div className={`search-dock ${open ? 'is-expanded' : ''}`} hidden={hidden}>
    {!open ? <button ref={triggerRef} className="search-entry" onClick={onOpen} aria-expanded={false} aria-controls="map-search-panel"><span>{tx('搜索场地、地址或设施类型')}</span><Icon name="search" size={23} /></button> :
      <section id="map-search-panel" className="map-search-panel" aria-label={tx('地图搜索')}>
        <form className="search-input-row" role="search" onSubmit={event => { event.preventDefault(); if (venueMatches.length) onVenue(venueMatches[0]); else if (matches.length === 1) onSelect(matches[0].key); }}>
          <label className="sr-only" htmlFor="venue-search">{tx('搜索场地和地址')}</label>
          <input ref={inputRef} id="venue-search" onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); close(); } }} value={query} onChange={event => setQuery(event.target.value)} placeholder={tx('输入场地名称、地址或类型…')} autoComplete="off" />
          {query && <button type="button" className="search-action" onClick={() => { setQuery(''); inputRef.current?.focus(); }} aria-label={tx('清空搜索')}><Icon name="close" size={16} /></button>}
          <button type="submit" className="search-action" aria-label={tx('搜索场地和地址')}><Icon name="search" size={22} /></button>
          <span className="search-divider" /><button type="button" className="search-action" onClick={close} aria-label={tx('关闭搜索')}><Icon name="chevron" size={20} /></button>
        </form>
        <div className="search-results">
          <div className="search-results-title">{tx(value ? '匹配的设施类型' : '按设施类型搜索')}</div>
          {error ? <p className="inline-error" role="alert">{tx(error)}</p> : !data ? <p className="muted" role="status">{tx('正在加载…')}</p> : matches.length ? <ul>{matches.map(sourceItem => <li key={sourceItem.key}><button className="search-result-item" onClick={() => onSelect(sourceItem.key)}><SourceIcon sourceKey={sourceItem.key} /><span>{source(sourceItem.key, sourceLabel(sourceItem.name_zh))}</span><Icon name="chevron" size={15} style={{ transform: 'rotate(180deg)' }} /></button></li>)}</ul> : <p className="search-no-results" role="status">{tx('没有匹配的类型，可查看下方场地结果。')}</p>}
          {loading && <p role="status" className="search-scope">{tx('正在获取政府场地数据…')}</p>}
          {value && <><div className="search-results-title">{tx('场地结果')} · {venueMatches.length} {tx('条设施记录')}</div><ul>{venueMatches.slice(0, 50).map(venue => <li key={venue.id}><button className="search-result-item venue-search-item" onClick={() => onVenue(venue)}><SourceIcon sourceKey={venue.source_id} /><span>{venueName(venue)}<small>{venueAddress(venue) || tx('官方暂无地址')}</small></span></button></li>)}</ul>{!loading && !venueMatches.length && <p className="search-scope">{tx('暂无匹配场地，试试其他名称或地区。')}</p>}</>}
          <p className="search-scope">{tx('点击场地定位地图。图层可能重叠，记录数不代表独立场所总数。最多显示前 50 条搜索结果。')}</p>
        </div>
      </section>}
  </div>;
}
