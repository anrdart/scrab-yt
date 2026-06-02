import { Link, useLocation } from "react-router-dom";

const NAV = [
  { to: "/", label: "Dashboard", icon: "D" },
  { to: "/analyses/new", label: "New Scan", icon: "+" },
];

export function Sidebar({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const location = useLocation();

  return (
    <aside
      className={`${open ? "w-60" : "w-[64px]"} h-screen border-r border-[var(--border-strong)] bg-[var(--surface-strong)] flex flex-col transition-[width] duration-200 shrink-0 text-white`}
    >
      <div className="h-16 border-b border-white/10 flex items-center px-4 gap-3">
        <div className="w-8 h-8 rounded-md bg-[var(--primary)] flex items-center justify-center text-white text-xs font-black shrink-0 shadow-[0_0_0_3px_rgba(255,255,255,0.08)]">
          Y
        </div>
        {open && (
          <div className="min-w-0">
            <span className="block text-sm font-black text-white">ytdupe</span>
            <span className="block text-[10px] font-bold uppercase tracking-wider text-white/45">duplicate lab</span>
          </div>
        )}
      </div>

      <nav className="flex-1 py-4 px-2 space-y-1">
        {NAV.map((n) => {
          const active = n.to === "/" ? location.pathname === "/" : location.pathname.startsWith(n.to);
          return (
            <Link
              key={n.to}
              to={n.to}
              className={`flex items-center gap-2.5 px-3 py-2.5 rounded-md text-[13px] font-bold transition-colors duration-150 ${
                active
                  ? "bg-white text-[var(--text)]"
                  : "text-white/58 hover:bg-white/8 hover:text-white"
              }`}
            >
              <span className={`w-5 h-5 rounded flex items-center justify-center text-xs font-black ${active ? "bg-[var(--primary)] text-white" : "bg-white/10 text-white/65"}`}>
                {n.icon}
              </span>
              {open && n.label}
            </Link>
          );
        })}
      </nav>

      <button
        onClick={onToggle}
        className="h-11 border-t border-white/10 flex items-center justify-center text-white/50 hover:text-white transition-colors cursor-pointer"
        aria-label="Toggle sidebar"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 18l-6-6-6 6" />
        </svg>
      </button>
    </aside>
  );
}
