/** Browser path including subpath base, e.g. /digifile/login */
export function appPath(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalized}`;
}

export function publicAsset(path: string): string {
  return `${import.meta.env.BASE_URL}${path.replace(/^\//, '')}`;
}

export function isAppPath(path: string): boolean {
  return window.location.pathname.startsWith(appPath(path));
}
