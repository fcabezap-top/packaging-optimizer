import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AppShell from '../../components/layout/AppShell';
import { useAuthStore } from '../../store/auth';
import {
  type ProposalResult,
  fetchProposalRenderHtml,
  fetchProductProposals,
  updateProposalStatus,
} from '../../api/optimization';
import { fetchProduct, type ProductSize } from '../../api/product';
import pdfIcon from '../../assets/pdf-file.png';
import '../containers/containers.css';
import './proposals.css';

type SizeRow = { length: string; width: string; height: string; weight: string; lotSize: string };

// ── Types ─────────────────────────────────────────────────────────────────────
interface LocationState {
  // Full data path (after submitting new proposal)
  results?: Record<string, ProposalResult | { error: string }>;
  sizes?: ProductSize[];
  // Light path (navigating directly from product list)
  productName?: string;
  productId?: string;
}

// ── ProposalResultPage ────────────────────────────────────────────────────────
const ProposalResultPage: React.FC = () => {
  const token = useAuthStore((s) => s.token)!;
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as Partial<LocationState>;

  const productId   = state.productId  ?? '';
  const productName = state.productName ?? '';

  // Results & sizes can come from location state (new proposal flow) or be fetched (view existing)
  const [sizes,   setSizes]   = useState<ProductSize[]>(state.sizes ?? []);
  const [results, setResults] = useState<Record<string, ProposalResult | { error: string }>>(state.results ?? {});
  const [initialLoading, setInitialLoading] = useState(!state.results || Object.keys(state.results).length === 0);
  const [initialError,   setInitialError]   = useState('');

  const [activeIdx, setActiveIdx] = useState(0);
  const [renderHtmlMap, setRenderHtmlMap] = useState<Record<string, string>>({});
  const fetchingRef = useRef<Set<string>>(new Set());
  const [iframeReadyMap, setIframeReadyMap] = useState<Record<string, boolean>>({});
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [pdfLoading, setPdfLoading] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showAcceptModal, setShowAcceptModal] = useState(false);
  const [pdfDownloaded, setPdfDownloaded] = useState(false);

  // Initial data load when navigating from product list (no results in state)
  useEffect(() => {
    if (!initialLoading) return;
    if (!productId) { setInitialLoading(false); return; }
    Promise.all([
      fetchProduct(token, productId),
      fetchProductProposals(token, productId),
    ])
      .then(([product, proposals]) => {
        const map: Record<string, ProposalResult | { error: string }> = {};
        proposals.forEach((r) => { map[r.size_id] = r; });
        setSizes(product.sizes.filter((s) => map[s.id]));
        setResults(map);
      })
      .catch(() => setInitialError('No se pudieron cargar las propuestas.'))
      .finally(() => setInitialLoading(false));
  }, []);

  // If no state (browser refresh or empty product), go back to manufacturer
  useEffect(() => {
    if (initialLoading) return;
    if (!initialError && validSizes.length === 0) navigate('/manufacturer', { replace: true });
  }, [initialLoading]);

  const validSizes = sizes.filter((s) => results[s.id]);

  // Fetch render for active size
  useEffect(() => {
    const size = validSizes[activeIdx];
    if (!size) return;
    const res = results[size.id];
    if (!res || 'error' in res) return;
    const proposal = res as ProposalResult;
    if (fetchingRef.current.has(proposal.id) || proposal.id in renderHtmlMap) return;
    fetchingRef.current.add(proposal.id);
    fetchProposalRenderHtml(token, proposal.id)
      .then((html) => setRenderHtmlMap((p) => ({ ...p, [proposal.id]: html })))
      .catch(() => setRenderHtmlMap((p) => ({ ...p, [proposal.id]: '' })));
  }, [activeIdx, token, results]);

  const size = validSizes[activeIdx];
  const currentResult = size ? results[size.id] : null;
  const proposal = currentResult && !('error' in currentResult) ? (currentResult as ProposalResult) : null;
  const m  = proposal?.selected_master ?? null;
  const ib = proposal?.inner_box ?? null;
  const noMatch = proposal != null && (m === null || m.accepted === false);
  // If ANY size has no valid match, block accept/reject/pdf for the whole proposal
  const anyNoMatch = validSizes.some((s) => {
    const r = results[s.id];
    if (!r || 'error' in r) return false;
    const sm = (r as ProposalResult).selected_master;
    return sm === null || sm.accepted === false;
  });
  const renderHtml = proposal ? (renderHtmlMap[proposal.id] ?? null) : null;
  const isIframeReady = proposal ? (iframeReadyMap[proposal.id] ?? false) : false;
  // Spinner while: HTML not yet received, OR HTML received but iframe not yet painted
  const showSpinner = proposal != null && (renderHtml === null || (renderHtml !== '' && !isIframeReady));

  const proposalIds = validSizes
    .map((s) => results[s.id])
    .filter((r): r is ProposalResult => !!r && !('error' in r))
    .map((r) => r.id);

  // Derive overall status from all size proposals
  const allProposals = validSizes
    .map((s) => results[s.id])
    .filter((r): r is ProposalResult => !!r && !('error' in r)) as ProposalResult[];
  const isRejected = allProposals.length > 0 && allProposals.every((p) => p.status === 'rejected');
  const isAccepted = allProposals.length > 0 && allProposals.some((p) => p.status === 'accepted');

  const anyPdf = !anyNoMatch && validSizes.some((s) => {
    const r = results[s.id];
    return r && !('error' in r) && (r as ProposalResult).pdf_b64;
  });

  const handleDownloadPdf = async () => {
    const pdfs = validSizes
      .map((s) => results[s.id])
      .filter((r): r is ProposalResult => !!r && !('error' in r))
      .map((r) => (r as ProposalResult).pdf_b64)
      .filter(Boolean) as string[];
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
          pages.forEach((p: import('pdf-lib').PDFPage) => merged.addPage(p));
        }
        const saved = await merged.save();
        const blob = new Blob([saved], { type: 'application/pdf' });
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

  const handleAccept = async () => {
    if (!proposalIds.length) return;
    setActionLoading(true);
    setActionError('');
    try {
      await Promise.all(proposalIds.map((id) => updateProposalStatus(token, id, 'accepted')));
      navigate('/manufacturer');
    } catch (e) {
      setActionError((e as Error).message ?? 'Error al aceptar');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!proposalIds.length) return;
    setActionLoading(true);
    setActionError('');
    try {
      await Promise.all(
        proposalIds.map((id) => updateProposalStatus(token, id, 'rejected')),
      );
      navigate('/manufacturer');
    } catch (e) {
      setActionError((e as Error).message ?? 'Error al rechazar');
    } finally {
      setActionLoading(false);
      setShowRejectModal(false);
    }
  };

  return (
    <AppShell>
      {initialLoading ? (
        <div className="prop__page-loader">
          <div className="prop__rv-spinner" />
        </div>
      ) : initialError ? (
        <div className="prop__page-loader">
          <p style={{ color: '#dc2626' }}>{initialError}</p>
        </div>
      ) : (
      <div className="prop__page" style={{ gap: 'var(--size-1)' }}>

        {/* ── Title row ───────────────────────────────────────────────────── */}
        <div className="prop__titleRow" style={{ paddingBottom: 0 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--size-4)' }}>
              <h2 className="containerDetail__name">{productName.toUpperCase()}</h2>
              {(isAccepted || isRejected) && (
                <span style={{ fontSize: 'var(--font-size-s)', fontWeight: 700, letterSpacing: '0.05em', color: isAccepted ? '#16a34a' : '#dc2626' }}>
                  {isAccepted ? 'ACEPTADO' : 'RECHAZADO'}
                </span>
              )}
            </div>
            <p className="containerDetail__desc">
              {'Propuesta de embalaje'}
              {proposal?.selected_master?.container_priority != null && !noMatch
                ? ` · Prioridad ${proposal.selected_master.container_priority}`
                : ''}
            </p>
          </div>

          <div className="prop__titleActions" style={{ alignSelf: 'flex-start' }}>
            {!isRejected && !isAccepted && (
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  const prefill: Record<string, SizeRow> = {};
                  const existingIds: Record<string, string> = {};
                  let wall = '3';
                  validSizes.forEach((s) => {
                    const res = results[s.id];
                    if (res && !('error' in res)) {
                      const p = res as ProposalResult;
                      existingIds[s.id] = p.id;
                      prefill[s.id] = {
                        length: String(p.article_dims?.length_cm ?? ''),
                        width:  String(p.article_dims?.width_cm ?? ''),
                        height: String(p.article_dims?.height_cm ?? ''),
                        weight: String(p.article_dims?.weight_kg ?? ''),
                        lotSize: String(p.lot_size ?? ''),
                      };
                      if (p.inner_box?.wall_thickness_mm) wall = String(p.inner_box.wall_thickness_mm);
                    }
                  });
                  navigate(`/proposals?product_id=${productId}`, {
                    state: { prefill, wallThickness: wall, existingIds },
                  });
                }}
                disabled={actionLoading}
              >
                Editar
              </button>
            )}
            {anyPdf && (
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => { void handleDownloadPdf(); }}
                disabled={pdfLoading}
              >
                {pdfLoading ? 'Generando...' : 'Descargar PDF'}
              </button>
            )}
            {!isRejected && !isAccepted && (
              <>
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={() => setShowRejectModal(true)}
                  disabled={actionLoading || proposalIds.length === 0 || anyNoMatch}
                >
                  Rechazar
                </button>
                <button
                  className="btn btn--sm"
                  onClick={() => { setPdfDownloaded(false); setShowAcceptModal(true); }}
                  disabled={actionLoading || proposalIds.length === 0 || anyNoMatch}
                >
                  Aceptar
                </button>
              </>
            )}
          </div>
        </div>

        {actionError && <p className="prop__submit-error">{actionError}</p>}

        {/* ── Result view ─────────────────────────────────────────────────── */}
        <div className="prop__rv">

          {/* Tabs */}
          <div className="prop__rv-tabs">
            {validSizes.map((s, i) => (
              <button
                key={s.id}
                className={`prop__rv-tab${i === activeIdx ? ' prop__rv-tab--active' : ''}`}
                onClick={() => setActiveIdx(i)}
              >
                {s.name}
              </button>
            ))}
          </div>

          {/* Body */}
          {currentResult && 'error' in currentResult ? (
            <div className="prop__rv-error">{(currentResult as { error: string }).error}</div>
          ) : (
            <div className="prop__rv-body">

              {/* Left panel */}
              <div className="prop__rv-panel">
                {m ? (
                  <>
                    <div className="prop__rv-section">
                      <p className="prop__rv-section-title">Contenedor</p>
                      <div className="containerDetail__dims">
                        {!noMatch && <span className="containerDetail__dim">{m.container_name}</span>}
                        {m.container_priority != null && !noMatch && (
                          <span className="containerDetail__dim">Prioridad {m.container_priority}</span>
                        )}
                        {m.ext_dims && !noMatch && (
                          <span className="containerDetail__dim">
                            Exterior {m.ext_dims[0]?.toFixed(1)} × {m.ext_dims[1]?.toFixed(1)} × {m.ext_dims[2]?.toFixed(1)} cm
                          </span>
                        )}
                        {m.util_dims && !noMatch && (
                          <span className="containerDetail__dim">
                            Utilizable {m.util_dims[0]?.toFixed(1)} × {m.util_dims[1]?.toFixed(1)} × {m.util_dims[2]?.toFixed(1)} cm
                          </span>
                        )}
                        {m.grid && !noMatch && (
                          <span className="containerDetail__dim">
                            Grid {m.grid[0]} × {m.grid[1]} × {m.grid[2]}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="prop__rv-section">
                      <p className="prop__rv-section-title">Caja interior</p>
                      <div className="containerDetail__dims">
                        {ib && !noMatch && (
                          <>
                            <span className="containerDetail__dim">
                              Inner ext. {ib.ext_max_cm.toFixed(1)} × {ib.ext_med_cm.toFixed(1)} × {ib.ext_min_cm.toFixed(1)} cm
                            </span>
                            <span className="containerDetail__dim">
                              Inner int. {ib.int_max_cm.toFixed(1)} × {ib.int_med_cm.toFixed(1)} × {ib.int_min_cm.toFixed(1)} cm
                            </span>
                            <span className="containerDetail__dim">Pared {ib.wall_thickness_mm} mm</span>
                          </>
                        )}
                        {!noMatch && <span className="containerDetail__dim">Uds./inner {proposal?.lot_size}</span>}
                        {!noMatch && <span className="containerDetail__dim">Inners/master {m.inners_used}</span>}
                      </div>
                    </div>

                    <div className="prop__rv-section">
                      <p className="prop__rv-section-title">Métricas</p>
                      <div className="containerDetail__dims">
                        {!noMatch && <span className="containerDetail__dim">Total {m.inners_used * (proposal?.lot_size ?? 0)} artículos</span>}
                        {!noMatch && <span className="containerDetail__dim">Ocupación {m.fill_pct.toFixed(1)}%</span>}
                        {!noMatch && <span className="containerDetail__dim">Aire {m.air_pct.toFixed(1)}%</span>}
                        {!noMatch && <span className="containerDetail__dim">Peso {m.total_weight_kg.toFixed(2)} kg</span>}
                      </div>
                    </div>
                  </>
                ) : (
                  <p className="prop__rv-no-result">Ningún contenedor compatible.</p>
                )}
              </div>

              {/* 3D Render */}
              <div className="prop__rv-render">
                {noMatch ? (
                  <div className="prop__rv-no-match">
                    <span className="prop__rv-no-match__icon">⚠</span>
                    <p className="prop__rv-no-match__title">Sin contenedor compatible</p>
                    <p className="prop__rv-no-match__body">
                      Las dimensiones o el peso introducidos no se ajustan a ningún contenedor
                      de nuestra normativa logística. Por favor, contacte con soporte o
                      modifique las medidas introducidas.
                    </p>
                  </div>
                ) : (
                  <>
                    {showSpinner && (
                      <div className="prop__rv-spinner-wrap">
                        <div className="prop__rv-spinner" />
                      </div>
                    )}
                    {renderHtml && renderHtml !== '' ? (
                      <iframe
                        className="prop__rv-iframe"
                        style={{ opacity: isIframeReady ? 1 : 0 }}
                        srcDoc={renderHtml}
                        title={`Render ${size?.name}`}
                        sandbox="allow-scripts"
                        onLoad={() => setIframeReadyMap((p) => ({ ...p, [proposal!.id]: true }))}
                      />
                    ) : renderHtml === '' ? (
                      <div className="prop__rv-no-render">Render no disponible</div>
                    ) : null}
                  </>
                )}
              </div>

            </div>
          )}
        </div>

      </div>
    )}

    {/* ── Reject modal ──────────────────────────────────────────────────── */}
    {showRejectModal && (
      <div className="propModal" onClick={() => setShowRejectModal(false)}>
        <div className="propModal__dialog" onClick={(e) => e.stopPropagation()}>
          <h3 className="propModal__title">Rechazar propuesta</h3>
          <p className="propModal__body">
            Esta acción <strong>no se puede deshacer</strong>. Solo se debe utilizar el rechazo
            cuando la propuesta no se adapte al producto por motivos excepcionales.
            La incidencia se gestionará directamente con oficina técnica.
          </p>
          <div className="propModal__actions">
            <button
              className="btn btn--ghost btn--sm"
              onClick={() => setShowRejectModal(false)}
              disabled={actionLoading}
            >
              Cancelar
            </button>
            <button
              className="btn btn--danger btn--sm"
              onClick={() => { void handleReject(); }}
              disabled={actionLoading}
            >
              {actionLoading ? 'Rechazando...' : 'Confirmar rechazo'}
            </button>
          </div>
        </div>
      </div>
    )}

    {/* ── Accept modal ──────────────────────────────────────────────────── */}
    {showAcceptModal && (
      <div className="propModal" onClick={() => setShowAcceptModal(false)}>
        <div className="propModal__dialog" onClick={(e) => e.stopPropagation()}>
          <h3 className="propModal__title">Aceptar propuesta</h3>
          <p className="propModal__body">
            Esta acción <strong>no se puede deshacer</strong>. La aceptación de la propuesta
            es <strong>vinculante</strong>. Se comprobará que las medidas son las especificadas
            en la entrada al almacén.
          </p>
          <div className="propModal__pdf">
            <img src={pdfIcon} alt="PDF" className="propModal__pdf-icon" />
            <button
              className="propModal__pdf-download"
              onClick={() => { void handleDownloadPdf(); setPdfDownloaded(true); }}
            >
              Descargar propuesta
            </button>
          </div>
          <div className="propModal__actions">
            <button
              className="btn btn--ghost btn--sm"
              onClick={() => setShowAcceptModal(false)}
              disabled={actionLoading}
            >
              Cancelar
            </button>
            <button
              className="btn btn--sm"
              onClick={() => { void handleAccept(); setShowAcceptModal(false); }}
              disabled={actionLoading || !pdfDownloaded}
              title={!pdfDownloaded ? 'Descarga primero el PDF para continuar' : undefined}
            >
              {actionLoading ? 'Guardando...' : 'Confirmar aceptación'}
            </button>
          </div>
        </div>
      </div>
    )}

  </AppShell>
  );
};

export default ProposalResultPage;
