import { useState, useEffect } from 'react';
import { getComplianceFrameworks, getFrameworkControls, updateComplianceControl, seedFrameworks } from '../services/api';

const STATUS_CONFIG = {
  compliant: { label: 'Compliant', color: 'ok' },
  non_compliant: { label: 'Non-Compliant', color: 'critical' },
  in_progress: { label: 'In Progress', color: 'warning' },
  not_started: { label: 'Not Started', color: '' },
  not_applicable: { label: 'N/A', color: '' },
};

export default function Compliance() {
  const [frameworks, setFrameworks] = useState([]);
  const [selectedFw, setSelectedFw] = useState(null);
  const [controls, setControls] = useState([]);
  const [filterStatus, setFilterStatus] = useState('all');
  const [editControl, setEditControl] = useState(null);
  const [msg, setMsg] = useState('');

  const loadFrameworks = () => getComplianceFrameworks().then(r => setFrameworks(r.data || [])).catch(() => {});
  useEffect(() => { loadFrameworks(); }, []);

  const loadControls = (fwId) => {
    setSelectedFw(fwId);
    getFrameworkControls(fwId).then(r => setControls(r.data?.controls || [])).catch(() => {});
  };

  const handleSeed = async () => {
    await seedFrameworks();
    loadFrameworks();
    setMsg('Frameworks seeded');
    setTimeout(() => setMsg(''), 3000);
  };

  const handleUpdateControl = async (controlId, data) => {
    await updateComplianceControl(controlId, data);
    if (selectedFw) loadControls(selectedFw);
    loadFrameworks();
  };

  const filtered = filterStatus === 'all' ? controls : controls.filter(c => c.status === filterStatus);

  return (
    <div>
      <div className="page-header">
        <h2>Compliance</h2>
        {frameworks.length === 0 && (
          <button onClick={handleSeed} className="btn btn-primary">Seed SOC 2 & GDPR Frameworks</button>
        )}
      </div>

      {msg && <div className="error-message" style={{ background: '#f0fff4', color: 'var(--color-status-ok)', marginBottom: '16px' }}>{msg}</div>}

      {/* Framework Overview Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: `repeat(${Math.min(frameworks.length || 1, 3)}, 1fr)` }}>
        {frameworks.map(f => (
          <div key={f.id} className="card" style={{ cursor: 'pointer', border: selectedFw === f.id ? '2px solid var(--color-primary)' : undefined }} onClick={() => loadControls(f.id)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700 }}>{f.name}</h3>
              <span style={{ fontSize: '24px', fontWeight: 800, color: f.compliance_pct >= 80 ? 'var(--color-status-ok)' : f.compliance_pct >= 50 ? 'var(--color-status-warning)' : 'var(--color-status-critical)' }}>{f.compliance_pct}%</span>
            </div>
            <div style={{ background: 'var(--color-bg)', borderRadius: '8px', height: '8px', overflow: 'hidden', marginBottom: '12px' }}>
              <div style={{ height: '100%', width: `${f.compliance_pct}%`, background: f.compliance_pct >= 80 ? 'var(--color-status-ok)' : f.compliance_pct >= 50 ? 'var(--color-status-warning)' : 'var(--color-status-critical)', borderRadius: '8px', transition: 'width 0.5s' }} />
            </div>
            <div style={{ display: 'flex', gap: '12px', fontSize: '12px' }}>
              <span><strong style={{ color: 'var(--color-status-ok)' }}>{f.compliant}</strong> Compliant</span>
              <span><strong style={{ color: 'var(--color-status-critical)' }}>{f.non_compliant}</strong> Non-Compliant</span>
              <span><strong style={{ color: 'var(--color-status-warning)' }}>{f.in_progress}</strong> In Progress</span>
              <span><strong>{f.not_started}</strong> Not Started</span>
            </div>
          </div>
        ))}
      </div>

      {/* Controls Table */}
      {selectedFw && (
        <div className="card">
          <div className="card-header">
            <h3>Controls</h3>
            <div style={{ display: 'flex', gap: '6px' }}>
              {['all', 'not_started', 'in_progress', 'non_compliant', 'compliant', 'not_applicable'].map(s => (
                <button key={s} className={`btn ${filterStatus === s ? 'btn-primary' : 'btn-outline'}`} style={{ padding: '3px 10px', fontSize: '11px' }} onClick={() => setFilterStatus(s)}>
                  {s === 'all' ? 'All' : (STATUS_CONFIG[s]?.label || s)}
                </button>
              ))}
            </div>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr><th>ID</th><th>Category</th><th>Control</th><th>Type</th><th>Status</th><th>Assigned</th><th>Action</th></tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{c.control_id}</td>
                    <td style={{ fontSize: '12px' }}>{c.category}</td>
                    <td>
                      <div style={{ fontWeight: 500, fontSize: '13px' }}>{c.title}</div>
                      {c.description && <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{c.description}</div>}
                      {c.evidence && (
                        <div style={{ fontSize: '11px', marginTop: '4px', padding: '6px 8px', borderRadius: '4px', background: c.evidence.includes('FAIL') ? '#fef2f220' : '#ecfdf520', border: `1px solid ${c.evidence.includes('FAIL') ? '#fecaca' : '#a7f3d0'}` }}>
                          {c.evidence.split('\n').map((line, i) => (
                            <div key={i} style={{ color: line.startsWith('PASS') ? 'var(--color-status-ok)' : line.startsWith('FAIL') ? 'var(--color-status-critical)' : 'var(--color-text-secondary)' }}>
                              {line.startsWith('PASS') ? '\u2713 ' : line.startsWith('FAIL') ? '\u2717 ' : ''}{line}
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                    <td><span className={`badge ${c.check_type === 'automated' ? 'badge-ok' : ''}`} style={{ fontSize: '10px' }}>{c.check_type}</span></td>
                    <td>
                      <select value={c.status} onChange={(e) => handleUpdateControl(c.id, { status: e.target.value })} style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '6px', border: '1px solid var(--color-border)' }}>
                        <option value="not_started">Not Started</option>
                        <option value="in_progress">In Progress</option>
                        <option value="compliant">Compliant</option>
                        <option value="non_compliant">Non-Compliant</option>
                        <option value="not_applicable">N/A</option>
                      </select>
                    </td>
                    <td style={{ fontSize: '12px' }}>{c.assigned_to || '—'}</td>
                    <td>
                      <button onClick={() => setEditControl(c)} className="btn btn-outline" style={{ padding: '3px 8px', fontSize: '10px' }}>Details</button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && <tr><td colSpan="7" style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-secondary)' }}>No controls match this filter</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Control Modal */}
      {editControl && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: 'var(--radius-lg)', padding: '28px', width: '100%', maxWidth: '500px', boxShadow: 'var(--shadow-xl)' }}>
            <h3 style={{ marginBottom: '4px' }}>{editControl.control_id} — {editControl.title}</h3>
            <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>{editControl.category}</p>
            <div className="form-group">
              <label>Status</label>
              <select value={editControl.status} onChange={(e) => setEditControl({ ...editControl, status: e.target.value })}>
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="compliant">Compliant</option>
                <option value="non_compliant">Non-Compliant</option>
                <option value="not_applicable">N/A</option>
              </select>
            </div>
            <div className="form-group">
              <label>Evidence / Notes</label>
              <textarea rows="3" value={editControl.evidence || ''} onChange={(e) => setEditControl({ ...editControl, evidence: e.target.value })} placeholder="Document evidence or implementation notes..." />
            </div>
            <div className="form-group">
              <label>Assigned To</label>
              <input value={editControl.assigned_to || ''} onChange={(e) => setEditControl({ ...editControl, assigned_to: e.target.value })} placeholder="team@company.com" />
            </div>
            <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
              <button onClick={async () => {
                await handleUpdateControl(editControl.id, { status: editControl.status, evidence: editControl.evidence, assigned_to: editControl.assigned_to });
                setEditControl(null);
              }} className="btn btn-primary">Save</button>
              <button onClick={() => setEditControl(null)} className="btn btn-outline">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
