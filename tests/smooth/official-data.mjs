const startMarker = '/*__THORADAR_DATA_START__*/';
const endMarker = '/*__THORADAR_DATA_END__*/';

export function splitOfficialData(html) {
  const start = html.indexOf(startMarker);
  const end = html.indexOf(endMarker);
  if (start < 0 || end < start + startMarker.length ||
      start !== html.lastIndexOf(startMarker) || end !== html.lastIndexOf(endMarker)) {
    throw new Error('Expected one ordered pair of SITE_DATA markers');
  }
  return {
    before: html.slice(0, start),
    block: html.slice(start, end + endMarker.length),
    after: html.slice(end + endMarker.length)
  };
}

export function parseOfficialData(block) {
  const declaration = /^\s*const\s+SITE_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$/.exec(
    block.slice(startMarker.length, -endMarker.length)
  );
  if (!declaration) throw new Error('Expected a SITE_DATA JSON declaration between the markers');

  let data;
  try {
    data = JSON.parse(declaration[1]);
  } catch (error) {
    throw new Error('Invalid SITE_DATA JSON', { cause: error });
  }
  const date = data.briefing_date;
  if (typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date) || date.startsWith('0000') ||
      !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date) {
    throw new Error('SITE_DATA.briefing_date must be a valid YYYY-MM-DD calendar date');
  }
  if (!Array.isArray(data.papers)) throw new Error('SITE_DATA.papers must be an array');
  return data;
}
