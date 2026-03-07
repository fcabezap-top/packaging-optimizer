import React, { useEffect, useRef, useState } from 'react';
import AppShell from '../../components/layout/AppShell';
import { listContainers, fetchContainerRenderHtml, fetchPreviewRenderHtml, deleteContainer, createContainer, type Container, type ContainerCreate } from '../../api/optimization';
import { useAuthStore } from '../../store/auth';
import './containers.css';

type DimInput = { isRange: boolean; fixed: string; min: string; max: string };
const emptyDim = (): DimInput => ({ isRange: true, fixed: '', min: '', max: '' });

const NumberInput: React.FC<{
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
  min?: number;
  placeholder?: string;
}> = ({ value, onChange, onBlur, placeholder }) => (
  <input
    className="numInput__field"
    type="text"
    inputMode="decimal"
    placeholder={placeholder}
    value={value}
    onChange={(e) => {
        const v = e.target.value.replace(',', '.');
        if (/^\d*\.?\d?$/.test(v)) onChange(v);
      }}
    onBlur={onBlur}
  />
);

const DimRow: React.FC<{ label: string; val: DimInput; set: (v: DimInput) => void }> = ({ label, val, set }) => {
  const clampMin = () => {
    const mn = parseFloat(val.min); const mx = parseFloat(val.max);
    if (!isNaN(mn) && !isNaN(mx) && mn > mx) set({ ...val, min: val.max });
  };
  const clampMax = () => {
    const mn = parseFloat(val.min); const mx = parseFloat(val.max);
    if (!isNaN(mn) && !isNaN(mx) && mx < mn) set({ ...val, max: val.min });
  };
  return (
    <div className="dimRow">
      <div className="dimRow__header">
        <span className="dimRow__label">{label}</span>
        <label className="dimRow__toggle">
          <input type="checkbox" checked={val.isRange} onChange={(e) => set({ ...val, isRange: e.target.checked })} />
          <span>Rango</span>
        </label>
      </div>
      <div className="dimRow__inputs">
        {val.isRange ? (
          <>
            <div className="dimRow__field">
              <label>Mín (cm)</label>
              <NumberInput value={val.min} min={0} placeholder="0" onChange={(v) => set({ ...val, min: v })} onBlur={clampMin} />
            </div>
            <div className="dimRow__field">
              <label>Máx (cm)</label>
              <NumberInput value={val.max} min={0} placeholder="0" onChange={(v) => set({ ...val, max: v })} onBlur={clampMax} />
            </div>
          </>
        ) : (
          <div className="dimRow__field">
            <label>Valor (cm)</label>
            <NumberInput value={val.fixed} min={0} placeholder="0" onChange={(v) => set({ ...val, fixed: v })} />
          </div>
        )}
      </div>
    </div>
  );
};

