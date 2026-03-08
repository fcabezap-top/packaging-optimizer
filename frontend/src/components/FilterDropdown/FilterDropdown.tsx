import React, { useEffect, useRef, useState } from 'react';
import './FilterDropdown.css';

export interface DropdownOption { id: string; name: string; }

interface Props {
  label: string;
  options: DropdownOption[];
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
}

const FilterDropdown: React.FC<Props> = ({ label, options, value, onChange, disabled }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className={`fdd__root${disabled ? ' fdd__root--disabled' : ''}`} ref={ref}>
      <button
        className="fdd__trigger"
        onClick={() => !disabled && setOpen((o) => !o)}
        type="button"
      >
        <span>{label}</span>
        <svg className={`fdd__arrow${open ? ' fdd__arrow--open' : ''}`} width="8" height="5" viewBox="0 0 8 5">
          <path d="M0 0l4 5 4-5z" fill="currentColor" />
        </svg>
      </button>
      {open && (
        <ul className="fdd__list">
          {options.map((o) => (
            <li
              key={o.id}
              className={`fdd__item${value === o.id ? ' fdd__item--active' : ''}`}
              onMouseDown={() => { onChange(o.id); setOpen(false); }}
            >
              {o.name.toUpperCase()}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default FilterDropdown;
