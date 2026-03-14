import React, { useEffect, useState, useMemo, useRef } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import AppShell from '../../components/layout/AppShell';
import { useAuthStore } from '../../store/auth';
import { fetchProduct, type ProductDetail, type ProductSize } from '../../api/product';
import { submitProposal, recalculateProposal, type ProposalResult, type ProposalCreateBody } from '../../api/optimization';
import './proposals.css';
import '../containers/containers.css';

// â”€â”€ Per-size row data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
interface SizeRow {
  length: string;
  width:  string;
  height: string;
  weight: string;
  lotSize: string;
}

const emptyRow = (): SizeRow => ({ length: '', width: '', height: '', weight: '', lotSize: '' });

function rowFilled(r: SizeRow): boolean {
  return (
    parseFloat(r.length) > 0 &&
    parseFloat(r.width)  > 0 &&
    parseFloat(r.height) > 0 &&
    parseFloat(r.weight) > 0 &&
    parseInt(r.lotSize)  > 0
  );
}

// â”€â”€ Inline cell input â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const CellInput: React.FC<{
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  integer?: boolean;
}> = ({ value, onChange, placeholder, integer = false }) => (
  <input
    className="prop__cell-input"
    type="text"
    inputMode={integer ? 'numeric' : 'decimal'}
    placeholder={placeholder}
    value={value}
    onChange={(e) => {
      const v = e.target.value.replace(',', '.');
      const ok = integer ? /^\d*$/.test(v) : /^\d*\.?\d*$/.test(v);
      if (ok) onChange(v);
    }}
  />
);

// â”€â”€ Result row per size â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const SizeResult: React.FC<{ size: ProductSize; result: ProposalResult | { error: string } }> = ({ size, result }) => {
  if ('error' in result) {
    return (
      <div className="prop__size-result prop__size-result--err">
        <span className="prop__size-result-name">{size.name}</span>
        <span className="prop__size-result-msg">{result.error}</span>
      </div>
    );
  }
  const m = result.selected_master;
  if (!m) {
    return (
      <div className="prop__size-result prop__size-result--warn">
        <span className="prop__size-result-name">{size.name}</span>
        <span className="prop__size-result-msg">NingÃºn contenedor compatible con el aire mÃ¡ximo configurado.</span>
      </div>
    );
  }
  return (
    <div className="prop__size-result prop__size-result--ok">
      <span className="prop__size-result-name">{size.name}</span>
      <div className="prop__result-chips">
        <span className="prop__chip prop__chip--accent">{m.container_name}</span>
        <span className="prop__chip">Relleno {m.fill_pct.toFixed(1)}Â %</span>
        <span className="prop__chip">Aire {m.air_pct.toFixed(1)}Â %</span>
        <span className="prop__chip">{m.inners_used} cajas int.</span>
        <span className="prop__chip">{m.total_weight_kg.toFixed(2)}Â kg</span>
      </div>
      {result.inner_box && (
        <span className="prop__size-result-inner">
          Caja int. ext.: {result.inner_box.ext_max_cm.toFixed(1)}Â Ã—Â {result.inner_box.ext_med_cm.toFixed(1)}Â Ã—Â {result.inner_box.ext_min_cm.toFixed(1)} cm
        </span>
      )}
    </div>
  );
};

