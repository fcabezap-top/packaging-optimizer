import React, { useEffect, useMemo, useState } from 'react';
import { useAuthStore } from '../../store/auth';
import AppShell from '../../components/layout/AppShell';
import FilterDropdown, { type DropdownOption } from '../../components/FilterDropdown/FilterDropdown';
import { listAllProposals, type ProposalResult } from '../../api/optimization';
import { fetchAllProducts, type ProductDetail } from '../../api/product';
import { listUsers, type UserInfo } from '../../api/auth';
import './dashboard.css';

const DashboardPage: React.FC = () => {
  const token = useAuthStore((s) => s.token) ?? '';

  const [proposals, setProposals] = useState<ProposalResult[]>([]);
  const [products,  setProducts]  = useState<ProductDetail[]>([]);
  const [users,     setUsers]     = useState<UserInfo[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState('');
  const [filterMfr, setFilterMfr] = useState('');

  useEffect(() => {
    if (!token) return;
    Promise.all([listAllProposals(token), fetchAllProducts(token), listUsers(token)])
      .then(([p, pr, u]) => { setProposals(p); setProducts(pr); setUsers(u); })
      .catch(() => setError('No se pudieron cargar los datos.'))
      .finally(() => setLoading(false));
  }, [token]);

  const manufacturerUsers = useMemo(() => users.filter((u) => u.role === 'manufacturer'), [users]);

  const manufacturerOptions: DropdownOption[] = useMemo(() => [
    { id: '', name: 'Todos los fabricantes' },
    ...manufacturerUsers.map((u) => ({ id: u.id ?? u.username, name: `${u.first_name} ${u.last_name}` })),
  ], [manufacturerUsers]);

  const selectedUser = useMemo(
    () => (filterMfr ? users.find((u) => (u.id ?? u.username) === filterMfr) ?? null : null),
    [filterMfr, users]
  );

  const filteredProposals = useMemo(() => {
    if (!selectedUser) return proposals;
    const uid = selectedUser.id; const uname = selectedUser.username;
    return proposals.filter((p) => (uid != null && p.created_by === uid) || p.created_by === uname);
  }, [proposals, selectedUser]);

  const filteredProducts = useMemo(() => {
    if (!selectedUser) return products;
    const uid = selectedUser.id ?? selectedUser.username;
    return products.filter((p) => p.manufacturer_id === uid);
  }, [products, selectedUser]);

  // Estado por producto: accepted > pending > rejected
  const derivedByProduct = useMemo(() => {
    const byPid = new Map<string, string[]>();
    filteredProposals.forEach((p) => {
      if (!byPid.has(p.product_id)) byPid.set(p.product_id, []);
      byPid.get(p.product_id)!.push(p.status);
    });
    const result = new Map<string, 'pending' | 'accepted' | 'rejected'>();
    byPid.forEach((statuses, pid) => {
      if (statuses.includes('accepted')) result.set(pid, 'accepted');
      else if (statuses.includes('pending')) result.set(pid, 'pending');
      else result.set(pid, 'rejected');
    });
    return result;
  }, [filteredProposals]);

  // KPI values â€” contamos productos Ãºnicos, no propuestas
  const proposalProductIds = useMemo(() => new Set(derivedByProduct.keys()), [derivedByProduct]);
  const productsPendientes = filteredProducts.filter((p) => !proposalProductIds.has(p.id)).length;
  const proposalsPending   = [...derivedByProduct.values()].filter((s) => s === 'pending').length;
  const accepted           = [...derivedByProduct.values()].filter((s) => s === 'accepted').length;
  const rejected           = [...derivedByProduct.values()].filter((s) => s === 'rejected').length;

  const withMaster = filteredProposals.filter((p) => p.selected_master != null);
  const avgFill = withMaster.length ? withMaster.reduce((s, p) => s + p.selected_master!.fill_pct, 0) / withMaster.length : null;
  const avgAir  = withMaster.length ? withMaster.reduce((s, p) => s + p.selected_master!.air_pct,  0) / withMaster.length : null;
  const decided = accepted + rejected;
  const rejectionRate = decided > 0 ? (rejected / decided) * 100 : null;

  const byManufacturer = useMemo(() => {
    const visibleMfrs = filterMfr
      ? manufacturerUsers.filter((u) => (u.id ?? u.username) === filterMfr)
      : manufacturerUsers;

    return visibleMfrs.map((u) => {
      const uid = u.id; const uname = u.username;
      const mfrProps = proposals.filter((p) => (uid != null && p.created_by === uid) || p.created_by === uname);
      const byPid = new Map<string, string[]>();
      mfrProps.forEach((p) => {
        if (!byPid.has(p.product_id)) byPid.set(p.product_id, []);
        byPid.get(p.product_id)!.push(p.status);
      });
      let pend = 0, acc = 0, rej = 0;
      byPid.forEach((statuses) => {
        if (statuses.includes('accepted')) acc++;
        else if (statuses.includes('pending')) pend++;
        else rej++;
      });
      const mfrProdUid = uid ?? uname;
      const mfrProdCount = products.filter((p) => p.manufacturer_id === mfrProdUid).length;
      return {
        name: `${u.first_name} ${u.last_name}`,
        sinPropuesta: Math.max(0, mfrProdCount - byPid.size),
        pending: pend, accepted: acc, rejected: rej,
      };
    }).sort((a, b) => (b.pending + b.accepted + b.rejected) - (a.pending + a.accepted + a.rejected));
  }, [manufacturerUsers, proposals, products, filterMfr]);

  return (
    <AppShell fullWidth>
      <div className="dash__page">
        {/* Toolbar */}
        <div className="dash__toolbar">
          <FilterDropdown
            label={selectedUser ? `${selectedUser.first_name} ${selectedUser.last_name}` : 'FABRICANTE'}
            options={manufacturerOptions}
            value={filterMfr}
            onChange={setFilterMfr}
          />
          {filterMfr && selectedUser && (
            <button className="btn btn--ghost btn--sm" onClick={() => setFilterMfr('')}>
              {selectedUser.first_name} {selectedUser.last_name} Ã—
            </button>
          )}
        </div>

        {loading && <p className="dash__loading">Cargando mÃ©tricasâ€¦</p>}
        {error   && <p className="dash__error">{error}</p>}

        {!loading && !error && (
          <>
            <section className="dash__section">
              <div className="dash__kpiRow">
                <div className="dash__kpi">
                  <span className="dash__kpiLabel">Pendientes</span>
                  <span className="dash__kpiValue">{productsPendientes}</span>
                  <span className="dash__kpiSub">productos sin propuesta</span>
                </div>
                <div className="dash__kpi">
                  <span className="dash__kpiLabel">Propuestas</span>
                  <span className="dash__kpiValue">{proposalsPending}</span>
                  <span className="dash__kpiSub">generadas, por decidir</span>
                </div>
                <div className="dash__kpi dash__kpi--green">
                  <span className="dash__kpiLabel">Aceptadas</span>
                  <span className="dash__kpiValue">{accepted}</span>
                  <span className="dash__kpiSub">propuestas aceptadas</span>
                </div>
                <div className="dash__kpi dash__kpi--red">
                  <span className="dash__kpiLabel">Rechazadas</span>
                  <span className="dash__kpiValue">{rejected}</span>
                  <span className="dash__kpiSub">propuestas rechazadas</span>
                </div>
              </div>
            </section>

            <section className="dash__section dash__section--mt">
              <h2 className="dash__sectionTitle">Eficiencia de embalaje</h2>
              <div className="dash__kpiRow">
                <div className="dash__kpi">
                  <span className="dash__kpiLabel">OcupaciÃ³n media</span>
                  <span className="dash__kpiValue">{avgFill != null ? `${avgFill.toFixed(1)}%` : 'â€”'}</span>
                  <span className="dash__kpiSub">fill_pct promedio</span>
                </div>
                <div className="dash__kpi">
                  <span className="dash__kpiLabel">Aire medio</span>
                  <span className="dash__kpiValue">{avgAir != null ? `${avgAir.toFixed(1)}%` : 'â€”'}</span>
                  <span className="dash__kpiSub">espacio vacÃ­o promedio</span>
                </div>
                <div className="dash__kpi">
                  <span className="dash__kpiLabel">Tasa de rechazo</span>
                  <span className="dash__kpiValue">{rejectionRate != null ? `${rejectionRate.toFixed(1)}%` : 'â€”'}</span>
                  <span className="dash__kpiSub">sobre propuestas decididas</span>
                </div>
              </div>
            </section>

            {byManufacturer.length > 0 && (
              <section className="dash__section dash__section--mt">
                <h2 className="dash__sectionTitle">Por fabricante</h2>
                <table className="dash__table">
                  <thead>
                    <tr>
                      <th>Fabricante</th>
                      <th>Pendientes</th>
                      <th>Propuestas</th>
                      <th>Aceptadas</th>
                      <th>Rechazadas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {byManufacturer.map((row) => (
                      <tr key={row.name}>
                        <td>{row.name}</td>
                        <td>{row.sinPropuesta}</td>
                        <td>{row.pending}</td>
                        <td className="dash__cell--green">{row.accepted}</td>
                        <td className="dash__cell--red">{row.rejected}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
};

export default DashboardPage;
