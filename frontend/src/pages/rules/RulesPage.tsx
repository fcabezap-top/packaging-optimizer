import React, { useEffect, useRef, useState } from 'react';
import AppShell from '../../components/layout/AppShell';
import {
  listRules, listRuleAssignments, createRuleAssignment, deleteRuleAssignment,
  fetchRuleRenderHtml,
  type Rule, type RuleAssignment,
} from '../../api/optimization';
import { listFamilies, listSubfamilies, type Family, type Subfamily } from '../../api/product';
import { useAuthStore } from '../../store/auth';
import '../containers/containers.css';
import './rules.css';

// An assignment enriched with resolved names for display
interface EnrichedAssignment {
  assignment: RuleAssignment;
  rule: Rule;
  familyName: string;
  subfamilyNames: string[];  // empty = whole family
  scopeNames: string[];      // display strings: "FAMILIA — SUBFAMILIA" or "FAMILIA (toda la familia)"
}

const constraintTags = (rule: Rule): string[] => {
  const parts: string[] = [];
  if (rule.constraint.orientation_locked) {
    const axis = rule.constraint.locked_axis;
    if (axis === 'height') parts.push('Posición: vertical (altura arriba)');
    else if (axis === 'width') parts.push('Posición: horizontal (anchura arriba)');
    else if (axis === 'length') parts.push('Posición: eje longitud forzado');
    else parts.push('Orientación bloqueada');
  }
  if (rule.constraint.max_stack_layers != null) {
    parts.push(`Máx. capas: ${rule.constraint.max_stack_layers}`);
  }
  return parts;
};

