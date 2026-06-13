import React, { useState } from 'react';
import { Trophy, Medal } from 'lucide-react';
import { useT } from '../i18n.jsx';

/**
 * WCChampionshipOdds
 * Sorted leaderboard of championship probabilities with horizontal bars.
 * `teams` is expected pre-sorted by p_champion (the API returns it that way).
 */
export default function WCChampionshipOdds({ teams = [] }) {
  const { t } = useT();
  const [showAll, setShowAll] = useState(false);

  if (!teams.length) return null;

  const maxChamp = Math.max(...teams.map((x) => x.p_champion), 0.0001);
  const shown = showAll ? teams : teams.slice(0, 16);

  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      <h3 className="section-title" style={{ fontSize: '1rem', marginBottom: '16px' }}>
        <Trophy size={18} style={{ color: 'var(--draw)' }} />
        {t('夺冠概率排行 (蒙特卡洛全赛程模拟)')}
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {shown.map((tm, idx) => (
          <div
            key={tm.name}
            style={{
              display: 'grid',
              gridTemplateColumns: '28px 1.6fr 3fr 56px',
              alignItems: 'center',
              gap: '10px',
              padding: '6px 8px',
              borderRadius: '8px',
              background: idx < 3 ? 'rgba(245, 158, 11, 0.06)' : 'transparent',
            }}
          >
            <span style={{
              fontFamily: 'var(--font-mono)', fontWeight: 700,
              color: idx === 0 ? 'var(--draw)' : 'var(--text-muted)', textAlign: 'center',
            }}>
              {idx + 1}
            </span>

            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
              <span style={{ fontSize: '1.1rem' }}>{tm.flag}</span>
              <span style={{
                fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }} title={`${tm.name} · ELO ${tm.elo}`}>
                {tm.name}
              </span>
            </span>

            <div style={{ position: 'relative', height: '20px', background: 'rgba(15,23,42,0.5)', borderRadius: '6px', overflow: 'hidden' }}>
              <div style={{
                position: 'absolute', inset: 0, width: `${(tm.p_champion / maxChamp) * 100}%`,
                background: idx === 0
                  ? 'linear-gradient(90deg, var(--draw), #fbbf24)'
                  : 'linear-gradient(90deg, var(--primary), var(--accent))',
                borderRadius: '6px', transition: 'width 0.4s ease',
              }} />
              <span style={{
                position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)',
                fontSize: '0.65rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)',
              }}>
                {t('决赛 ')}{(tm.p_final * 100).toFixed(1)}%{t(' · 4强 ')}{(tm.p_sf * 100).toFixed(1)}%
              </span>
            </div>

            <span style={{
              fontFamily: 'var(--font-mono)', fontWeight: 800, textAlign: 'right',
              color: idx === 0 ? 'var(--draw)' : 'var(--text-primary)',
            }}>
              {(tm.p_champion * 100).toFixed(1)}%
            </span>
          </div>
        ))}
      </div>

      {teams.length > 16 && (
        <button
          className="btn-action"
          onClick={() => setShowAll((v) => !v)}
          style={{ marginTop: '12px', width: '100%', justifyContent: 'center', display: 'flex', gap: '6px' }}
        >
          <Medal size={14} />
          {showAll ? t('收起') : `${t('显示全部')} ${teams.length}${t(' 支球队')}`}
        </button>
      )}
    </div>
  );
}
