import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import LandmarkSlider from '../hero/LandmarkSlider';

export default function AppLayout() {
  return (
    <div className="relative flex min-h-screen flex-col bg-[#f5f6f9]">
      {/* Sliding landmark photo background */}
      <LandmarkSlider variant="background" />

      {/* Faint geometric background pattern */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(20,30,53,0.05) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Gold + navy accent line */}
      <div className="relative z-10 flex h-1 w-full shrink-0">
        <div className="w-24 bg-[#C9A227]" />
        <div className="flex-1 bg-navy-800" />
      </div>

      <div className="relative z-10 flex min-h-0 flex-1 flex-col">
        <Topbar />
        <main className="min-w-0 flex-1 px-5 pb-36 pt-6 sm:px-7 lg:px-8">
          <div className="mx-auto w-full max-w-[1600px]">
            <Outlet />
          </div>
        </main>
      </div>

      <Sidebar />
    </div>
  );
}