const RulesPage: React.FC = () => {
  const token = useAuthStore((s) => s.token) ?? '';

  // ── Catálogos (cargados una vez) ──────────────────────────────────────────
  const [allRules, setAllRules] = useState<Rule[]>([]);
  const [allFamilies, setAllFamilies] = useState<Family[]>([]);
  const [allSubfamilies, setAllSubfamilies] = useState<Subfamily[]>([]);

  // ── Vista carrusel ────────────────────────────────────────────────────────
  const [items, setItems] = useState<EnrichedAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<EnrichedAssignment | null>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  // ── Modal eliminar ────────────────────────────────────────────────────────
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  // ── Formulario asignar ────────────────────────────────────────────────────
  const [showForm, setShowForm] = useState(false);
  const [formRuleId, setFormRuleId] = useState('');
  const [formFamilyId, setFormFamilyId] = useState('');
  const [formSubfamilyIds, setFormSubfamilyIds] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  // Subfamilias filtradas por la familia seleccionada en el form
  const formSubfamilies = allSubfamilies.filter((s) => s.family_id === formFamilyId);

  const canSave = formRuleId !== '' && formFamilyId !== '';

  const resetForm = () => {
    setFormRuleId('');
    setFormFamilyId('');
    setFormSubfamilyIds([]);
    setSaveError('');
  };

  const openForm = () => { resetForm(); setShowForm(true); };

  const toggleSubfamily = (id: string) => {
    setFormSubfamilyIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  // ── Carga de datos ────────────────────────────────────────────────────────
  const loadAll = () => {
    Promise.all([
      listRuleAssignments(token),
      listRules(token),
      listFamilies(token),
      listSubfamilies(token),
    ])
      .then(([assignments, rules, families, subfamilies]) => {
        setAllRules(rules);
        setAllFamilies(families);
        setAllSubfamilies(subfamilies);

        const ruleMap = new Map<string, Rule>(rules.map((r) => [r.id, r]));
        const familyMap = new Map<string, Family>(families.map((f) => [f.id, f]));
        const subfamilyMap = new Map<string, Subfamily>(subfamilies.map((s) => [s.id, s]));

        const enriched: EnrichedAssignment[] = assignments
          .filter((a) => ruleMap.has(a.rule_id))
          .map((a) => {
            const rule = ruleMap.get(a.rule_id)!;
            const familyName = familyMap.get(a.filter.family_id)?.name ?? a.filter.family_id;
            const subfamilyNames = a.filter.subfamily_ids.map((id) => subfamilyMap.get(id)?.name ?? id);
            const scopeNames: string[] = subfamilyNames.length > 0
              ? subfamilyNames.map((s) => `${familyName} — ${s}`)
              : [`${familyName} (toda la familia)`];
            return { assignment: a, rule, familyName, subfamilyNames, scopeNames };
          });

        setItems(enriched);
        if (enriched.length) setSelected((prev) => enriched.find((e) => e.assignment.id === prev?.assignment.id) ?? enriched[0]);
        else setSelected(null);
      })
      .catch(() => setError('No se pudieron cargar las asignaciones.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadAll(); }, [token]);

  // ── Render 3D (cacheado por rule.id) ─────────────────────────────────────
  const renderCache = useRef<Map<string, string>>(new Map());
  const [renderHtml, setRenderHtml] = useState('');
  const [renderLoading, setRenderLoading] = useState(false);
  const [renderReady, setRenderReady] = useState(false);

  useEffect(() => {
    if (!selected) return;
    const ruleId = selected.rule.id;
    setRenderReady(false);
    if (renderCache.current.has(ruleId)) {
      setRenderHtml(renderCache.current.get(ruleId)!);
      return;
    }
    setRenderHtml('');
    setRenderLoading(true);
    fetchRuleRenderHtml(token, ruleId)
      .then((html) => { renderCache.current.set(ruleId, html); setRenderHtml(html); })
      .catch(() => {})
      .finally(() => setRenderLoading(false));
  }, [selected?.rule.id, token]);

  // ── Flechas carrusel ──────────────────────────────────────────────────────
  const updateArrows = () => {
    const el = trackRef.current;
    if (!el) return;
    setCanLeft(el.scrollLeft > 0);
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  };

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    updateArrows();
    el.addEventListener('scroll', updateArrows);
    window.addEventListener('resize', updateArrows);
    return () => {
      el.removeEventListener('scroll', updateArrows);
      window.removeEventListener('resize', updateArrows);
    };
  }, [items]);

  const scroll = (dir: 'left' | 'right') => {
    trackRef.current?.scrollBy({ left: dir === 'left' ? -300 : 300, behavior: 'smooth' });
  };

  // ── Render 3D para el formulario (por rule seleccionada en el form) ──────
  const [formRenderHtml, setFormRenderHtml] = useState('');
  const [formRenderLoading, setFormRenderLoading] = useState(false);
  const [formRenderReady, setFormRenderReady] = useState(false);
  const formRenderCache = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    if (!formRuleId) { setFormRenderHtml(''); return; }
    setFormRenderReady(false);
    if (formRenderCache.current.has(formRuleId)) {
      setFormRenderHtml(formRenderCache.current.get(formRuleId)!);
      return;
    }
    setFormRenderHtml('');
    setFormRenderLoading(true);
    fetchRuleRenderHtml(token, formRuleId)
      .then((html) => { formRenderCache.current.set(formRuleId, html); setFormRenderHtml(html); })
      .catch(() => {})
      .finally(() => setFormRenderLoading(false));
  }, [formRuleId, token]);

  // ── Guardar asignación ────────────────────────────────────────────────────
  const handleSave = () => {
    setSaving(true);
    setSaveError('');
    createRuleAssignment(token, {
      rule_id: formRuleId,
      filter: { family_id: formFamilyId, subfamily_ids: formSubfamilyIds },
    })
      .then(() => {
        setShowForm(false);
        resetForm();
        setLoading(true);
        loadAll();
      })
      .catch(() => setSaveError('No se pudo guardar. Comprueba tu rol.'))
      .finally(() => setSaving(false));
  };

  // ── Eliminar asignación ───────────────────────────────────────────────────
  const handleDelete = () => {
    if (!selected) return;
    setDeleting(true);
    setDeleteError('');
    const deletedId = selected.assignment.id;
    deleteRuleAssignment(token, deletedId)
      .then(() => {
        setShowDeleteModal(false);
        setLoading(true);
        loadAll();
      })
      .catch(() => setDeleteError('No se pudo eliminar. Comprueba tu rol.'))
      .finally(() => setDeleting(false));
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <AppShell>
      {/* Modal eliminar */}
      {showDeleteModal && selected && (
        <div className="confirmModal" onClick={() => setShowDeleteModal(false)}>
          <div className="confirmModal__dialog" onClick={(e) => e.stopPropagation()}>
            <h3 className="confirmModal__title">Eliminar asignación</h3>
            <p className="confirmModal__body">
              ¿Seguro que quieres eliminar la asignación de <strong>{selected.rule.name}</strong> para{' '}
              <strong>{selected.scopeNames.join(', ')}</strong>?{' '}
              Esta acción no se puede deshacer.
            </p>
            {deleteError && <p className="confirmModal__error">{deleteError}</p>}
            <div className="confirmModal__actions">
              <button className="btn btn--ghost btn--sm" onClick={() => setShowDeleteModal(false)} disabled={deleting}>Cancelar</button>
              <button className="btn btn--sm" onClick={handleDelete} disabled={deleting}>
                {deleting ? 'Eliminando...' : 'Eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showForm ? (
        /* ── Formulario asignar regla ────────────────────────────────────── */
        <div className="createForm">
          <div className="createForm__titleRow">
            <h2 className="createForm__title">Asignar regla</h2>
            <div className="createForm__titleActions">
              <button className="btn btn--ghost btn--sm" onClick={() => { setShowForm(false); resetForm(); }}>Volver</button>
              <button className="btn btn--sm" onClick={handleSave} disabled={!canSave || saving}>
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
            {saveError && <p className="createForm__saveError">{saveError}</p>}
          </div>
          <div className="createForm__body">
            <div className="createForm__left">

              {/* Seleccionar regla */}
              <div className="createForm__field">
                <label className="createForm__label">Regla</label>
                <select
                  className="createForm__input"
                  value={formRuleId}
                  onChange={(e) => setFormRuleId(e.target.value)}
                >
                  <option value="">— Selecciona una regla —</option>
                  {allRules.filter((r) => r.active).map((r) => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
                {formRuleId && (
                  <p className="createForm__hint">
                    {allRules.find((r) => r.id === formRuleId)?.description ?? ''}
                  </p>
                )}
              </div>

              {/* Seleccionar familia */}
              <div className="createForm__field">
                <label className="createForm__label">Familia</label>
                <select
                  className="createForm__input"
                  value={formFamilyId}
                  onChange={(e) => { setFormFamilyId(e.target.value); setFormSubfamilyIds([]); }}
                >
                  <option value="">— Selecciona una familia —</option>
                  {allFamilies.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              </div>

              {/* Seleccionar subfamilias */}
              {formFamilyId && (
                <div className="createForm__field">
                  <label className="createForm__label">Subfamilias</label>
                  <p className="createForm__hint">
                    Sin selección → aplica a toda la familia.
                  </p>
                  <div className="ruleForm__checkList">
                    {formSubfamilies.map((s) => (
                      <label key={s.id} className="ruleForm__checkItem">
                        <input
                          type="checkbox"
                          checked={formSubfamilyIds.includes(s.id)}
                          onChange={() => toggleSubfamily(s.id)}
                        />
                        {s.name}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Lado derecho: render + resumen */}
            <div className="createForm__right">
              <div className="createForm__previewArea">
                {/* Resumen encima del render */}
                {(formRuleId || formFamilyId) && (
                  <div className="ruleForm__summary" style={{ marginBottom: formRenderHtml ? 'var(--size-4)' : 0, flexShrink: 0 }}>
                    {formRuleId && (
                      <>
                        <p className="ruleForm__summaryLabel">Regla</p>
                        <p className="ruleForm__summaryValue">{allRules.find((r) => r.id === formRuleId)?.name}</p>
                      </>
                    )}
                    {formFamilyId && (
                      <>
                        <p className="ruleForm__summaryLabel">Aplicará a</p>
                        {formSubfamilyIds.length > 0
                          ? formSubfamilyIds.map((id) => {
                              const s = allSubfamilies.find((x) => x.id === id);
                              const f = allFamilies.find((x) => x.id === formFamilyId);
                              return (
                                <p key={id} className="ruleForm__summaryValue">
                                  {f?.name} — {s?.name}
                                </p>
                              );
                            })
                          : <p className="ruleForm__summaryValue">
                              {allFamilies.find((f) => f.id === formFamilyId)?.name} (toda la familia)
                            </p>
                        }
                      </>
                    )}
                  </div>
                )}

                {/* Render 3D debajo del resumen */}
                {(formRenderLoading || formRenderHtml) ? (
                  <div className="containerDetail__renderWrap" style={{ flex: 1, width: '100%', minHeight: 0 }}>
                    {(formRenderLoading || (formRenderHtml && !formRenderReady)) && (
                      <div
                        className="containerDetail__loading"
                        style={{
                          opacity: (formRenderLoading || !formRenderReady) ? 1 : 0,
                          transition: formRenderReady ? 'opacity 0.3s ease' : 'none',
                          pointerEvents: 'none',
                        }}
                      >
                        <div className="containerDetail__spinner" />
                      </div>
                    )}
                    {formRenderHtml && (
                      <iframe
                        className="containerDetail__render"
                        style={{ opacity: 1, marginTop: 0 }}
                        srcDoc={formRenderHtml}
                        title="Render regla"
                        sandbox="allow-scripts"
                        onLoad={() => setFormRenderReady(true)}
                      />
                    )}
                  </div>
                ) : (
                  !formRuleId && !formFamilyId
                    ? <p className="createForm__placeholder">Selecciona una regla y una familia para ver el resumen</p>
                    : null
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ── Vista carrusel ──────────────────────────────────────────────── */
        <div className="rulesPage">
          <div className="rulesPage__topRow">
            {/* Carrusel */}
            <div className="carousel">
              <button className="carousel__arrow carousel__arrow--left" onClick={() => scroll('left')} disabled={!canLeft} aria-label="Anterior">&#8592;</button>
              <div className="carousel__track" ref={trackRef}>
                {loading && <p className="carousel__msg">Cargando...</p>}
                {error && <p className="carousel__msg carousel__msg--error">{error}</p>}
                {!loading && !error && items.length === 0 && (
                  <p className="carousel__msg">No hay asignaciones aún.</p>
                )}
                {!loading && !error && items.map((item) => (
                  <button
                    key={item.assignment.id}
                    className={`carousel__card${selected?.assignment.id === item.assignment.id ? ' carousel__card--active' : ''}`}
                    onClick={() => setSelected(item)}
                  >
                    <span className="carousel__badge">{item.familyName.toUpperCase()}</span>
                    <p className="carousel__name">{item.rule.name}</p>
                    <p className="carousel__desc">
                      {item.subfamilyNames.length > 0 ? item.subfamilyNames.join(', ') : 'Toda la familia'}
                    </p>
                  </button>
                ))}
              </div>
              <button className="carousel__arrow carousel__arrow--right" onClick={() => scroll('right')} disabled={!canRight} aria-label="Siguiente">&#8594;</button>
            </div>

            {/* Botón asignar */}
            <button className="containerCreate" onClick={openForm}>
              <span className="containerCreate__icon">+</span>
              <span className="containerCreate__label">Asignar regla</span>
            </button>
          </div>

          {/* Detalle */}
          {selected ? (
            <div className="containerDetail">
              <div className="containerDetail__header">
                <div>
                  <h2 className="containerDetail__name">{selected.rule.name}</h2>
                </div>
                <div className="containerDetail__actions">
                  <button className="btn btn--sm" onClick={() => { setDeleteError(''); setShowDeleteModal(true); }}>Eliminar</button>
                </div>
              </div>
              <p className="containerDetail__desc">{selected.rule.description ?? ''}</p>
              <div className="containerDetail__dims">
                {constraintTags(selected.rule).map((tag) => (
                  <span key={tag} className="containerDetail__dim">{tag}</span>
                ))}
                <span className="containerDetail__dim">Familia: {selected.familyName}</span>
                {selected.subfamilyNames.length > 0
                  ? selected.subfamilyNames.map((s) => (
                      <span key={s} className="containerDetail__dim">{selected.familyName} — {s}</span>
                    ))
                  : <span className="containerDetail__dim">Toda la familia</span>
                }
                <span className="containerDetail__dim">{selected.assignment.active ? 'Activa' : 'Inactiva'}</span>
              </div>
              <div className="containerDetail__renderWrap">
                {(renderLoading || renderHtml) && (
                  <div
                    className="containerDetail__loading"
                    style={{
                      opacity: (renderLoading || !renderReady) ? 1 : 0,
                      transition: renderReady ? 'opacity 0.3s ease' : 'none',
                      pointerEvents: 'none',
                    }}
                  >
                    <div className="containerDetail__spinner" />
                  </div>
                )}
                {renderHtml && (
                  <iframe
                    className="containerDetail__render"
                    style={{ opacity: 1 }}
                    srcDoc={renderHtml}
                    title={`Render regla ${selected.rule.name}`}
                    sandbox="allow-scripts"
                    onLoad={() => setRenderReady(true)}
                  />
                )}
              </div>
            </div>
          ) : (
            !loading && !error && (
              <div className="page__emptyDetail"><p>No hay asignaciones aún.</p></div>
            )
          )}
        </div>
      )}
    </AppShell>
  );
};

export default RulesPage;
