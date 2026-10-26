import type { BookingCollection, BookingVenue } from '../../api/client';

const facilityCodes: Record<string, string> = { badminton: 'BADC', basketball: 'BASC', volleyball: 'VOLC', tennis: 'TENC', 'turf-soccer-pitch': 'FOTP' };
const districtCodes: Record<string, string> = { '中西': 'CW', '東': 'EN', '南': 'SN', '灣仔': 'WCH', '九龍城': 'KC', '觀塘': 'KT', '深水埗': 'SSP', '黃大仙': 'WTS', '油尖旺': 'YTM', '北': 'N', '西貢': 'SK', '沙田': 'ST', '大埔': 'TP', '離島': 'IS', '葵青': 'KWT', '荃灣': 'TW', '屯門': 'TM', '元朗': 'YL' };

// Open-data snapshots do not contain SmartPLAY venueId/fatId. Never substitute
// our hashed venue ID or invent an exact-session link using a time-slot index.
export function smartplaySearchLink(entry: BookingVenue, data: Pick<BookingCollection, 'sport' | 'sport_label'>, date: string): string {
  const typeCode = facilityCodes[data.sport];
  if (!typeCode) return 'https://www.smartplay.lcsd.gov.hk/facilities/home';
  const params = new URLSearchParams({
    typeCode, typeName: data.sport_label || data.sport, sportCode: 'BAGM', groupCode: 'BAGM',
    playDate: date, isFree: 'false', keywords: entry.venue.name_zh,
    district: districtCodes[(entry.venue.district || '').trim().replace(/區$/, '')] || 'all',
  });
  return `https://www.smartplay.lcsd.gov.hk/facilities/search-result?${params.toString()}`;
}
