import { BarChart3, ClipboardCheck, LogOut } from "lucide-react";

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("username");
  localStorage.removeItem("role");
  window.location.assign("/");
}

export default function Sidebar({ view, setView, modelsLoaded }) {
  const username = localStorage.getItem("username");

  return (
    <aside className="w-64 shrink-0 bg-[#0f2a1c] text-white flex flex-col justify-between p-6 min-h-screen">
      <div>
        <div className="w-10 h-10 rounded-lg bg-[#1a5c3a] flex items-center justify-center font-bold text-sm mb-3">
          HS
        </div>
        <div className="font-semibold text-lg mb-1">Agent Risk Console</div>
        {username && (
          <div className="text-xs text-white/50 mb-3 truncate">Signed in as {username}</div>
        )}
        <div className="flex items-center gap-2 text-xs text-white/60">
          <span
            className={
              modelsLoaded
                ? "w-2 h-2 rounded-full bg-emerald-400"
                : "w-2 h-2 rounded-full bg-white/30"
            }
          />
          {modelsLoaded ? "Models online" : "Models unavailable"}
        </div>
      </div>

      <nav className="flex-1 mt-10 flex flex-col gap-1" aria-label="Console views">
        <button
          onClick={() => setView("score")}
          className={
            view === "score"
              ? "flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-[#1a5c3a] text-white text-sm font-medium transition"
              : "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-white/70 text-sm font-medium hover:bg-white/5 hover:text-white transition"
          }
        >
          <ClipboardCheck size={17} /> Score agent
        </button>
        <button
          onClick={() => setView("dashboard")}
          className={
            view === "dashboard"
              ? "flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-[#1a5c3a] text-white text-sm font-medium transition"
              : "flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-white/70 text-sm font-medium hover:bg-white/5 hover:text-white transition"
          }
        >
          <BarChart3 size={17} /> Dashboard
        </button>
      </nav>

      <button
        onClick={logout}
        className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-white/60 text-sm font-medium hover:bg-white/5 hover:text-white transition"
      >
        <LogOut size={17} /> Log out
      </button>
    </aside>
  );
}
