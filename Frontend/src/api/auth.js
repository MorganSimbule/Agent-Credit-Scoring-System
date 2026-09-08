import apiClient from "./client";

// /auth/login expects OAuth2 form-encoded fields (username, password),
// not JSON — FastAPI's OAuth2PasswordRequestForm requires this format.
export async function login(username, password) {
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const { data } = await apiClient.post("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data; // { access_token, token_type, role, username }
}

export async function registerAgent({ username, password, full_name }) {
  const { data } = await apiClient.post("/auth/register", {
    username,
    password,
    full_name,
  });
  return data;
}

export async function getMe() {
  const { data } = await apiClient.get("/auth/me");
  return data;
}