const ContainersPage: React.FC = () => {
  const token = useAuthStore((s) => s.token) ?? '';
  const [containers, setContainers] = useState<Container[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Container | null>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);
  const [renderHtml, setRenderHtml] = useState<string>('');
  const [renderLoading, setRenderLoading] = useState(false);
  const [renderReady, setRenderReady] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [formL, setFormL] = useState<DimInput>(emptyDim());
  const [formH, setFormH] = useState<DimInput>(emptyDim());
  const [formW, setFormW] = useState<DimInput>(emptyDim());
  const [formMaxAir, setFormMaxAir] = useState('');
  const [formMaxWeight, setFormMaxWeight] = useState('');
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formPriority, setFormPriority] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewReady, setPreviewReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  const dimFilled = (d: DimInput) => d.isRange ? d.min !== '' && d.max !== '' : d.fixed !== '';
  const canPreview =
    formName.trim() !== '' &&
    dimFilled(formL) && dimFilled(formH) && dimFilled(formW) &&
    formPriority !== '' && formMaxAir !== '' && formMaxWeight !== '';
  const canSave = canPreview && previewHtml !== '';

  const handleSave = () => {
    const parseDim = (dim: DimInput) => ({
      min: parseFloat(dim.isRange ? dim.min : dim.fixed) || 0,
      max: parseFloat(dim.isRange ? dim.max : dim.fixed) || 0,
    });
    const payload: ContainerCreate = {
      name: formName.trim(),
      description: formDesc.trim() || undefined,
      dims_cm: { length: parseDim(formL), height: parseDim(formH), width: parseDim(formW) },
      priority: parseInt(formPriority) || 1,
      max_air_pct: parseFloat(formMaxAir) || 0,
      max_weight_kg: parseFloat(formMaxWeight) || 0,
      active: true,
    };
    setSaving(true);
    setSaveError('');
    createContainer(token, payload)
      .then((created) =>
        listContainers(token).then((data) => {
          const sorted = [...data].sort((a, b) => a.priority - b.priority);
          setContainers(sorted);
          setSelected(sorted.find((c) => c.id === created.id) ?? sorted[0] ?? null);
          setShowCreate(false);
        })
      )
      .catch(() => setSaveError('No se pudo guardar. Comprueba tu rol.'))
      .finally(() => setSaving(false));
  };

  useEffect(() => {
    listContainers(token)
      .then((data) => {
        const sorted = [...data].sort((a, b) => a.priority - b.priority);
        setContainers(sorted);
        if (sorted.length) setSelected(sorted[0]);
      })
      .catch(() => setError('No se pudieron cargar los contenedores.'))
      .finally(() => setLoading(false));
  }, [token]);

  // Fetch 3D render HTML whenever selected container changes
  useEffect(() => {
    if (!selected) return;
    setRenderHtml('');
    setRenderReady(false);
    setRenderLoading(true);
    fetchContainerRenderHtml(token, selected.id)
      .then((html) => setRenderHtml(html))
      .catch(() => {})
      .finally(() => setRenderLoading(false));
  }, [selected?.id, token]);

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
  }, [containers]);

  const scroll = (dir: 'left' | 'right') => {
    trackRef.current?.scrollBy({ left: dir === 'left' ? -300 : 300, behavior: 'smooth' });
  };

  const handlePreview = () => {
    const parse = (dim: DimInput) => ({
      min: parseFloat(dim.isRange ? dim.min : dim.fixed) || 0,
      max: parseFloat(dim.isRange ? dim.max : dim.fixed) || 0,
    });
    const l = parse(formL); const h = parse(formH); const w = parse(formW);
    setPreviewReady(false);
    setPreviewLoading(true);
    fetchPreviewRenderHtml(token, {
      length_min: l.min, length_max: l.max,
      height_min: h.min, height_max: h.max,
      width_min:  w.min, width_max:  w.max,
    })
      .then((html) => setPreviewHtml(html))
      .catch(() => {})
      .finally(() => setPreviewLoading(false));
  };

  const handleDelete = () => {
    if (!selected) return;
    setDeleting(true);
    setDeleteError('');
    const deletedId = selected.id;
    deleteContainer(token, deletedId)
      .then(() => listContainers(token))
      .then((data) => {
        const sorted = [...data].sort((a, b) => a.priority - b.priority);
        setContainers(sorted);
        setSelected(sorted.find((c) => c.id !== deletedId) ?? sorted[0] ?? null);
        setShowDeleteModal(false);
      })
      .catch(() => setDeleteError('No se pudo eliminar. Comprueba tu rol.'))
      .finally(() => setDeleting(false));
  };

  return (
    <AppShell>
      {showDeleteModal && selected && (
        <div className="confirmModal" onClick={() => setShowDeleteModal(false)}>
          <div className="confirmModal__dialog" onClick={(e) => e.stopPropagation()}>
            <h3 className="confirmModal__title">Eliminar contenedor</h3>
            <p className="confirmModal__body">
              ¿Seguro que quieres eliminar <strong>{selected.name}</strong>?{' '}
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
      {showCreate ? (
        <div className="createForm">
          <div className="createForm__titleRow">
            <h2 className="createForm__title">Nuevo contenedor</h2>
            <div className="createForm__titleActions">
              <button className="btn btn--ghost btn--sm" onClick={() => setShowCreate(false)}>Volver</button>
              <button className="btn btn--ghost btn--sm" onClick={handlePreview} disabled={!canPreview}>Preview</button>
              <button className="btn btn--sm" onClick={handleSave} disabled={!canSave || saving}>
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
            {saveError && <p className="createForm__saveError">{saveError}</p>}
          </div>
          <div className="createForm__body">
            <div className="createForm__left">
              <div className="createForm__field">
                <label className="createForm__label">Nombre</label>
                <input
                  className="createForm__input"
                  type="text" placeholder="Ej. Caja-M"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>
              <div className="createForm__field">
                <label className="createForm__label">Descripción</label>
                <textarea
                  className="createForm__input createForm__input--textarea"
                  placeholder="Descripción opcional"
                  rows={3}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                />
              </div>
              <p className="createForm__hint">Define las medidas de cada lado. Pueden ser un rango o una medida fija.</p>
              <DimRow label="Length" val={formL} set={setFormL} />
              <DimRow label="Height" val={formH} set={setFormH} />
              <DimRow label="Width"  val={formW} set={setFormW} />
              <div className="createForm__airRow">
                <label className="createForm__airLabel">Peso máximo</label>
                <div className="createForm__airInput">
                  <input
                    type="number" min="0" placeholder="10"
                    value={formMaxWeight}
                    onChange={(e) => setFormMaxWeight(e.target.value)}
                  />
                  <span className="createForm__airUnit">kg</span>
                </div>
              </div>
              <div className="createForm__airRow">
                <label className="createForm__airLabel">Prioridad</label>
                <div className="createForm__airInput">
                  <input
                    type="number" min="1" placeholder="1"
                    value={formPriority}
                    onChange={(e) => setFormPriority(e.target.value)}
                  />
                </div>
                <p className="createForm__airHint">Si ya existe un contenedor con esta prioridad, ese y todos los posteriores se desplazarán automáticamente una posición hacia abajo.</p>
              </div>
              <div className="createForm__airRow">
                <label className="createForm__airLabel">Aire máximo aceptable</label>
                <div className="createForm__airInput">
                  <input
                    type="number" min="0" max="100" placeholder="5"
                    value={formMaxAir}
                    onChange={(e) => setFormMaxAir(e.target.value)}
                  />
                  <span className="createForm__airUnit">%</span>
                </div>
                <p className="createForm__airHint">Porcentaje máximo de espacio vacío antes de pasar a la siguiente prioridad.</p>
              </div>
            </div>
            <div className="createForm__right">
              {previewHtml && (
                <div className="containerDetail__dims createForm__previewDims">
                  {(() => {
                    const parse = (dim: DimInput) => ({
                      min: parseFloat(dim.isRange ? dim.min : dim.fixed) || 0,
                      max: parseFloat(dim.isRange ? dim.max : dim.fixed) || 0,
                    });
                    const l = parse(formL); const h = parse(formH); const w = parse(formW);
                    return (
                      <>
                        {([['Length', l], ['Height', h], ['Width', w]] as [string, {min:number;max:number}][]).map(([label, dim]) => (
                          <span key={label} className="containerDetail__dim">
                            {label} {dim.min === dim.max ? `${dim.min} cm` : `${dim.min}–${dim.max} cm`}
                          </span>
                        ))}
                        {formMaxWeight && <span className="containerDetail__dim">Max weight {formMaxWeight} kg</span>}
                        {formPriority && <span className="containerDetail__dim">Priority {formPriority}</span>}
                        {formMaxAir && <span className="containerDetail__dim">Air max {formMaxAir}%</span>}
                      </>
                    );
                  })()}
                </div>
              )}
              <div className="createForm__previewArea">
                {!previewHtml && !previewLoading && (
                  <p className="createForm__placeholder">Aquí se generará un preview del contenedor</p>
                )}
                {(previewLoading || (previewHtml && !previewReady)) && (
                  <div className="containerDetail__loading">
                    <div className="containerDetail__spinner" />
                  </div>
                )}
                {previewHtml && (
                  <iframe
                    className="containerDetail__render"
                    style={{ opacity: previewReady ? 1 : 0, pointerEvents: previewReady ? 'auto' : 'none' }}
                    srcDoc={previewHtml}
                    title="Preview 3D"
                    sandbox="allow-scripts"
                    onLoad={() => setPreviewReady(true)}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
      <div className="containersPage">
        {/* Fila superior: carrusel (80%) + panel nuevo contenedor (20%) */}
        <div className="containersPage__topRow">
          {/* Carrusel */}
          <div className="carousel">
          <button
            className="carousel__arrow carousel__arrow--left"
            onClick={() => scroll('left')}
            disabled={!canLeft}
            aria-label="Anterior"
          >&#8592;</button>

          <div className="carousel__track" ref={trackRef}>
            {loading && <p className="carousel__msg">Cargando...</p>}
            {error  && <p className="carousel__msg carousel__msg--error">{error}</p>}
            {!loading && !error && containers.map((c) => (
              <button
                key={c.id}
                className={`carousel__card${selected?.id === c.id ? ' carousel__card--active' : ''}`}
                onClick={() => setSelected(c)}
              >
                <span className="carousel__badge">P{c.priority}</span>
                <p className="carousel__name">{c.name}</p>
                <p className="carousel__desc">{c.description ?? '—'}</p>
              </button>
            ))}
          </div>

          <button
            className="carousel__arrow carousel__arrow--right"
            onClick={() => scroll('right')}
            disabled={!canRight}
            aria-label="Siguiente"
          >&#8594;</button>
          </div>{/* end .carousel */}

          {/* Panel crear contenedor */}
          <button className="containerCreate" onClick={() => setShowCreate(true)}>
            <span className="containerCreate__icon">+</span>
            <span className="containerCreate__label">Nuevo contenedor</span>
          </button>
          </div>{/* end .containersPage__topRow */}

        {/* Detalle seleccionado */}
        {selected && (
          <div className="containerDetail">
            <div className="containerDetail__header">
              <div>
                <h2 className="containerDetail__name">{selected.name}</h2>
              </div>
              <div className="containerDetail__actions">
                <button className="btn btn--ghost btn--sm" disabled>Editar</button>
                <button className="btn btn--sm" onClick={() => { setDeleteError(''); setShowDeleteModal(true); }}>Eliminar</button>
              </div>
            </div>
            <p className="containerDetail__desc">{selected.description ?? ''}</p>
            <div className="containerDetail__dims">
              {([
                { label: 'Length', dim: selected.dims_cm.length },
                { label: 'Height', dim: selected.dims_cm.height },
                { label: 'Width',  dim: selected.dims_cm.width },
              ] as { label: string; dim: { min: number; max: number } }[]).map(({ label, dim }) => (
                <span key={label} className="containerDetail__dim">
                  {label} {dim.min === dim.max ? `${dim.min} cm` : `${dim.min}–${dim.max} cm`}
                </span>
              ))}
              <span className="containerDetail__dim">Max weight {selected.max_weight_kg} kg</span>
              <span className="containerDetail__dim">Priority {selected.priority}</span>
              <span className="containerDetail__dim">Air max {selected.max_air_pct}%</span>
            </div>
            {(renderLoading || (renderHtml && !renderReady)) && (
              <div className="containerDetail__loading">
                <div className="containerDetail__spinner" />
              </div>
            )}
            {renderHtml && (
              <iframe
                className="containerDetail__render"
                style={{ opacity: renderReady ? 1 : 0, pointerEvents: renderReady ? 'auto' : 'none' }}
                srcDoc={renderHtml}
                title={`Render 3D ${selected.name}`}
                sandbox="allow-scripts"
                onLoad={() => setRenderReady(true)}
              />
            )}
          </div>
        )}
      </div>
      )}
    </AppShell>
  );
};

export default ContainersPage;

