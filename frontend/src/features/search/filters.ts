import type { Venue } from '../../api/client';
export const sportOptions = [
  {key: 'badminton', label: '羽毛球设施', pattern: /羽毛球/},
  {key: 'basketball', label: '篮球设施', pattern: /籃球|篮球/},
  {key: 'volleyball', label: '排球设施', pattern: /排球/},
  {key: 'handball', label: '手球设施', pattern: /手球/},
  {key: 'tennis', label: '网球设施', pattern: /網球|网球/},
  {key: 'table-tennis', label: '乒乓球设施', pattern: /乒乓/},
  {key: 'squash', label: '壁球设施', pattern: /壁球/},
  {key: 'fitness', label: '健身设施', pattern: /健身|健體|健体/},
  {key: 'football', label: '足球设施', pattern: /足球|草地球場/},
  {key: 'running', label: '缓跑径', pattern: /緩跑|缓跑/},
  {key: 'climbing', label: '攀登设施', pattern: /攀登/},
  {key: 'cycling', label: '单车设施', pattern: /單車|单车|BMX/},
  {key: 'skating', label: '滚轴溜冰', pattern: /滾軸|滚轴/},
  {key: 'skateboard', label: '滑板场', pattern: /滑板/},
  {key: 'bowls', label: '草地滚球设施', pattern: /草地滾球|草地滚球/},
  {key: 'dance', label: '舞蹈室', pattern: /舞蹈/},
  {key: 'netball', label: '投球设施', pattern: /投球/},
  {key: 'gateball', label: '门球设施', pattern: /門球|门球/},
  {key: 'golf', label: '高尔夫球', pattern: /高爾夫|高尔夫/},
  {key: 'archery', label: '射箭场', pattern: /射箭/},
  {key: 'rugby', label: '榄球设施', pattern: /欖球|榄球/},
  {key: 'hockey', label: '曲棍球设施', pattern: /曲棍球/},
  {key: 'cricket', label: '板球设施', pattern: /板球/},
  {key: 'baseball', label: '棒球设施', pattern: /棒球/},
  {key: 'gymnastics', label: '体操训练', pattern: /體操|体操/},
  {key: 'swimming', label: '游泳池', pattern: /游泳|泳池/},
  {key: 'athletics', label: '运动场', pattern: /运动场|運動場|大球場|大球场/},
  {key: 'walking', label: '健身步行径', pattern: /步行径|步行徑/},
  {key: 'hiking', label: '远足径', pattern: /远足|遠足|郊遊徑|郊游径/},
  {key: 'camping', label: '露营地', pattern: /露营|露營/},
  {key: 'bbq', label: '烧烤场', pattern: /烧烤|燒烤/},
  {key: 'play', label: '儿童游乐', pattern: /兒童|儿童/},
];
export const ballSportKeys = ['badminton', 'basketball', 'volleyball', 'handball', 'tennis', 'table-tennis', 'squash', 'football', 'bowls', 'netball', 'gateball', 'rugby', 'hockey', 'cricket', 'baseball'];
export const ballOnlyCategories = ['sports_centres', 'ball_venues'];
export const flatCategories = ['sports_grounds', 'parks_rec', 'outdoor_fitness'];
export type FacilityFilters = Record<string, string[] | null>;
export function venueHasSport(venue: Venue, key: string) {
  if (key === 'fitness' && venue.source_id === 'outdoor_fitness') return true;
  return sportOptions.find(s => s.key === key)?.pattern.test(`${venue.sports.join(' ')} ${venue.name_zh}`) ?? false;
}
export function filterVenues(venues: Venue[], filters: FacilityFilters) {
  if (!Object.keys(filters).length) return venues;
  return venues.filter(v => v.source_id in filters && (filters[v.source_id] === null || filters[v.source_id]!.some(key => venueHasSport(v, key))));
}