// â”€â”€ Table rows â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// ── Proposal result full view ───────────────────────────────────────────────
const ProposalResultView: React.FC<{
  sizes: ProductSize[];
  results: Record<string, ProposalResult>;
}> = ({ sizes, results }) => {
  const [activeIdx, setActiveIdx] = useState(0);
  const size = sizes[activeIdx];
  if (!size) return null;
  const res = results[size.id];
  const m = 'error' in res ? null : (res as ProposalResult).selected_master;
  const ib = 'error' in res ? null : (res as ProposalResult).inner_box;
  const html = 'error' in res ? null : (res as ProposalResult).render_html;

  return (
    <div className="prop__rv">
      <div className="prop__rv-tabs">
        {sizes.map((s, i) => (
          <button
            key={s.id}
            className={`prop__rv-tab${i === activeIdx ? ' prop__rv-tab--active' : ''}`}
            onClick={() => setActiveIdx(i)}
          >
            {s.name}
          </button>
        ))}
      </div>

      {'error' in res ? (
        <div className="prop__rv-error">{(res as { error: string }).error}</div>
      ) : (
        <div className="prop__rv-body">
          <div className="prop__rv-panel">
            {m ? (
              <>
                <div className="prop__rv-section">
                  <p className="prop__rv-section-title">Master box</p>
                  <div className="prop__rv-row"><span className="prop__rv-label">Exterior</span><span className="prop__rv-value">{m.ext_dims?.[0]?.toFixed(1)} &times; {m.ext_dims?.[1]?.toFixed(1)} &times; {m.ext_dims?.[2]?.toFixed(1)} cm</span></div>
                  <div className="prop__rv-row"><span className="prop__rv-label">Utilizable</span><span className="prop__rv-value">{m.util_dims?.[0]?.toFixed(1)} &times; {m.util_dims?.[1]?.toFixed(1)} &times; {m.util_dims?.[2]?.toFixed(1)} cm</span></div>
                </div>
                <div className="prop__rv-section">
                  <p className="prop__rv-section-title">Inner box</p>
                  <div className="prop__rv-row"><span className="prop__rv-label">Base capacity</span><span className="prop__rv-value">{(res as ProposalResult).lot_size} units</span></div>
                  <div className="prop__rv-row"><span className="prop__rv-label">Total placed</span><span className="prop__rv-value">{m.inners_used * (res as ProposalResult).lot_size} units</span></div>
                  {ib && <div className="prop__rv-row"><span className="prop__rv-label">Size</span><span className="prop__rv-value">{ib.ext_max_cm.toFixed(1)} &times; {ib.ext_med_cm.toFixed(1)} &times; {ib.ext_min_cm.toFixed(1)} cm</span></div>}
                </div>
                <div className="prop__rv-section">
                  <p className="prop__rv-section-title">Metrics</p>
                  <div className="prop__rv-row"><span className="prop__rv-label">Fill</span><span className="prop__rv-value prop__rv-value--accent">{m.fill_pct.toFixed(0)}%</span></div>
                  <div className="prop__rv-row"><span className="prop__rv-label">Void</span><span className="prop__rv-value">{m.air_pct.toFixed(0)}%</span></div>
                  <div className="prop__rv-row"><span className="prop__rv-label">Total weight</span><span className="prop__rv-value">{m.total_weight_kg.toFixed(2)} kg</span></div>
                </div>
              </>
            ) : (
              <p className="prop__rv-no-result">Ningún contenedor compatible.</p>
            )}
          </div>
          <div className="prop__rv-render">
            {html ? (
              <iframe className="prop__rv-iframe" srcDoc={html} title={`Render ${size.name}`} sandbox="allow-scripts" />
            ) : (
              <div className="prop__rv-no-render">Render no disponible</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const TABLE_ROWS: { label: string; unit: string; field: keyof SizeRow; integer?: boolean; placeholder: string }[] = [
  { label: 'Ancho',           unit: 'cm',  field: 'width',   placeholder: '0'   },
  { label: 'Alto',            unit: 'cm',  field: 'height',  placeholder: '0'   },
  { label: 'Largo',           unit: 'cm',  field: 'length',  placeholder: '0'   },
  { label: 'Peso',            unit: 'kg',  field: 'weight',  placeholder: '0'   },
  { label: 'Uds. por caja',   unit: 'uds', field: 'lotSize', integer: true, placeholder: '0' },
];

// â”€â”€ Page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const ProposalPage: React.FC = () => {
  const token = useAuthStore((s) => s.token)!;
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const productId = searchParams.get('product_id') ?? '';

  // State passed from ProposalResultPage when clicking "Editar"
  const editState = (location.state ?? {}) as {
    prefill?: Record<string, SizeRow>;
    wallThickness?: string;
    existingIds?: Record<string, string>;
  };

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loadingProduct, setLoadingProduct] = useState(true);
  const [productError, setProductError] = useState('');

  const [rows, setRows] = useState<Record<string, SizeRow>>({});
  const [wallThickness, setWallThickness] = useState(editState.wallThickness ?? '3');
  const [existingIds] = useState<Record<string, string>>(editState.existingIds ?? {});

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const dragPayload = useRef<DragPayload | null>(null);
  const [dragOverCol, setDragOverCol] = useState<string | null>(null);
  const [dragOverCell, setDragOverCell] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) { setProductError('No se indicó producto.'); setLoadingProduct(false); return; }
    setLoadingProduct(true);
    fetchProduct(token, productId)
      .then(async (p) => {
        setProduct(p);
        const init: Record<string, SizeRow> = {};
        // In edit mode, pre-fill rows from the state passed by ProposalResultPage
        p.sizes.forEach((s) => { init[s.id] = editState.prefill?.[s.id] ?? emptyRow(); });
        setRows(init);
      })
      .catch(() => setProductError('No se pudo cargar el producto.'))
      .finally(() => setLoadingProduct(false));
  }, [productId, token]);

  const setCell = (sizeId: string, field: keyof SizeRow, value: string) => {
    setRows((prev) => ({ ...prev, [sizeId]: { ...prev[sizeId], [field]: value } }));
  };

  const filledSizes = useMemo(
    () => (product?.sizes ?? []).filter((s) => rows[s.id] && rowFilled(rows[s.id])),
    [rows, product],
  );

  const canSubmit = filledSizes.length > 0 && !submitting;

  const copyColumn = (fromId: string, toId: string) => {
    setRows(prev => ({ ...prev, [toId]: { ...prev[fromId] } }));
  };

  const handleSubmit = () => {
    if (!canSubmit || !productId) return;
    setSubmitting(true);
    setSubmitError('');
    const wall = parseFloat(wallThickness) || 0;
    Promise.allSettled(
      filledSizes.map((s) => {
        const r = rows[s.id];
        const body: ProposalCreateBody = {
          product_id: productId,
          size_id: s.id,
          article_dims: {
            length_cm: parseFloat(r.length),
            width_cm:  parseFloat(r.width),
            height_cm: parseFloat(r.height),
            weight_kg: parseFloat(r.weight),
          },
          lot_size: parseInt(r.lotSize),
          inner_wall_thickness_mm: wall,
        };
        const existingId = existingIds[s.id];
        if (existingId) {
          return recalculateProposal(token, existingId, body).then((res) => ({ sizeId: s.id, res }));
        }
        return submitProposal(token, body).then((res) => ({ sizeId: s.id, res }));
      }),
    ).then((settled) => {
      const map: Record<string, ProposalResult | { error: string }> = {};
      settled.forEach((s, i) => {
        const sizeId = filledSizes[i].id;
        if (s.status === 'fulfilled') map[sizeId] = s.value.res;
        else map[sizeId] = { error: (s.reason as Error)?.message ?? 'Error desconocido' };
      });
      navigate('/proposals/result', {
        state: {
          results: map,
          sizes: filledSizes,
          productName: product?.name ?? '',
          productId,
        },
      });
    }).finally(() => setSubmitting(false));
  };

  const sizes = product?.sizes ?? [];

  return (
    <AppShell>
      <div className="prop__page">

        {/* â”€â”€ Title row â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        <div className="prop__titleRow">
          <div className="prop__titleLeft">
            <h2 className="prop__title">MEDIDAS DEL ARTÍCULO</h2>
            {product && (
              <p className="prop__subtitle">
                {product.name.toUpperCase()} &middot; {product.family.name} &middot; {product.subfamily.name}
              </p>
            )}
            {loadingProduct && <span className="prop__hint">Cargando producto...</span>}
            {productError  && <span className="prop__hint prop__hint--err">{productError}</span>}
          </div>
          <div className="prop__titleActions">
            <button className="btn btn--ghost btn--sm" onClick={() => navigate('/manufacturer')}>Volver</button>
            <button className="btn btn--sm" onClick={handleSubmit} disabled={!canSubmit}>
              {submitting ? 'Calculando...' : Object.keys(existingIds).length > 0 ? 'Actualizar propuesta' : 'Generar propuesta'}
            </button>
          </div>
        </div>

        <div className="prop__body">
          <div className="prop__sideImages">
            <div className="prop__imgItem">
              <img src="/sub-box.svg" className="prop__img" alt="Artículo empaquetado" />
              <span className="prop__imgLabel">Artículo empaquetado</span>
            </div>
            <div className="prop__imgItem">
              <img src="/POLYBAG.svg" className="prop__img" alt="Polybag" />
              <span className="prop__imgLabel">Polybag</span>
            </div>
          </div>

          <div className="prop__mainContent">
            {submitError && <p className="prop__submit-error">{submitError}</p>}

        {/* â”€â”€ Measurements table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        {product && sizes.length > 0 && (
          <div className="prop__tableWrap">
            <p className="prop__hint">Medidas del artículo empaquetado o embolsado. Si el artículo no tiene embalaje propio, introduce las medidas del propio artículo. Si el artículo no lleva cartón, deja el grosor a 0.</p>
            <div className="prop__hint-tags">
              <span className="containerDetail__dim">Dimensiones en cm</span>
              <span className="containerDetail__dim">Peso en kg</span>
            </div>

            <table className="prop__table">
              <thead>
                <tr>
                  <th className="prop__th prop__th--label" />
                  {sizes.map((s) => (
                    <th
                      key={s.id}
                      className={`prop__th${dragOverCol === s.id ? ' prop__th--drag-over' : ''}`}
                      draggable
                      title="Arrastra para copiar esta talla a otra"
                      onDragStart={(e) => { e.dataTransfer.effectAllowed = 'copy'; dragPayload.current = { type: 'column', sizeId: s.id }; }}
                      onDragOver={(e) => { e.preventDefault(); setDragOverCol(s.id); }}
                      onDragLeave={() => setDragOverCol(null)}
                      onDrop={(e) => {
                        e.preventDefault();
                        const drag = dragPayload.current;
                        if (drag?.type === 'column' && drag.sizeId !== s.id) copyColumn(drag.sizeId, s.id);
                        setDragOverCol(null);
                      }}
                    >
                      {s.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {TABLE_ROWS.map((row) => (
                  <tr key={row.field} className="prop__tr">
                    <td className="prop__td prop__td--label">
                      {row.label}
                    </td>
                    {sizes.map((s) => (
                      <td
                        key={s.id}
                        className={`prop__td${dragOverCell === `${s.id}:${row.field}` ? ' prop__td--drag-over' : ''}`}
                        draggable
                        onDragStart={(e) => { e.dataTransfer.effectAllowed = 'copy'; dragPayload.current = { type: 'cell', field: row.field, sizeId: s.id }; }}
                        onDragOver={(e) => { e.preventDefault(); setDragOverCell(`${s.id}:${row.field}`); }}
                        onDragLeave={() => setDragOverCell(null)}
                        onDrop={(e) => {
                          e.preventDefault();
                          const drag = dragPayload.current;
                          if (!drag) return;
                          if (drag.type === 'cell') {
                            setCell(s.id, row.field, rows[drag.sizeId]?.[drag.field] ?? '');
                          } else if (drag.type === 'column') {
                            copyColumn(drag.sizeId, s.id);
                          }
                          setDragOverCell(null);
                        }}
                      >
                        <CellInput
                          value={rows[s.id]?.[row.field] ?? ''}
                          onChange={(v) => setCell(s.id, row.field, v)}
                          placeholder={row.placeholder}
                          integer={row.integer}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
                <tr className="prop__tr--wall">
                  <td className="prop__td--wall-full" colSpan={1 + sizes.length}>
                    <div className="prop__wall-row">
                      <span className="prop__wall-label">Grosor cartón</span>
                      <input
                        className="prop__wall-input"
                        type="text"
                        inputMode="decimal"
                        value={wallThickness}
                        onChange={(e) => {
                          const v = e.target.value.replace(',', '.');
                          if (/^\d*\.?\d*$/.test(v)) setWallThickness(v);
                        }}
                      />
                      <span className="prop__wall-hint">mm &middot; aplica a todas las tallas</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* â”€â”€ Results â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        {/* results are now shown in ProposalResultPage after navigation */}

          </div> {/* prop__mainContent */}
        </div> {/* prop__body */}

      </div>
    </AppShell>
  );
};

export default ProposalPage;
