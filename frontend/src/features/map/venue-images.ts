export function venueThumbnailUrl(sourceUrl: string) {
  return `/api/v1/venue-photo?url=${encodeURIComponent(sourceUrl)}`;
}
