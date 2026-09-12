import { useEffect, useRef, useState } from 'react';
import { Languages, Check } from 'lucide-react';
import { useI18n, Lang } from '../../i18n';

const options: { value: Lang; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'हिन्दी' },
];

interface LanguageSwitcherProps {
  variant?: 'light' | 'dark';
}

export default function LanguageSwitcher({ variant = 'dark' }: LanguageSwitcherProps) {
  const { lang, setLang } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const base =
    variant === 'light'
      ? 'border-gray-300 bg-white text-navy-800 hover:bg-gray-50'
      : 'border-gray-700 bg-navy-800 text-white hover:bg-navy-700';

  const menuItem =
    'flex w-full items-center justify-between gap-6 px-3 py-2 text-left text-sm transition-colors';

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex h-9 items-center gap-1.5 rounded-lg border px-3 text-sm font-medium transition-colors ${base}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Select language"
      >
        <Languages size={16} />
        <span className="hidden sm:inline">{lang === 'en' ? 'English' : 'हिन्दी'}</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-40 overflow-hidden rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
        >
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              role="menuitem"
              onClick={() => {
                setLang(option.value);
                setOpen(false);
              }}
              className={`${menuItem} ${
                lang === option.value
                  ? 'bg-navy-50 font-semibold text-navy-900'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              {option.label}
              {lang === option.value && <Check size={15} className="text-blue-600" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
