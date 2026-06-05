/** Format storage for display: e.g. "6067.85 MB / 6 GB" */
export function formatStorageMbWithGb(mb: number): string {
  const mbText = `${mb.toFixed(2)} MB`;
  const gb = mb / 1024;

  if (gb < 0.01) {
    return mbText;
  }

  let gbText: string;
  if (gb >= 10) {
    gbText = `${Math.round(gb)} GB`;
  } else if (gb >= 1) {
    gbText = `${gb.toFixed(1)} GB`;
  } else {
    gbText = `${gb.toFixed(2)} GB`;
  }

  return `${mbText} / ${gbText}`;
}
