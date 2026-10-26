import type { CSSProperties, ReactNode } from 'react';

type IconName = 'menu' | 'close' | 'search' | 'chevron' | 'chevron-left' | 'clock' | 'sparkles' | 'chat' | 'wave' | 'track' | 'trail' | 'tent' | 'calendar' | 'send' | 'pin' | 'layers' | 'activity' | 'ball' | 'fitness' | 'tree' | 'info';
const paths: Record<IconName, ReactNode> = {
  menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></>,
  chevron: <path d="m14 6-6 6 6 6" />,
  'chevron-left': <path d="m14 6-6 6 6 6" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  sparkles: <><path d="m12 3 2.7 6.3L21 12l-6.3 2.7L12 21l-2.7-6.3L3 12l6.3-2.7L12 3Z" /><path d="m20 2 .6 1.4L22 4l-1.4.6L20 6l-.6-1.4L18 4l1.4-.6L20 2Z" /></>,
  chat: <><path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-7l-5 4v-4H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" /><path d="M8 10h8M8 13h5" /></>,
  calendar: <><rect x="3.5" y="5" width="17" height="15" rx="3" /><path d="M8 3v4M16 3v4M3.5 10h17" /></>,
  wave: <><path d="M3 8c3 0 3-2 6-2s3 2 6 2 3-2 6-2M3 13c3 0 3-2 6-2s3 2 6 2 3-2 6-2M3 18c3 0 3-2 6-2s3 2 6 2 3-2 6-2" /></>,
  track: <><rect x="3" y="6" width="18" height="12" rx="6" /><rect x="7" y="9.5" width="10" height="5" rx="2.5" /></>,
  trail: <><path d="m3 20 6-11 4 6 3-4 5 9H3Z" /><path d="m9 9 1.5-2.5" /></>,
  tent: <><path d="M12 4 3 20h18L12 4Z" /><path d="m12 20-3-6h6l-3 6Z" /></>,
  send: <><path d="m21 3-7 18-4-7-7-4L21 3Z" /><path d="m10 14 7-7" /></>,
  pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
  layers: <><path d="m12 3 10 6-10 6L2 9l10-6Z" /><path d="m3 14 9 5 9-5M3 18l9 5 9-5" /></>,
  activity: <><path d="M3 12h4l3-8 4 16 3-8h4" /></>,
  ball: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3v18M5.6 5.6c8 1 8 11.8 12.8 12.8M18.4 5.6c-8 1-8 11.8-12.8 12.8" /></>,
  fitness: <><path d="m7 7 10 10M3 7l4-4M17 21l4-4M3 11l8-8M13 21l8-8" /></>,
  tree: <><path d="m12 3-6 7h3l-5 7h16l-5-7h3l-6-7ZM12 17v5" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7h.01" /></>,
};

export default function Icon({ name, size = 20, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={style}>{paths[name]}</svg>;
}
