import type {
  Catalog,
  Me as GeneratedMe,
  Notification,
  NotificationList,
  Profile as GeneratedProfile,
  SessionResponse as GeneratedSession,
  TrackResponse,
} from "./api/types.gen";

export type {
  Catalog,
  Notification,
  Olympiad,
  TrackEntry,
} from "./api/types.gen";
// The API serializes Pydantic defaults on every profile response.
export type Profile = Required<GeneratedProfile>;
export type Me = Omit<GeneratedMe, "profile"> & { profile: Profile };
type SessionResponse = Omit<GeneratedSession, "user"> & { user: Me };

declare global {
  interface Window {
    WebApp?: {
      initData?: string;
      ready?: () => void;
      openLink?: (url: string) => void;
      openMaxLink?: (url: string) => void;
    };
  }
}

const SESSION_KEY = "olympiad-route-session";
export const session = {
  get: () => sessionStorage.getItem(SESSION_KEY),
  set: (token: string) => sessionStorage.setItem(SESSION_KEY, token),
  clear: () => sessionStorage.removeItem(SESSION_KEY),
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = session.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new ApiError(
      "Не удалось связаться с сервером. Проверьте соединение и попробуйте ещё раз.",
      0,
    );
  }
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      data?.error?.message || "Не удалось выполнить действие",
      response.status,
    );
  return data as T;
}

export const api = {
  catalog: () => request<Catalog>("/catalog"),
  login: (initData?: string) =>
    request<SessionResponse>(
      initData ? "/auth/max" : "/auth/demo",
      "POST",
      initData ? { init_data: initData } : undefined,
    ),
  me: () => request<Me>("/me"),
  save: (profile: Profile) => request<Me>("/me", "PUT", profile),
  delete: () => request("/me", "DELETE"),
  track: () => request<TrackResponse>("/track"),
  add: (id: string) => request<TrackResponse>(`/track/${id}`, "PUT"),
  update: (id: string, status: string) =>
    request<TrackResponse>(`/track/${id}`, "PATCH", { status }),
  remove: (id: string) => request<TrackResponse>(`/track/${id}`, "DELETE"),
  notifications: () => request<NotificationList>("/notifications"),
  demo: (id: string, kind: "registration" | "rule_change") =>
    request<Notification>("/demo/events", "POST", { olympiad_id: id, kind }),
  action: (id: string, action: string) =>
    request(`/notifications/${id}/actions`, "POST", { action }),
};

export function openSource(url: string) {
  if (window.WebApp?.initData && window.WebApp.openLink)
    window.WebApp.openLink(url);
  else window.open(url, "_blank", "noopener,noreferrer");
}
