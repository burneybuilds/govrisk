import { useNavigate } from "react-router-dom";
import { Search, Bell, Menu, LogOut } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

interface TopbarProps {
  onToggleSidebar: () => void;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export default function Topbar({ onToggleSidebar }: TopbarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const today = new Date();
  const formattedDate = today.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const initials = user ? getInitials(user.fullName) : "GR";

  const handleSearch = (value: string) => {
    if (value.trim().length > 0) {
      navigate(`/projects?search=${encodeURIComponent(value)}`);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center gap-3 border-b border-gray-200 bg-white/95 px-5 sm:gap-4 sm:px-6 lg:h-[72px] lg:gap-5 lg:px-8">
      {/* Left: Emblem + branding */}
      <div className="hidden shrink-0 items-center gap-3 sm:flex">
        <img
          src="/emblem_of_india.svg"
          alt="Indian National Emblem"
          className="h-10 w-auto shrink-0"
        />
        <div className="min-w-0 border-l border-gray-200 pl-3">
          <p className="text-sm font-bold tracking-wide text-navy-900">GovRisk</p>
          <p className="text-[11px] text-gray-500">Government of India</p>
        </div>
      </div>

      {/* Mobile hamburger */}
      <button
        type="button"
        onClick={onToggleSidebar}
        className="mr-auto shrink-0 rounded-lg p-2 text-gray-500 hover:bg-gray-100 lg:hidden"
        aria-label="Toggle navigation"
      >
        <Menu size={20} />
      </button>

      {/* Center: Search bar (nudged right) */}
      <div className="flex min-w-0 flex-1 items-center justify-center">
        <div className="w-full max-w-sm shrink-0 translate-x-7 sm:max-w-md sm:translate-x-8 lg:max-w-lg">
        <div className="relative w-full">
          <Search className="pointer-events-none absolute left-4 top-1/2 z-10 h-[18px] w-[18px] -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            onChange={(e) => handleSearch(e.target.value)}
            className="h-11 w-full rounded-lg border border-gray-200 bg-gray-50 pl-12 pr-4 text-sm text-navy-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/10"
          />
        </div>
        </div>
      </div>

      {/* Right: actions */}
      <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3">
        <span className="hidden whitespace-nowrap text-sm font-medium text-gray-500 sm:block">
          {formattedDate}
        </span>

        <button
          type="button"
          className="relative rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-navy-900"
          aria-label="Notifications"
        >
          <Bell size={18} />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white" />
        </button>

        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-navy-700 text-sm font-semibold text-white">
          {initials}
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-red-500"
          aria-label="Log out"
          title="Log out"
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}