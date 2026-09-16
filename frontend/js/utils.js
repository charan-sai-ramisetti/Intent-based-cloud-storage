// Get the current access token from localStorage
function getAccessToken() {
  return localStorage.getItem("access_token");
}

// Get the refresh token from localStorage
function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

// Logout — clear both tokens and redirect to login
function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "../auth/login.html";
}

// Protect dashboard — redirect to login if no token exists at all
(function protectRoute() {
  const token = getAccessToken();
  if (!token) {
    window.location.href = "../auth/login.html";
  }
})();

// Common auth headers used on every API request
function authHeaders() {
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${getAccessToken()}`
  };
}


// ============================================================
// TOKEN REFRESH INTERCEPTOR
// ============================================================
// The access token expires after 120 minutes (set in Django SIMPLE_JWT).
// When it expires, every API call returns 401 with "token not valid" or
// 400 with "Authentication credentials were not provided" if the token
// has become null. Without this interceptor, users get silent failures
// or cryptic error alerts after 2 hours of inactivity.
//
// This function wraps fetch() with automatic token refresh:
//   1. Make the request with the current access token
//   2. If 401 is returned → call /api/auth/token/refresh/ with the refresh token
//   3. If refresh succeeds → save the new access token → retry the original request
//   4. If refresh fails (refresh token also expired, 7 day lifetime) → logout
//
// All existing code calls authFetch() instead of fetch() for authenticated
// requests. The API_BASE_URL and authHeaders() references remain unchanged.
// ============================================================

async function authFetch(url, options = {}) {
  // Make the initial request with the current access token
  let response = await fetch(url, options);

  // Token is valid — return immediately
  if (response.status !== 401 && response.status !== 403) {
    return response;
  }

  // Peek at the error body to confirm it's an auth failure, not a real 403
  // (e.g. storage quota exceeded also returns 403 — don't refresh for that)
  let errorBody = {};
  try {
    errorBody = await response.clone().json();
  } catch (_) {}

  const isAuthError = (
    errorBody.detail === "Given token not valid for any token type" ||
    errorBody.detail === "Authentication credentials were not provided." ||
    errorBody.code === "token_not_valid" ||
    errorBody.code === "user_not_found"
  );

  if (!isAuthError) {
    // Real 403 (e.g. quota exceeded) — return the original response unchanged
    return response;
  }

  // Try to refresh the access token silently
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    // No refresh token at all — session is completely dead, log out
    logout();
    return response;
  }

  let refreshResponse;
  try {
    refreshResponse = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });
  } catch (_) {
    // Network error during refresh — log out rather than loop
    logout();
    return response;
  }

  if (!refreshResponse.ok) {
    // Refresh token itself has expired (7 day lifetime) — session is dead
    logout();
    return response;
  }

  const refreshData = await refreshResponse.json();

  // Save the new access token — future authHeaders() calls will use it
  localStorage.setItem("access_token", refreshData.access);

  // Also update the refresh token if the server rotated it
  if (refreshData.refresh) {
    localStorage.setItem("refresh_token", refreshData.refresh);
  }

  // Rebuild the Authorization header with the new token and retry once
  const retryOptions = {
    ...options,
    headers: {
      ...options.headers,
      "Authorization": `Bearer ${refreshData.access}`,
    },
  };

  // Return the retried response — if this also fails, surface it to the caller
  return fetch(url, retryOptions);
}