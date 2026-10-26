import { useState } from 'react';
import type { Programme, ProgrammeCatalog, ProgrammePage } from '../../api/client';
import Icon from '../../components/Icon';
import { useLanguage } from '../../language';

interface Props {
  catalog: ProgrammeCatalog | null; page: ProgrammePage | null; sport: string; district: string;
  query: string; currentPage: number; loading: boolean; error: string;
  onSport: (value: string) => void; onDistrict: (value: string) => void;
  onQuery: (value: string) => void; onPage: (value: number) => void; onRetry: () => void;
  onLocate: (item: Programme) => void; onGovernmentLink: (item: Programme) => {url: string; label: string} | null; locationNotice: string;
}
function snapshotTime(value: string | null, locale: string) {
  if (!value) return '未知';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(locale, { timeZone: 'Asia/Hong_Kong' });
}
function dateRange(item: Programme, tx: (value: string) => string) {
  if (item.start_date && item.end_date) return `${item.start_date} – ${item.end_date}`;
  return item.start_date || item.end_date || tx('日期未注明');
}
function enrolLabel(value: string | null, tx: (value: string) => string) {
  return value === 'BALLOT' ? tx('抽签') : value === 'FCFS' ? tx('先到先得') : value === 'WALKIN' ? tx('现场报名') : value || tx('报名方式未注明');
}
function dateLine(item: Programme, language: string, tx: (value: string) => string) {
  const day = language === 'en' ? item.days_en || item.days_zh : item.days_zh;
  const time = item.start_time || item.end_time ? `${item.start_time || tx('时间未注明')}${item.end_time ? `–${item.end_time}` : ''}` : '';
  return [dateRange(item, tx), day, time].filter(Boolean).join(' · ');
}
function ProgrammeRow({ item, onSelect }: { item: Programme; onSelect: (item: Programme) => void }) {
  const { language, tx, district, sport } = useLanguage();
  const title = language === 'en' ? item.name_en || item.name_zh : tx(item.name_zh);
  const venue = [
    language === 'en' ? district(item.district_en || item.district_zh) : district(item.district_zh),
    language === 'en' ? item.venue_en || item.venue_zh : tx(item.venue_zh || ''),
  ].filter(Boolean).join(' · ') || tx('场地未注明');
  return <article className="programme-card programme-card-compact">
    <button type="button" className="programme-card-main" onClick={() => onSelect(item)} aria-label={`${tx('查看活动详情')}：${title}`}>
      <span className="programme-row-heading"><span className="programme-sport-tag">{language === 'en' ? item.sport : tx(item.sport)}</span><strong>{title}</strong><span className="programme-row-arrow" aria-hidden="true">›</span></span>
      <span className="programme-row-meta"><span className="programme-row-date"><Icon name="activity" size={13} /><span>{dateLine(item, language, tx)}</span></span><span className="programme-row-venue"><Icon name="pin" size={13} /><span>{venue}</span></span></span>
      <span className={`programme-row-spaces ${item.places_left === null ? 'is-unknown' : item.places_left > 0 ? 'is-open' : 'is-none'}`}>
        {item.places_left === null ? tx('余量未知') : `${tx('余量')} ${item.places_left}`}
      </span>
    </button>
  </article>;
}
function ProgrammeDetails({ item, onBack, onLocate, onGovernmentLink, locationNotice }: { item: Programme; onBack: () => void; onLocate: (item: Programme) => void; onGovernmentLink: (item: Programme) => {url: string; label: string} | null; locationNotice: string }) {
  const { language, tx, district } = useLanguage();
  const title = language === 'en' ? item.name_en || item.name_zh : tx(item.name_zh);
  const officialVenue = onGovernmentLink(item);
  const districtName = language === 'en' ? district(item.district_en || item.district_zh) : district(item.district_zh);
  const venueName = language === 'en' ? item.venue_en || item.venue_zh : tx(item.venue_zh || '场地未注明');
  const notes = language === 'en' ? item.notes_en?.length ? item.notes_en : item.notes_zh : item.notes_zh?.length ? item.notes_zh : item.notes_en;
  const time = item.start_time || item.end_time ? `${item.start_time || tx('时间未注明')}${item.end_time ? ` – ${item.end_time}` : ''}` : tx('时间未注明');
  const enrolRange = item.enrol_start_date || item.enrol_end_date ? `${item.enrol_start_date || '—'} – ${item.enrol_end_date || '—'}` : null;
  const openRange = item.open_enrol_start_date || item.open_enrol_end_date ? `${item.open_enrol_start_date || '—'} – ${item.open_enrol_end_date || '—'}` : null;
  const ballotRange = item.ballot_start_date || item.ballot_end_date ? `${item.ballot_start_date || '—'} – ${item.ballot_end_date || '—'}` : null;
  return <section className="programme-detail-view" aria-label={tx('活动详情')}>
    <button type="button" className="programme-back-button" onClick={onBack}><Icon name="chevron" size={15} />{tx('返回活动列表')}</button>
    <div className="programme-detail-heading"><span className="programme-sport-tag">{language === 'en' ? item.sport : tx(item.sport)}</span><code>{item.activity_no}</code></div>
    <h2>{title}</h2>
    {language === 'zh-Hant' && item.name_en && <p className="programme-detail-english">{item.name_en}</p>}
    <div className="programme-detail-card programme-availability-card">
      <span className="programme-detail-card-label">{tx('剩余名额')}</span>
      <strong>{item.places_left === null ? tx('公开资料未提供') : item.places_left}</strong>
      {item.quota !== null && <span>{tx('总名额')} {item.quota}</span>}
    </div>
    <div className="programme-detail-section">
      <h3>{tx('日期与时间')}</h3>
      <p><Icon name="activity" size={15} /><span>{dateRange(item, tx)}{(language === 'en' ? item.days_en || item.days_zh : item.days_zh) ? ` · ${language === 'en' ? item.days_en || item.days_zh : tx(item.days_zh || '')}` : ''}</span></p>
      <p><Icon name="activity" size={15} /><span>{time}</span></p>
    </div>
    <div className="programme-detail-section">
      <h3>{tx('活动地点')}</h3>
      <p><Icon name="pin" size={15} /><span>{venueName}{districtName ? ` · ${districtName}` : ''}</span></p>
      {locationNotice && <p className="activity-warning" role="status">{tx(locationNotice)}</p>}
      {(item.venue_zh || item.venue_en) && <div className="programme-location-actions">
        {officialVenue && <a className="programme-government-link" href={officialVenue.url} target="_blank" rel="noreferrer">{tx(officialVenue.label)}</a>}
        <button type="button" className="programme-map-button" onClick={() => onLocate(item)}><Icon name="pin" size={15} />{tx('在地图中查看场所')}</button>
      </div>}
    </div>
    <div className="programme-detail-section">
      <h3>{tx('活动简介 / 备注')}</h3>
      {notes?.length ? <ul className="programme-notes">{notes.map((note, index) => <li key={`${index}-${note}`}>{note}</li>)}</ul> : <p className="programme-muted">{tx('公开资料未提供课程简介，请查看康体通课程详情。')}</p>}
    </div>
    <div className="programme-detail-section programme-detail-facts">
      <h3>{tx('报名与对象')}</h3>
      <p><span>{tx('报名方式')}</span><strong>{enrolLabel(item.enrol_method, tx)}</strong></p>
      {enrolRange && <p><span>{tx('报名日期')}</span><strong>{enrolRange}</strong></p>}
      {openRange && <p><span>{tx('公开报名日期')}</span><strong>{openRange}</strong></p>}
      {ballotRange && <p><span>{tx('抽签日期')}</span><strong>{ballotRange}</strong></p>}
      <p><span>{tx('参加对象')}</span><strong>{language === 'en' ? item.target_en || item.target_zh || tx('未注明') : tx(item.target_zh || '未注明')}</strong></p>
      <p><span>{tx('费用')}</span><strong>{item.fee === null ? tx('未注明') : item.fee === 0 ? tx('免费') : `HK$${item.fee}`}</strong></p>
    </div>
    {item.url && <a className="programme-official-link" href={item.url} target="_blank" rel="noreferrer">{tx('打开康体通活动详情 ↗')}</a>}
  </section>;
}

