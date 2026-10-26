export interface Source {
  key: string;
  name_zh: string;
  group?: string;
  research_record_count: number;
  research_checked_on: string;
}
export interface DataStatus {
  facility_sync: string;
  booking_sync: string;
  unique_venue_total: number | null;
  sources: Source[];
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : '请求失败，请稍后重试。');
  }
  return response.json() as Promise<T>;
}

export const getDataStatus = () => request<DataStatus>('/sources');
export interface ChatMessage { role: 'user' | 'assistant'; content: string; }
export const chat = (message: string, history: ChatMessage[] = []) => request<{ answer: string; model: string }>(
  '/assistant/chat',
  { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, history }) },
);

export interface Venue {
  id: string; source_id: string; name_zh: string; name_en: string | null;
  address_zh: string | null; address_en: string | null; district: string | null;
  latitude: number; longitude: number; sports: string[]; photos: string[]; court_count: number | null;
  opening_hours: string | null; telephone: string | null; website: string | null;
}
export interface VenueCollection {
  data_status: 'not_synced' | 'ready' | 'partial' | 'error';
  items: Venue[]; total: number | null; updated_at: string | null;
  source_errors: string[]; skipped_records: number; message: string;
}
export const getVenues = () => request<VenueCollection>('/venues');

export interface BookingSlot { date: string; start: string; end: string; remaining: number | null; location: string; facility: string; }
export interface BookingVenue { venue: Omit<Venue, 'latitude' | 'longitude'> & { latitude: number | null; longitude: number | null }; slots: BookingSlot[]; }
export interface BookingCollection {
  sport: string; sport_label: string; status: 'ready' | 'stale' | 'error'; fetched_at: string | null;
  source_updated_at: string | null; source_url: string; dates: string[]; venues: BookingVenue[]; message: string;
}
export const getAvailability = (sport: string, signal?: AbortSignal) => request<BookingCollection>(`/availability?sport=${encodeURIComponent(sport)}`, { signal });

export interface BookingSport { key: string; label: string; source_url: string; dataset_url: string; update_interval_seconds: number; }
export interface BookingCatalog { checked_on: string; lcsd_dataset_count: number; items: BookingSport[]; }
export const getBookingCatalog = () => request<BookingCatalog>('/availability/sports');

export interface ProgrammeSport { key: string; label: string; count: number; }
export interface ProgrammeCatalog {
  status: 'ready' | 'stale' | 'error' | 'not_synced'; fetched_at: string | null; source_updated_at: string | null;
  total: number; sports: ProgrammeSport[]; districts: string[]; source_url: string; dataset_url: string;
  update_interval_seconds: number; message: string;
}
export interface Programme {
  activity_no: string; name_zh: string; name_en: string | null; sport: string;
  district_zh: string | null; district_en: string | null; start_date: string | null; end_date: string | null;
  days_zh: string | null; days_en: string | null; start_time: string | null; end_time: string | null;
  venue_zh: string | null; venue_en: string | null; target_zh: string | null; target_en: string | null;
  fee: number | null; quota: number | null; places_left: number | null; enrol_method: string | null;
  enrol_start_date: string | null; enrol_end_date: string | null; open_enrol_start_date: string | null;
  open_enrol_end_date: string | null; ballot_start_date: string | null; ballot_end_date: string | null; url: string | null;
  notes_zh: string[]; notes_en: string[];
}
export interface ProgrammePage {
  status: 'ready' | 'stale' | 'error' | 'not_synced'; fetched_at: string | null; source_updated_at: string | null;
  sport: string | null; district: string | null; total: number; page: number; page_size: number;
  items: Programme[]; source_url: string; dataset_url: string; message: string;
}
export const getProgrammeCatalog = (signal?: AbortSignal) => request<ProgrammeCatalog>('/programmes/catalog', { signal });
export function getProgrammes(options: { sport?: string; district?: string; q?: string; page?: number; signal?: AbortSignal }) {
  const params = new URLSearchParams();
  if (options.sport) params.set('sport', options.sport);
  if (options.district) params.set('district', options.district);
  if (options.q) params.set('q', options.q);
  if (options.page) params.set('page', String(options.page));
  return request<ProgrammePage>(`/programmes${params.size ? `?${params.toString()}` : ''}`, { signal: options.signal });
}
