import { useNavigate } from "react-router-dom";
import { Search, Bell, Menu } from "lucide-react";

interface TopbarProps {
  onToggleSidebar: () => void;
}

export default function Topbar({ onToggleSidebar }: TopbarProps) {
  const navigate = useNavigate();
  const today = new Date();
  const formattedDate = today.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const handleSearch = (value: string) => {
    if (value.trim().length > 0) {
      navigate(`/projects?search=${encodeURIComponent(value)}`);
    }
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center justify-end gap-3 border-b border-gray-200 bg-white px-5 sm:gap-4 sm:px-6 lg:h-[72px] lg:gap-5 lg:px-8">
      <button
        type="button"
        onClick={onToggleSidebar}
        className="mr-auto shrink-0 rounded-lg p-2 text-gray-500 hover:bg-gray-100 lg:hidden"
        aria-label="Toggle navigation"
      >
        <Menu size={20} />
      </button>

      <div className="relative min-w-0 w-[190px] shrink sm:w-[320px] sm:shrink-0 lg:w-[340px]">
        <Search className="pointer-events-none absolute left-4 top-1/2 z-10 h-[18px] w-[18px] -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search projects..."
          onChange={(e) => handleSearch(e.target.value)}
          className="h-11 w-full rounded-lg border border-gray-200 bg-gray-50 pl-12 pr-4 text-sm text-navy-900 outline-none transition-all placeholder:text-gray-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/10"
        />
      </div>

      <span className="hidden shrink-0 whitespace-nowrap text-sm font-medium text-gray-500 sm:block">
        {formattedDate}
      </span>

      <button
        type="button"
        className="relative shrink-0 rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-navy-900"
        aria-label="Notifications"
      >
        <Bell size={18} />
        <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white" />
      </button>

      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-navy-700 text-sm font-semibold text-white">
        AS
      </div>
    </header>
  );
}