export default function ActivityIndex(p: Props) {
  const { tx, district, sport, dateLocale } = useLanguage();
  const [selected, setSelected] = useState<Programme | null>(null);
  const totalPages = Math.max(1, Math.ceil((p.page?.total ?? 0) / (p.page?.page_size ?? 30)));
  if (selected) return <ProgrammeDetails item={selected} onBack={() => setSelected(null)} onLocate={p.onLocate} onGovernmentLink={p.onGovernmentLink} locationNotice={p.locationNotice} />;
  return <section className="activity-index" aria-label={tx('体育课程和活动')}>
    <p className="panel-hint">{tx('按官方活动类别浏览康文署社区体育课程和活动')}</p>
    {p.error && <div className="activity-error" role="alert">{tx(p.error)}<button onClick={p.onRetry}>{tx('重试')}</button></div>}
    {p.locationNotice && <p className="activity-warning" role="status">{tx(p.locationNotice)}</p>}
    {!p.catalog && !p.error && <p className="activity-loading" role="status">{tx('正在读取官方课程清单…')}</p>}
    {p.catalog && <>
      <div className="activity-source-note"><span>{p.catalog.total.toLocaleString()} {tx('项进行中或未开始的活动')}</span><a href={p.catalog.dataset_url} target="_blank" rel="noreferrer">{tx('政府数据集 ↗')}</a></div>
      <label className="activity-filter-label">{tx('运动 / 活动类别')}
        <select value={p.sport} onChange={event => { p.onSport(event.target.value); p.onPage(1); }}>
          <option value="">{tx('全部运动')}</option>
          {p.catalog.sports.map(item => <option key={item.key} value={item.key}>{sport(item.key, item.label)} ({item.count})</option>)}
        </select>
      </label>
      <div className="activity-filter-row">
        <input aria-label={tx('搜索课程、场地或地区')} placeholder={tx('搜索课程、场地或地区…')} value={p.query} onChange={event => { p.onQuery(event.target.value); p.onPage(1); }} />
        <select aria-label={tx('按地区或组别筛选')} value={p.district} onChange={event => { p.onDistrict(event.target.value); p.onPage(1); }}>
          <option value="">{tx('全部地区 / 组别')}</option>
          {p.catalog.districts.map(value => <option key={value} value={value}>{district(value)}</option>)}
        </select>
      </div>
      {p.catalog.status === 'stale' && <p className="activity-warning" role="status">{tx(p.catalog.message)}</p>}
      <p className="activity-updated">{tx('抓取时间：')}{tx(snapshotTime(p.catalog.fetched_at, dateLocale))}{tx(' · 官方约每 10 分钟更新')}</p>
      {p.loading && <p className="activity-loading" role="status">{tx('正在筛选活动…')}</p>}
      {p.page && <>
        <p className="activity-result-count">{p.page.total.toLocaleString()} {tx('项符合条件')}</p>
        <div className="programme-list">{p.page.items.map(item => <ProgrammeRow key={item.activity_no} item={item} onSelect={setSelected} />)}</div>
        {!p.loading && !p.page.items.length && <p className="activity-empty">{tx('没有符合条件的课程或活动。')}</p>}
        {p.page.total > 0 && <div className="activity-pagination"><button disabled={p.currentPage <= 1 || p.loading} onClick={() => p.onPage(p.currentPage - 1)}>{tx('上一页')}</button><span>{p.currentPage} / {totalPages}</span><button disabled={p.currentPage >= totalPages || p.loading} onClick={() => p.onPage(p.currentPage + 1)}>{tx('下一页')}</button></div>}
      </>}
      <details className="source-details activity-source-details"><summary>{tx('数据范围与说明')}</summary><p>{tx('资料来自康文署 SmartPLAY 社区康乐体育活动公开数据。这里显示课程的公开名额和报名方式；实际资格、报名时段及余量以康体通活动详情页为准。已结束的活动会自动隐藏。')}</p><a href={p.catalog.source_url} target="_blank" rel="noreferrer">{tx('打开公开数据文件 ↗')}</a></details>
    </>}
  </section>;
}
