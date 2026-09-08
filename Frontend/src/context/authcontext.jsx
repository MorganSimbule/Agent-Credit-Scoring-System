import { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("hobbiton_user");
    return saved ? JSON.parse(saved) : null;
  });

  const login = (data) => {
    // data = { access_token, role, username }
    localStorage.setItem("hobbiton_token", data.access_token);
    localStorage.setItem("hobbiton_user", JSON.stringify(data));
    setUser(data);
  };

  const logout = () => {
    localStorage.removeItem("hobbiton_token");
    localStorage.removeItem("hobbiton_user");
    setUser(null);
  };

  const token = user?.access_token || null;
  const role = user?.role || null;

  return (
    <AuthContext.Provider value={{ user, token, role, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);