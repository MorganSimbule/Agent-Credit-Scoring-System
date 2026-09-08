import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import LandingPage from "./pages/LandingPage";
import RegisterPage from "./pages/RegisterPage";
import Console from "./pages/Console";
import Predict from "./pages/Predict";
import Monitoring from "./pages/Monitoring";
import Agents from "./pages/Agents";
import AgentWorkspace from "./pages/AgentWorkspace";

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Convenience redirect: /admin isn't a real page, but forwards
            to the actual admin-facing route so old links/bookmarks work. */}
        <Route path="/admin" element={<Navigate to="/console/monitoring" replace />} />

        <Route
          path="/console"
          element={
            <ProtectedRoute>
              <Console />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/console/predict" replace />} />
          <Route path="predict" element={<Predict />} />
          <Route path="workspace" element={<AgentWorkspace />} />
          <Route
            path="monitoring"
            element={
              <ProtectedRoute adminOnly>
                <Monitoring />
              </ProtectedRoute>
            }
          />
          <Route
            path="agents"
            element={
              <ProtectedRoute adminOnly>
                <Agents />
              </ProtectedRoute>
            }
          />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

export default App;
