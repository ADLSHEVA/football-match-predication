import React from 'react';
import { Trophy } from 'lucide-react';

/**
 * WCBracket
 * Renders the projected knockout tree (Round of 32 → Final). The model's
 * favourite in each tie (higher championship probability) is highlighted —
 * this is the modal projected path, not a guaranteed result.
 */
function isFav(a, b) {
  const pa = a?.p_champion ?? -1;
  const pb = b?.p_champion ?? -1;
  if (pa !== pb) return pa >= pb;
  return (a?.elo ?? 0) >= (b?.elo ?? 0);
}

function TeamRow({ team, winner }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '6px',
      padding: '3px 6px',
      opacity: team?.name === 'TBD' ? 0.4 : winner ? 1 : 0.55,
      fontWeight: winner ? 700 : 400,
    }}>
      <span style={{ fontSize: '0.95rem' }}>{team?.flag || ''}</span>
      <span style={{
        fontSize: '0.72rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        color: winner ? 'var(--text-primary)' : 'var(--text-secondary)',
      }}>
        {team?.name || 'TBD'}
      </span>
    </div>
  );
}

function MatchCard({ left, right }) {
  const leftWins = isFav(left, right);
  return (
    <div style={{
      background: 'rgba(15,23,42,0.5)',
      border: '1px solid var(--border-light)',
      borderLeft: '3px solid var(--win-home)',
      borderRadius: '6px',
      minWidth: '150px',
    }}>
      <TeamRow team={left} winner={leftWins} />
      <div style={{ height: 1, background: 'var(--border-light)' }} />
      <TeamRow team={right} winner={!leftWins} />
    </div>
  );
}

function Column({ title, matches }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: '160px' }}>
      <div style={{
        fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent)',
        textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '10px', textAlign: 'center',
      }}>
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', justifyContent: 'space-around', flex: 1 }}>
        {matches.map((m, i) => (
          <MatchCard key={i} left={m.left} right={m.right} />
        ))}
      </div>
    </div>
  );
}

export default function WCBracket({ bracket }) {
  if (!bracket) return null;
  const { r32 = [], r16 = [], qf = [], sf = [], final = [], projected_champion } = bracket;

  return (
    <div className="glass-panel" style={{ padding: '20px', overflowX: 'auto' }}>
      <h3 className="section-title" style={{ fontSize: '1rem', marginBottom: '6px' }}>
        <Trophy size={18} style={{ color: 'var(--accent)' }} />
        淘汰赛对阵预测 (模型最可能晋级路径)
      </h3>
      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '18px' }}>
        小组名次按模拟均分排定，淘汰赛每场高亮一方为模型favorite——仅为最可能路径，非确定结果。
      </p>

      <div style={{ display: 'flex', gap: '18px', alignItems: 'stretch', minWidth: 'max-content', paddingBottom: '8px' }}>
        <Column title="32 强" matches={r32} />
        <Column title="16 强" matches={r16} />
        <Column title="1/4 决赛" matches={qf} />
        <Column title="半决赛" matches={sf} />
        <Column title="决赛" matches={final} />

        {/* Champion */}
        <div style={{ display: 'flex', flexDirection: 'column', minWidth: '150px' }}>
          <div style={{
            fontSize: '0.72rem', fontWeight: 700, color: 'var(--draw)',
            textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '10px', textAlign: 'center',
          }}>
            冠军
          </div>
          <div style={{ display: 'flex', flex: 1, alignItems: 'center' }}>
            <div style={{
              background: 'linear-gradient(135deg, rgba(245,158,11,0.15), rgba(251,191,36,0.05))',
              border: '1px solid rgba(245,158,11,0.4)',
              borderRadius: '10px', padding: '16px 12px', textAlign: 'center', width: '100%',
            }}>
              <Trophy size={22} style={{ color: 'var(--draw)' }} />
              <div style={{ fontSize: '1.6rem', margin: '6px 0' }}>{projected_champion?.flag}</div>
              <div style={{ fontWeight: 800, fontSize: '0.85rem' }}>{projected_champion?.name}</div>
              {projected_champion?.p_champion != null && (
                <div style={{ fontSize: '0.7rem', color: 'var(--draw)', fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
                  {(projected_champion.p_champion * 100).toFixed(1)}% 夺冠
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
