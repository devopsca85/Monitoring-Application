import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getK8sClusters, deleteK8sCluster } from '../services/api';
import { formatCST } from '../services/time';

const PROVIDER_LABELS = { azure: 'Azure AKS', aws: 'AWS EKS', gcp: 'GCP GKE', on_prem: 'On-Premise' };
const ENV_COLORS = { production: 'critical', staging: 'warning', qa: 'ok', development: 'ok' };
const STATUS_COLORS = { healthy: 'ok', degraded: 'warning', critical: 'critical', unknown: 'warning' };

export default function K8sClusters() {
  const [clusters, setClusters] = useState([]);
  const load = () => getK8sClusters().then(r => setClusters(r.data || [])).catch(e => console.error(e));
  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, []);

  return (
    <div>
      <div className="page-header">
        <h2>Kubernetes Clusters</h2>
        <Link to="/k8s/new" className="btn btn-primary">+ Add Cluster</Link>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="stat-card info"><div className="stat-value">{clusters.length}</div><div className="stat-label">Total Clusters</div></div>
        <div className="stat-card ok"><div className="stat-value">{clusters.filter(c => c.status === 'healthy').length}</div><div className="stat-label">Healthy</div></div>
        <div className="stat-card warning"><div className="stat-value">{clusters.filter(c => c.status === 'degraded').length}</div><div className="stat-label">Degraded</div></div>
        <div className="stat-card critical"><div className="stat-value">{clusters.reduce((s, c) => s + (c.active_alerts || 0), 0)}</div><div className="stat-label">Active Alerts</div></div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Cluster</th>
                <th>Provider</th>
                <th>Environment</th>
                <th>Status</th>
                <th>Nodes</th>
                <th>Pods</th>
                <th>CPU</th>
                <th>Memory</th>
                <th>Alerts</th>
                <th>Last Check</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clusters.map(c => (
                <tr key={c.id}>
                  <td><Link to={`/k8s/${c.id}`} style={{ fontWeight: 600 }}>{c.name}</Link><div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{c.k8s_version} {c.region && `| ${c.region}`}</div></td>
                  <td style={{ fontSize: '12px' }}>{PROVIDER_LABELS[c.cloud_provider] || c.cloud_provider}</td>
                  <td><span className={`badge badge-${ENV_COLORS[c.environment] || 'ok'}`} style={{ fontSize: '10px' }}>{c.environment}</span></td>
                  <td><span className={`badge badge-${STATUS_COLORS[c.status] || 'warning'}`}>{c.status}</span></td>
                  <td style={{ fontVariantNumeric: 'tabular-nums' }}>{c.ready_nodes}/{c.total_nodes}</td>
                  <td style={{ fontVariantNumeric: 'tabular-nums' }}>{c.running_pods}/{c.total_pods}{c.failed_pods > 0 && <span style={{ color: 'var(--color-status-critical)', marginLeft: 4 }}>({c.failed_pods} failed)</span>}</td>
                  <td style={{ fontVariantNumeric: 'tabular-nums', color: c.cpu_pct > 85 ? 'var(--color-status-critical)' : c.cpu_pct > 70 ? 'var(--color-status-warning)' : undefined }}>{c.cpu_pct}%</td>
                  <td style={{ fontVariantNumeric: 'tabular-nums', color: c.memory_pct > 85 ? 'var(--color-status-critical)' : c.memory_pct > 70 ? 'var(--color-status-warning)' : undefined }}>{c.memory_pct}%</td>
                  <td>{c.active_alerts > 0 ? <span className="badge badge-critical">{c.active_alerts}</span> : <span style={{ color: 'var(--color-text-secondary)' }}>0</span>}</td>
                  <td style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>{formatCST(c.last_checked)}</td>
                  <td style={{ display: 'flex', gap: '4px' }}>
                    <Link to={`/k8s/${c.id}`} className="btn btn-primary" style={{ padding: '3px 10px', fontSize: '11px' }}>View</Link>
                    <button onClick={() => { if(confirm(`Delete "${c.name}"?`)) { deleteK8sCluster(c.id).then(load); }}} className="btn btn-danger" style={{ padding: '3px 10px', fontSize: '11px' }}>Delete</button>
                  </td>
                </tr>
              ))}
              {clusters.length === 0 && <tr><td colSpan="11" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>No Kubernetes clusters configured. Click "+ Add Cluster" to start monitoring.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
