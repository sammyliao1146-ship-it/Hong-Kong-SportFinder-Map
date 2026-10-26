import type { Venue } from '../../api/client';
const districts: Record<string, number> = {'中西': 1, '東': 2, '離島': 3, '九龍城': 4, '葵青': 5, '觀塘': 6, '北': 7, '西貢': 8, '深水埗': 9, '沙田': 10, '南': 11, '大埔': 12, '荃灣': 13, '屯門': 14, '灣仔': 15, '黃大仙': 16, '油尖旺': 17, '元朗': 18};
export function navigationUrl(v: Pick<Venue, 'name_en' | 'name_zh' | 'address_en' | 'address_zh' | 'district' | 'website'>) {
  const target = `${v.name_en || v.name_zh} ${v.address_en || v.address_zh || ''}`;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(target)}&travelmode=transit`;
}
export function governmentLink(v: Pick<Venue, 'name_en' | 'name_zh' | 'address_en' | 'address_zh' | 'district' | 'website'>): {url: string; label: string} {
  const did = districts[(v.district || '').replace(/區$/, '')];
  if (did && /體育館/.test(v.name_zh)) {
    const name = v.name_zh.replace(/\s*[(（].*$/, '').trim();
    return {url: `https://www.lcsd.gov.hk/clpss/tc/webApp/Facility/Details.do?ftid=0&fcid=&did=${did}#${encodeURIComponent(name)}`, label: '政府官网 · 场所简介 ↗'};
  }
  if (v.website && /^https?:\/\/([^/]+\.)?lcsd\.gov\.hk\//i.test(v.website)) return {url: v.website, label: /Details.do/.test(v.website) ? '政府官网 · 场所简介 ↗' : '政府官网 · 设施资料 ↗'};
  return {url: 'https://www.lcsd.gov.hk/tc/facilities/facilitieslist.html', label: '政府官网 · 场所目录 ↗'};
}
