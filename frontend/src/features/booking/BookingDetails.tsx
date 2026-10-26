import { useEffect, useRef, useState } from 'react';
import type { BookingCollection, BookingSlot, BookingVenue } from '../../api/client';
import { countClass, displayCount, sumSlots } from './booking-utils';
import { governmentLink, navigationUrl } from '../map/venue-links';
import { smartplaySearchLink } from './smartplay-link';
import { useLanguage } from '../../language';
import { venueThumbnailUrl } from '../map/venue-images';

export default function BookingDetails({ entry, data, onClose }: { entry: BookingVenue; data: BookingCollection; onClose: () => void }) {
  const { language, tx, venueName, venueAddress, district, sport, dateLocale } = useLanguage();
  const dialog = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState<{ date: string; start: string; end: string; slots: BookingSlot[] } | null>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  useEffect(() => { setSelected(null); }, [entry.venue.id]);
  const times = [...new Set(entry.slots.map(s => `${s.start}|${s.end}`))].sort();
  const official = governmentLink(entry.venue);
  return <dialog ref={dialog} className="booking-dialog" onCancel={e => { e.preventDefault(); onClose(); }} aria-labelledby="booking-detail-title">
    <header className="booking-detail-header"><div><span className="eyebrow">{tx('AVAILABLE SESSIONS')}</span><h2 id="booking-detail-title">{venueName(entry.venue)}</h2><p>{district(entry.venue.district)} · {sport(data.sport, data.sport_label || data.sport)}</p></div><button className="icon-button" onClick={onClose} aria-label={tx('关闭空位明细')}>✕</button></header>
    <div className="booking-detail-content">
      <p>{venueAddress(entry.venue)} <a href={navigationUrl(entry.venue)} target="_blank" rel="noreferrer">{tx('导航 ↗')}</a></p>
      {entry.venue.photos.length > 0 && <><div className="booking-venue-gallery">{entry.venue.photos.slice(0, 2).map((photo, index) => <a key={photo} href={photo} target="_blank" rel="noreferrer" aria-label={`${venueName(entry.venue)} ${tx('官方照片')} ${index + 1}`}><img src={venueThumbnailUrl(photo)} alt={`${venueName(entry.venue)} · ${tx('康文署官方照片')} ${index + 1}`} loading="lazy" /></a>)}</div><small className="venue-photo-credit">{tx('图片来源：')}<a href={entry.venue.photos[0]} target="_blank" rel="noreferrer">{tx('康文署公开资料 ↗')}</a></small></>}
      <div className="booking-detail-meta"><span>{tx('官方发布日期范围：')}{data.dates[0]}{tx(' 至 ')}{data.dates.at(-1)}</span><span>{tx('抓取时间：')}{data.fetched_at ? new Date(data.fetched_at).toLocaleString(dateLocale, {timeZone: 'Asia/Hong_Kong'}) : tx('未知')}</span></div>
      <p className={`booking-warning ${data.status === 'ready' ? 'subtle' : ''}`}>{tx(data.message)}</p>
      <h3>{tx('可用时段 · 剩余场数')}</h3>
      <p className="slot-booking-hint">{tx('点击有空位的数字，在新标签页打开康体通对应运动、地区和日期的查询页。公开文件缺少官方场馆及设施 ID，仍需在康体通选择本场馆和所点时段；可能需要先登录。')}</p>
      <div className="availability-grid-scroll"><table className="availability-grid"><caption className="sr-only">{tx('各日期实际时段的剩余场数，问号表示未提供资料')}</caption><thead><tr><th scope="col">{tx('日期 / 时间')}</th>{times.map(time => <th scope="col" key={time}>{time.split('|')[0]}<small>–{time.split('|')[1]}</small></th>)}</tr></thead><tbody>
        {data.dates.map(date => <tr key={date}><th scope="row">{date.slice(5)}<small>{new Date(`${date}T12:00:00+08:00`).toLocaleDateString(dateLocale, {weekday: 'short', timeZone: 'Asia/Hong_Kong'})}</small></th>{times.map(time => {
          const [start, end] = time.split('|');
          const slots = entry.slots.filter(s => s.date === date && s.start === start && s.end === end);
          const n = sumSlots(slots);
          const label = `${date} ${start} ${tx(' 至 ')} ${end}, ${n === null ? tx('未知') : `${tx('剩余')} ${n} ${tx('个场')}`}`;
          return <td key={time}>{n !== null && n > 0
            ? <a className={`slot-cell slot-booking-link ${countClass(n)}`} href={smartplaySearchLink(entry, data, date)} target="_blank" rel="noopener noreferrer" onClick={() => setSelected({date, start, end, slots})} aria-label={`${label}, ${tx('打开康体通查询并选择此时段')}`} title={`${venueName(entry.venue)} · ${date} ${start}–${end}; ${tx('前往康体通选择场馆及时段')}`}>{displayCount(n)}</a>
            : <button className={`slot-cell ${countClass(n)}`} onClick={() => setSelected({date, start, end, slots})} aria-label={label}>{displayCount(n)}</button>}</td>;
        })}</tr>)}
      </tbody></table></div>
      <div className="availability-legend"><span><i className="plenty" />{tx('充足 ≥3')}</span><span><i className="limited" />{tx('有限 1–2')}</span><span><i className="empty" />{tx('0 无可订空位')}</span><span><i className="unknown" />{tx('? 未发布 / 未知')}</span></div>
      {selected && <section className="slot-breakdown" aria-live="polite"><h3>{selected.date} · {selected.start}–{selected.end}</h3><p className="slot-booking-context">{venueName(entry.venue)} · {sport(data.sport, data.sport_label)}. {tx('在康体通核对此场馆和时段，实际余量以官方页面为准。')}</p>{selected.slots.length ? selected.slots.map((slot, i) => <p key={i}><span>{tx(slot.location)} · {tx(slot.facility)}</span><strong>{slot.remaining === null ? tx('未知') : `${slot.remaining} ${tx('个场')}`}</strong></p>) : <p>{tx('官方未提供此时段资料，不能判断是否已满。')}</p>}</section>}
      <p className="booking-detail-links"><a href={official.url} target="_blank" rel="noreferrer">{tx(official.label)}</a><a href={smartplaySearchLink(entry, data, selected?.date || data.dates[0])} target="_blank" rel="noopener noreferrer">{tx('前往康体通查询／预订 ↗')}</a></p>
      <small>{tx('来源：康文署 SmartPLAY 公开数据。不同场区同一时段按官方记录相加；不同运动可能共用场地，不能跨运动相加。此表不包含约战活动资料。')}</small>
    </div>
  </dialog>;
}
