export const AUTH_TOKEN_KEY = "auth_token";
export const AUTH_REFRESH_TOKEN_KEY = "auth_refresh_token";
export const AUTH_USER_KEY = "auth_user";

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string) {
  accessToken = token;
}

export function clearLegacyTokenStorage() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
}

export function clearAuthStorage() {
  accessToken = null;
  clearLegacyTokenStorage();
  localStorage.removeItem(AUTH_USER_KEY);
}
