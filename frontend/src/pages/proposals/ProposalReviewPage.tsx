import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AppShell from '../../components/layout/AppShell';
import { useAuthStore } from '../../store/auth';
import {
  type ProposalResult,
  fetchProductProposals,
  fetchProposalRenderHtml,
} from '../../api/optimization';
import { fetchProduct, type ProductSize } from '../../api/product';
import '../containers/containers.css';
import './proposals.css';

interface LocationState {
  productId?: string;
  productName?: string;
}

const ProposalReviewPage: React.FC = () => {
  const token = useAuthStore((s) => s.token)!;
  const navigate = useNavigate();
  const { state } = useLocation();
  const { productId, productName: initName } = (state ?? {}) as LocationState;

  const [productName, setProductName] = useState(initName ?? '');
  const [productSubtitle, setProductSubtitle] = useState('');
  const [productSizes, setProductSizes] = useState<ProductSize[]>([]);
  const [proposals, setProposals] = useState<ProposalResult[]>([]);
  const [activeSizeId, setActiveSizeId] = useState<string | null>(null);
  const [renderHtmlMap, setRenderHtmlMap] = useState<Record<string, string>>({});
  const [renderReadyMap, setRenderReadyMap] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [pdfLoading, setPdfLoading] = useState(false);
  const fetchingRef = useRef<Set<string>>(new Set());

  // Load proposals + product name
  useEffect(() => {
    if (!productId) { navigate('/product', { replace: true }); return; }
    Promise.all([
      fetchProductProposals(token, productId),
      fetchProduct(token, productId),
    ])
      .then(([props, product]) => {
        // Only show non-pending proposals (accepted or rejected)
        const resolved = props.filter((p) => p.status === 'accepted' || p.status === 'rejected');
        setProposals(resolved);
        setProductName(product.name);
        setProductSizes(product.sizes);
        const parts = [product.family?.name, product.subfamily?.name].filter(Boolean);
        setProductSubtitle(parts.join(' · '));
        if (resolved.length > 0) setActiveSizeId(resolved[0].size_id);
      })
      .catch(() => setError('No se pudieron cargar las propuestas.'))
      .finally(() => setLoading(false));
  }, [productId, token]);

  // Fetch render for active proposal
  const activeProposal = proposals.find((p) => p.size_id === activeSizeId);

  // Reset iframe ready state whenever tab changes so spinner shows during reload
  useEffect(() => {
    if (activeProposal) {
      setRenderReadyMap((prev) => ({ ...prev, [activeProposal.id]: false }));
    }
  }, [activeSizeId]);

  useEffect(() => {
    if (!activeProposal) return;
    if (fetchingRef.current.has(activeProposal.id) || activeProposal.id in renderHtmlMap) return;
    fetchingRef.current.add(activeProposal.id);
    fetchProposalRenderHtml(token, activeProposal.id)
      .then((html) => setRenderHtmlMap((prev) => ({ ...prev, [activeProposal.id]: html })))
      .catch(() => setRenderHtmlMap((prev) => ({ ...prev, [activeProposal.id]: '' })));
  }, [activeProposal, token]);

  const m = activeProposal?.selected_master ?? null;
  const ib = activeProposal?.inner_box ?? null;
  const renderHtml = activeProposal ? (renderHtmlMap[activeProposal.id] ?? null) : null;
  const renderReady = activeProposal ? (renderReadyMap[activeProposal.id] ?? false) : false;

  const hasPdf = proposals.some((p) => p.pdf_b64);

  const handleDownloadPdf = async () => {
    const pdfs = proposals.map((p) => p.pdf_b64).filter(Boolean) as string[];
    if (!pdfs.length) return;
    setPdfLoading(true);
    try {
      if (pdfs.length === 1) {
        const link = document.createElement('a');
        link.href = `data:application/pdf;base64,${pdfs[0]}`;
        link.download = `propuesta-${productName ?? 'packaging'}.pdf`;
        link.click();
      } else {
        const { PDFDocument } = await import('pdf-lib');
        const merged = await PDFDocument.create();
        for (const b64 of pdfs) {
          const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
          const doc = await PDFDocument.load(bytes);
          const pages = await merged.copyPages(doc, doc.getPageIndices());
          pages.forEach((p) => merged.addPage(p));
        }
        const saved = await merged.save();
        const blob = new Blob([saved as unknown as Uint8Array<ArrayBuffer>], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `propuesta-${productName ?? 'packaging'}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } finally {
      setPdfLoading(false);
    }
  };

  const statusColor = activeProposal?.status === 'accepted' ? '#16a34a' : '#dc2626';
  const statusLabel = activeProposal?.status === 'accepted' ? 'ACEPTADO' : 'RECHAZADO';

  return (
    <AppShell>
      <div className="containerDetail">
        {/* ── Header ───────────────────────────────────────────────────── */}
        <div className="containerDetail__header">
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--size-4)' }}>
            <h2 className="containerDetail__name">{productName.toUpperCase()}</h2>
            {activeProposal && (
              <span style={{ fontSize: 'var(--font-size-s)', fontWeight: 700, letterSpacing: '0.05em', color: statusColor }}>
                {statusLabel}
              </span>
            )}
          </div>
          {productSubtitle && (
            <p className="containerDetail__desc">{productSubtitle}</p>
          )}
          <div className="containerDetail__actions">
            {hasPdf && (
              <button className="btn btn--ghost btn--sm" onClick={() => { void handleDownloadPdf(); }} disabled={pdfLoading}>
                {pdfLoading ? 'Generando...' : 'Descargar PDF'}
              </button>
            )}
            <button className="btn btn--ghost btn--sm" onClick={() => navigate('/product')}>
              Volver
            </button>
          </div>
        </div>

        {loading && <p style={{ color: 'var(--color-content-3)', fontSize: 'var(--font-size-s)' }}>Cargando...</p>}
        {error && <p style={{ color: '#dc2626', fontSize: 'var(--font-size-s)' }}>{error}</p>}

        {/* ── Size tabs ────────────────────────────────────────────────── */}
        {proposals.length > 0 && (
          <div className="prop__rv-tabs">
            {proposals.map((p) => {
              const sizeName = productSizes.find((s) => s.id === p.size_id)?.name ?? p.size_id;
              return (
                <button
                  key={p.size_id}
                  className={`prop__rv-tab${p.size_id === activeSizeId ? ' prop__rv-tab--active' : ''}`}
                  onClick={() => setActiveSizeId(p.size_id)}
                >
                  {sizeName}
                </button>
              );
            })}
          </div>
        )}

        {/* ── Chips ────────────────────────────────────────────────────── */}
        {m && (
          <div className="containerDetail__dims" style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--size-4)' }}>
            <span className="containerDetail__dim">{m.container_name}</span>
            {m.container_priority != null && (
              <span className="containerDetail__dim">Prioridad {m.container_priority}</span>
            )}
            {m.ext_dims && (
              <span className="containerDetail__dim">
                Exterior {m.ext_dims[0]?.toFixed(1)} × {m.ext_dims[1]?.toFixed(1)} × {m.ext_dims[2]?.toFixed(1)} cm
              </span>
            )}
            {m.util_dims && (
              <span className="containerDetail__dim">
                Utilizable {m.util_dims[0]?.toFixed(1)} × {m.util_dims[1]?.toFixed(1)} × {m.util_dims[2]?.toFixed(1)} cm
              </span>
            )}
            {m.grid && (
              <span className="containerDetail__dim">
                Grid {m.grid[0]} × {m.grid[1]} × {m.grid[2]}
              </span>
            )}
            {ib && (
              <span className="containerDetail__dim">
                Inner {ib.ext_max_cm.toFixed(1)} × {ib.ext_med_cm.toFixed(1)} × {ib.ext_min_cm.toFixed(1)} cm
              </span>
            )}
            {activeProposal?.lot_size != null && (
              <span className="containerDetail__dim">Uds./inner {activeProposal.lot_size}</span>
            )}
            {m.inners_used != null && (
              <span className="containerDetail__dim">Inners/master {m.inners_used}</span>
            )}
            {m.inners_used != null && activeProposal?.lot_size != null && (
              <span className="containerDetail__dim">
                Total artículos {m.inners_used * activeProposal.lot_size}
              </span>
            )}
            <span className="containerDetail__dim">Ocupación {m.fill_pct.toFixed(1)}%</span>
            <span className="containerDetail__dim">Aire {m.air_pct.toFixed(1)}%</span>
            <span className="containerDetail__dim">Peso {m.total_weight_kg.toFixed(2)} kg</span>
          </div>
        )}

        {/* ── 3D Render ────────────────────────────────────────────────── */}
        <div className="containerDetail__renderWrap">
          {renderHtml === null && activeProposal && (
            <div className="containerDetail__loading">
              <div className="containerDetail__spinner" />
            </div>
          )}
          {renderHtml && renderHtml !== '' && (
            <>
              {!renderReady && (
                <div className="containerDetail__loading" style={{ pointerEvents: 'none' }}>
                  <div className="containerDetail__spinner" />
                </div>
              )}
              <iframe
                className="containerDetail__render"
                style={{ opacity: renderReady ? 1 : 0 }}
                srcDoc={renderHtml}
                title={`Render ${productName}`}
                sandbox="allow-scripts"
                onLoad={() => setRenderReadyMap((prev) => ({ ...prev, [activeProposal!.id]: true }))}
              />
            </>
          )}
          {renderHtml === '' && (
            <p style={{ padding: 'var(--size-6)', color: 'var(--color-content-3)', fontSize: 'var(--font-size-s)' }}>
              Render no disponible
            </p>
          )}
          {!loading && !error && proposals.length === 0 && (
            <p style={{ padding: 'var(--size-6)', color: 'var(--color-content-3)', fontSize: 'var(--font-size-s)' }}>
              No hay propuestas aceptadas o rechazadas para este producto.
            </p>
          )}
        </div>
      </div>
    </AppShell>
  );
};

export default ProposalReviewPage;
