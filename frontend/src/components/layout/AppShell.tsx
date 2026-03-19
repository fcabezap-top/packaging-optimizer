import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import './AppShell.css';

interface Tab {
  label: string;
  path: string;
  roles?: string[];
}

const TABS: Tab[] = [
  { label: 'Producto',     path: '/product',      roles: ['reviewer', 'admin'] },
  { label: 'Contenedores', path: '/containers',   roles: ['reviewer', 'admin'] },
  { label: 'Reglas',       path: '/rules',        roles: ['reviewer', 'admin'] },
  { label: 'Producto',     path: '/manufacturer', roles: ['manufacturer'] },
  { label: 'Propuestas',   path: '/proposals',    roles: ['manufacturer'] },
];

interface AppShellProps {
  children: React.ReactNode;
  fullWidth?: boolean;
}

const AppShell: React.FC<AppShellProps> = ({ children, fullWidth }) => {
  const { username, fullName, role, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const visibleTabs = TABS.filter(
    (tab) => !tab.roles || (role && tab.roles.includes(role))
  );

  // /proposals/review is a sub-page of the reviewer's Product tab
  const effectivePath = location.pathname === '/proposals/review'
    ? '/product'
    : location.pathname;

  const activeTab = visibleTabs.find((t) => effectivePath.startsWith(t.path));
  const sectionLabel = activeTab?.label ?? visibleTabs[0]?.label ?? '';

  return (
    <div className="shell">
      <header className="shell__header">
        <span className="shell__logo">Packaging Optimizer</span>
        <span className="shell__section">{sectionLabel}</span>
        <div className="shell__user">
          <span className="shell__username">{fullName ?? username} · {role}</span>
          <button className="shell__logout" onClick={clearAuth}>Salir</button>
        </div>
      </header>

      <div className="shell__tabs">
        {visibleTabs.map((tab) => {
          const isActive = effectivePath.startsWith(tab.path);
          // Propuestas tab: informative only — no direct navigation
          const isDisabled = tab.path === '/proposals' && !isActive;
          return (
            <button
              key={tab.path}
              className={`shell__tab${isActive ? ' shell__tab--active' : ''}${isDisabled ? ' shell__tab--disabled' : ''}`}
              onClick={isDisabled ? undefined : () => navigate(tab.path)}
              disabled={isDisabled}
              title={isDisabled ? 'Accede desde un producto' : undefined}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <main className={`shell__content${(role === 'manufacturer' || fullWidth) ? ' shell__content--full' : ''}`}>
        {children}
      </main>
    </div>
  );
};

export default AppShell;

