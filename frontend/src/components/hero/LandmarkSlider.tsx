import { useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Slide {
  src: string;
  title: string;
}

interface LandmarkSliderProps {
  variant?: 'card' | 'background';
}

const slides: Slide[] = [
  { src: '/assets/india-gate-photo.jpg', title: 'India Gate' },
  { src: '/assets/slides/gateway-of-india.jpg', title: 'Gateway of India' },
  { src: '/assets/slides/taj-mahal.jpg', title: 'Taj Mahal' },
  { src: '/assets/slides/jagannath-temple.jpg', title: 'Jagannath Temple' },
  { src: '/assets/slides/charminar.jpg', title: 'Charminar' },
  { src: '/assets/slides/golden-temple.jpg', title: 'Golden Temple' },
  { src: '/assets/slides/qutub-minar.jpg', title: 'Qutub Minar' },
];

const SLIDE_INTERVAL_MS = 5000;

function clampIndex(i: number) {
  return (i + slides.length) % slides.length;
}

function useAutoSlide() {
  const [index, setIndex] = useState(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    timerRef.current = window.setInterval(() => {
      setIndex((i) => clampIndex(i + 1));
    }, SLIDE_INTERVAL_MS);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, []);

  const goTo = (i: number) => setIndex(clampIndex(i));
  return { index, goTo };
}

function SlideImage({ slide }: { slide: Slide }) {
  return (
    <div className="relative h-full w-full shrink-0">
      <img
        src={slide.src}
        alt={slide.title}
        className="h-full w-full object-cover"
        loading="lazy"
      />
    </div>
  );
}

export default function LandmarkSlider({ variant = 'card' }: LandmarkSliderProps) {
  const { index, goTo } = useAutoSlide();

  if (variant === 'background') {
    return (
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0">
        <div
          className="flex h-full w-full transition-transform duration-1000 ease-in-out"
          style={{ transform: `translateX(-${index * 100}%)` }}
        >
          {slides.map((slide) => (
            <div key={slide.src} className="relative h-full w-full shrink-0">
              <img
                src={slide.src}
                alt=""
                className="h-full w-full object-cover"
                loading="lazy"
              />
            </div>
          ))}
        </div>
        <div className="absolute inset-0 bg-gradient-to-b from-white/30 via-white/5 to-white/30" />
      </div>
    );
  }

  return (
    <section
      className="overflow-hidden rounded-xl border border-navy-900 bg-navy-900 shadow-sm"
      aria-label="Iconic Indian landmarks"
    >
      <div className="relative flex h-52 w-full sm:h-60 lg:h-[300px]">
        <div
          className="flex h-full w-full transition-transform duration-700 ease-in-out"
          style={{ transform: `translateX(-${index * 100}%)` }}
        >
          {slides.map((slide) => (
            <SlideImage key={slide.src} slide={slide} />
          ))}
        </div>

        <div className="absolute inset-0 bg-gradient-to-t from-navy-950/50 via-transparent to-navy-950/15" />

        {/* Controls */}
        <div className="absolute inset-x-0 top-1/2 flex -translate-y-1/2 items-center justify-between px-3 sm:px-4">
          <button
            type="button"
            onClick={() => goTo(index - 1)}
            aria-label="Previous landmark"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-navy-950/50 text-white ring-1 ring-white/25 transition-colors hover:bg-[#C9A227] hover:text-navy-950"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            type="button"
            onClick={() => goTo(index + 1)}
            aria-label="Next landmark"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-navy-950/50 text-white ring-1 ring-white/25 transition-colors hover:bg-[#C9A227] hover:text-navy-950"
          >
            <ChevronRight size={18} />
          </button>
        </div>

        {/* Dots */}
        <div className="absolute bottom-3.5 right-4 hidden items-center gap-1.5 sm:flex">
          {slides.map((slide, i) => (
            <button
              key={slide.src}
              type="button"
              aria-label={`Go to ${slide.title}`}
              onClick={() => goTo(i)}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === index
                  ? 'w-6 bg-[#C9A227]'
                  : 'w-1.5 bg-white/40 hover:bg-white/80'
              }`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}