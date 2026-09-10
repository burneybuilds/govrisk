import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  BarChart3,
  FolderOpen,
  MapPin,
  TrendingUp,
  AlertTriangle,
  Bot,
  FileText,
  Settings,
  ShieldCheck,
  LogOut,
  X,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const STORAGE_KEY = "govrisk-sidebar-collapsed";

const navItems = [
  { to: "/", icon: BarChart3, label: "Dashboard" },
  { to: "/projects", icon: FolderOpen, label: "Projects" },
  { to: "/risk-map", icon: MapPin, label: "Risk Map" },
  { to: "/analytics", icon: TrendingUp, label: "Analytics" },
  { to: "/alerts", icon: AlertTriangle, label: "Early Warnings" },
  { to: "/assistant", icon: Bot, label: "AI Assistant" },
  { to: "/reports", icon: FileText, label: "Reports" },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

function CollapsedTooltip({ label }: { label: string }) {
  return (
    <span className="pointer-events-none absolute left-full top-1/2 z-50 ml-3 hidden -translate-y-1/2 whitespace-nowrap rounded-md bg-navy-700 px-2.5 py-1.5 text-xs font-medium text-white opacity-0 shadow-lg ring-1 ring-navy-600 transition-opacity duration-150 lg:block group-hover:opacity-100">
      {label}
    </span>
  );
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

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(STORAGE_KEY) === "true";
  });
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const displayName = user?.fullName || "GovRisk User";
  const displayRole = user?.designation || user?.role ? (
    user.designation && user.role ? `${user.designation} · ${user.role[0].toUpperCase()}${user.role.slice(1)}` : (user.designation || user.role)
  ) : "Platform User";
  const initials = getInitials(displayName);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      window.localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `group relative flex h-11 w-full items-center rounded-lg px-3 text-sm font-medium transition-all duration-200 ${
      collapsed ? "lg:h-12 lg:justify-center lg:gap-0" : "lg:gap-3"
    } ${
      isActive
        ? "bg-navy-800 text-white"
        : "text-navy-300 hover:bg-navy-800/60 hover:text-white"
    }`;

  const labelClass = `whitespace-nowrap transition-all duration-200 ${
    collapsed ? "lg:max-w-0 lg:overflow-hidden lg:opacity-0" : ""
  }`;

  const iconClass = (isActive: boolean) =>
    `shrink-0 transition-colors ${
      isActive ? "text-blue-400" : "text-navy-400 group-hover:text-blue-400"
    }`;

  const sectionHeader = (label: string) => (
    <div className={collapsed ? "lg:hidden" : ""}>
      <p className="px-3 pb-2.5 pt-1 text-[11px] font-medium uppercase tracking-widest text-navy-500">
        {label}
      </p>
    </div>
  );

  const sectionDivider = (
    <div className={`mx-3 my-5 hidden h-px bg-navy-800 ${collapsed ? "lg:block" : ""}`} />
  );

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-navy-950/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col bg-navy-900 text-white shadow-2xl transition-all duration-200 ease-in-out lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 lg:shadow-none ${
          collapsed ? "lg:w-[78px]" : "lg:w-[248px]"
        } ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <button
          type="button"
          onClick={toggleCollapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="absolute -right-3 top-5 z-20 hidden h-6 w-6 items-center justify-center rounded-full border border-navy-700 bg-navy-800 text-navy-200 shadow-md transition-colors hover:border-blue-500 hover:bg-blue-600 hover:text-white lg:flex"
        >
          {collapsed ? <PanelLeftOpen size={14} /> : <PanelLeftClose size={14} />}
        </button>

        <div className="flex items-center px-5 pb-4 pt-5">
          <div
            className={`flex min-w-0 flex-1 items-center gap-3 overflow-hidden transition-all duration-200 ${
              collapsed ? "lg:w-0 lg:flex-none lg:opacity-0" : ""
            }`}
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
              GR
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-bold uppercase leading-none tracking-wide text-white">
                GovRisk
              </h1>
              <p className="mt-1.5 text-[11px] leading-snug text-navy-300">
                AI Infrastructure Intelligence
              </p>
            </div>
          </div>

          <div
            className={`mx-auto hidden h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white ${
              collapsed ? "lg:flex" : ""
            }`}
          >
            GR
          </div>

          <button
            type="button"
            onClick={onClose}
            className="ml-3 rounded-lg p-1.5 text-navy-300 hover:bg-navy-800 hover:text-white lg:hidden"
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mx-6 mb-4 border-t border-navy-800" />

        <nav className="flex-1 space-y-2.5 overflow-y-auto px-3">
          {!collapsed && sectionHeader("Platform")}
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === "/"} className={linkClass} onClick={onClose}>
              {({ isActive }) => (
                <>
                  <Icon size={20} className={iconClass(isActive)} />
                  <span className={labelClass}>{label}</span>
                  {collapsed && <CollapsedTooltip label={label} />}
                </>
              )}
            </NavLink>
          ))}

          <div className={collapsed ? "hidden" : "pt-3.5 pb-3"}>
            <div className="mx-3 border-t border-navy-800" />
          </div>

          {collapsed ? sectionDivider : sectionHeader("System")}
          {user?.role === "admin" && (
            <NavLink to="/admin" className={linkClass} onClick={onClose}>
              {({ isActive }) => (
                <>
                  <ShieldCheck size={20} className={iconClass(isActive)} />
                  <span className={labelClass}>Admin Panel</span>
                  {collapsed && <CollapsedTooltip label="Admin Panel" />}
                </>
              )}
            </NavLink>
          )}
          <NavLink to="/settings" className={linkClass} onClick={onClose}>
            {({ isActive }) => (
              <>
                <Settings size={20} className={iconClass(isActive)} />
                <span className={labelClass}>Settings</span>
                {collapsed && <CollapsedTooltip label="Settings" />}
              </>
            )}
          </NavLink>
        </nav>

        <div className="border-t border-navy-800/60 px-4 pb-[18px] pt-4">
          <div
            className={`group relative flex items-center transition-all duration-200 ${
              collapsed ? "lg:justify-center lg:gap-0" : "lg:gap-3"
            }`}
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-navy-600 text-sm font-semibold text-white ring-1 ring-navy-500">
              {initials}
            </div>
            <div className={`min-w-0 ${collapsed ? "lg:hidden" : ""}`}>
              <p className="truncate text-[15px] font-semibold text-white">{displayName}</p>
              <p className="truncate text-[13px] text-navy-300">{displayRole}</p>
            </div>
            {!collapsed && (
              <button
                type="button"
                onClick={handleLogout}
                title="Log out"
                aria-label="Log out"
                className="ml-auto shrink-0 rounded-lg p-2 text-navy-300 transition-colors hover:bg-navy-800 hover:text-red-400"
              >
                <LogOut size={16} />
              </button>
            )}
            {collapsed && <CollapsedTooltip label={displayName} />}
          </div>
        </div>
      </aside>
    </>
  );
}