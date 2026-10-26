/** Render government-source Markdown links without interpreting arbitrary HTML. */
export default function AssistantAnswer({ text }: { text: string }) {
  const pattern = /\[([^\]]+)\]\((https:\/\/[^\s)]+)\)/g;
  const parts: React.ReactNode[] = [];
  let previous = 0;
  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0;
    parts.push(text.slice(previous, index));
    let safe = false;
    try {
      const url = new URL(match[2]);
      safe = url.protocol === 'https:' && (url.hostname === 'gov.hk' || url.hostname.endsWith('.gov.hk')) && !url.username && !url.password;
    } catch { /* Keep invalid URLs as plain text. */ }
    parts.push(safe ? <a key={index} href={match[2]} target="_blank" rel="noopener noreferrer">{match[1]} ↗</a> : match[0]);
    previous = index + match[0].length;
  }
  parts.push(text.slice(previous));
  return <>{parts}</>;
}
