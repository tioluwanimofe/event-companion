// The shapes the API sends back. Each one mirrors a class in backend/app/schemas.py.
// 🧠 If you change a schema in Python, change it here too (or TypeScript can't warn you).
// Dates arrive as ISO strings like "2027-04-16T10:42:00-05:00".

export interface MyRole {
  event_slug: string;
  role: string;
}

/** GET /api/auth/me (MeOut) */
export interface Me {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_platform_admin: boolean;
  roles: MyRole[];
}

/** GET /api/scan/{token} (ScanPreview): shown before anything is shared */
export interface ScanPreview {
  booth_name: string;
  description: string | null;
  location_label: string | null;
  event_name: string;
  signed_in: boolean;
  already_shared_at: string | null;
}

/** POST /api/scan/{token} (ScanResult) */
export interface ScanResult {
  booth_name: string;
  location_label: string | null;
  preloaded_notes: string | null;
  shared_at: string;
  first_time: boolean;
}

/** GET /api/me/booth-visits (VisitOut) */
export interface Visit {
  event_slug: string;
  booth_name: string;
  location_label: string | null;
  preloaded_notes: string | null;
  shared_at: string;
}
