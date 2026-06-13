import React from 'react';
import { Users } from 'lucide-react';
import { useT } from '../i18n.jsx';

/**
 * WCGroupStage
 * Twelve group cards (A–L). Each row shows mean simulated points and the
 * probability of reaching the knockout stage. Top two are highlighted as
 * direct qualifiers (green); third place (amber) may still advance as one of
 * the eight best third-placed teams.
 */
function qualifyColor(rank) {
  if (rank < 2) return 'var(--win-home)';   // top 2 advance directly
  if (rank === 2) return 'var(--draw)';      // 3rd: best-third contender
  return 'transparent';
}

export default function WCGroupStage({ groups = {} }) {
  const { t } = useT();
  const labels = Object.keys(groups).sort();
  if (!labels.length) return null;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', marginBottom: '14px' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--win-home)' }} /> {t('直接出线 (前二)')}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--draw)' }} /> {t('小组第三 (争最佳8席)')}
        </span>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '16px',
      }}>
        {labels.map((label) => (
          <div key={label} className="glass-panel" style={{ padding: '16px' }}>
            <h4 style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              fontSize: '0.9rem', fontWeight: 700, marginBottom: '12px', color: 'var(--text-primary)',
            }}>
              <Users size={15} style={{ color: 'var(--primary)' }} />
              {t('小组 ')}{label}
            </h4>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', fontSize: '0.7rem', textAlign: 'left' }}>
                  <th style={{ padding: '2px 4px', fontWeight: 500 }}>{t('球队')}</th>
                  <th style={{ padding: '2px 4px', fontWeight: 500, textAlign: 'right' }}>{t('均分')}</th>
                  <th style={{ padding: '2px 4px', fontWeight: 500, textAlign: 'right' }}>{t('出线率')}</th>
                </tr>
              </thead>
              <tbody>
                {groups[label].map((tm, rank) => (
                  <tr key={tm.name} style={{ borderTop: '1px solid var(--border-light)' }}>
                    <td style={{ padding: '6px 4px' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          width: 3, height: 18, borderRadius: 2,
                          background: qualifyColor(rank), flexShrink: 0,
                        }} />
                        <span style={{ fontSize: '1rem' }}>{tm.flag}</span>
                        <span style={{
                          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '120px',
                        }} title={`${tm.name} · ELO ${tm.elo}`}>
                          {tm.name}
                        </span>
                      </span>
                    </td>
                    <td style={{ padding: '6px 4px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      {tm.avg_points.toFixed(1)}
                    </td>
                    <td style={{
                      padding: '6px 4px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700,
                      color: rank < 2 ? 'var(--win-home)' : 'var(--text-primary)',
                    }}>
                      {(tm.p_advance * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
