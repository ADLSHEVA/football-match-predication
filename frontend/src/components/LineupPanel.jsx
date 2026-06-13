import React, { useState, useEffect } from 'react';
import { LayoutGrid, Users, Shield } from 'lucide-react';

export default function LineupPanel({ homeTeam, awayTeam, competition }) {
  const [lineupData, setLineupData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [configured, setConfigured] = useState(true);

  useEffect(() => {
    const fetchLineups = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `/api/lineups/${encodeURIComponent(homeTeam)}/${encodeURIComponent(awayTeam)}?competition=${competition}`
        );
        const data = await res.json();
        setConfigured(data.configured);
        setLineupData(data);
      } catch (e) {
        console.error('Failed to fetch lineups:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchLineups();
  }, [homeTeam, awayTeam, competition]);

  if (!configured) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '12px' }}>
          <LayoutGrid size={16} style={{ color: 'var(--accent)' }} />
          阵容与阵型分析
        </h3>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '0.85rem' }}>
          未配置 API_FOOTBALL_KEY，请在 .env 文件中设置。
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div className="loading-spinner-overlay" style={{ padding: '20px' }}>
          <div className="spinner"></div>
          <span>正在查询阵容信息...</span>
        </div>
      </div>
    );
  }

  if (!lineupData || (!lineupData.home && !lineupData.away)) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '12px' }}>
          <LayoutGrid size={16} style={{ color: 'var(--accent)' }} />
          阵容与阵型分析
        </h3>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '0.85rem' }}>
          阵容尚未公布（通常在比赛前1小时左右确认）
        </div>
      </div>
    );
  }

  const analysis = lineupData.formation_analysis;

  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '16px' }}>
        <LayoutGrid size={16} style={{ color: 'var(--accent)' }} />
        阵容与阵型分析
      </h3>

      {/* Formation Matchup Analysis */}
      {analysis && (
        <div style={{ marginBottom: '20px' }}>
          <div className="formation-matchup-row">
            <div className="formation-badge">{analysis.home_formation}</div>
            <div className="formation-advantage-arrow">
              <span className={`formation-advantage-score ${
                analysis.advantage_score > 0.05 ? 'positive' :
                analysis.advantage_score < -0.05 ? 'negative' : 'neutral'
              }`}>
                {analysis.advantage_score > 0 ? '+' : ''}{analysis.advantage_score}
              </span>
              <span className="formation-advantage-label">{analysis.advantage_label}</span>
            </div>
            <div className="formation-badge">{analysis.away_formation}</div>
          </div>

          <p style={{ textAlign: 'center', fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '10px', lineHeight: '1.5' }}>
            {analysis.description}
          </p>

          {analysis.key_factors && analysis.key_factors.length > 0 && (
            <div className="key-factors-list">
              {analysis.key_factors.map((f, i) => (
                <span key={i} className="key-factor-tag">{f}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Starting XI */}
      {(lineupData.home || lineupData.away) && (
        <div>
          <h4 style={{ fontSize: '0.85rem', fontWeight: '700', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Users size={14} style={{ color: 'var(--accent)' }} />
            首发阵容
          </h4>
          <div className="lineup-dual-grid">
            {lineupData.home && (
              <div className="lineup-team-section">
                <h4>
                  <Shield size={13} style={{ color: 'var(--win-home)' }} />
                  {homeTeam} ({lineupData.home.formation})
                </h4>
                <div className="standings-container">
                  <table className="data-table" style={{ fontSize: '0.78rem' }}>
                    <thead>
                      <tr>
                        <th style={{ width: '30px' }}>#</th>
                        <th>球员</th>
                        <th style={{ width: '40px' }}>位置</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lineupData.home.start_xi.map((p, idx) => (
                        <tr key={idx}>
                          <td style={{ fontFamily: 'var(--font-mono)', textAlign: 'center' }}>{p.number}</td>
                          <td style={{ fontWeight: '600' }}>{p.name}</td>
                          <td style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.72rem' }}>{p.pos}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {lineupData.home.coach && (
                  <div className="lineup-coach">
                    <Shield size={11} style={{ display: 'inline', marginRight: '4px' }} />
                    主教练: {lineupData.home.coach}
                  </div>
                )}
              </div>
            )}

            {lineupData.away && (
              <div className="lineup-team-section">
                <h4>
                  <Shield size={13} style={{ color: 'var(--win-away)' }} />
                  {awayTeam} ({lineupData.away.formation})
                </h4>
                <div className="standings-container">
                  <table className="data-table" style={{ fontSize: '0.78rem' }}>
                    <thead>
                      <tr>
                        <th style={{ width: '30px' }}>#</th>
                        <th>球员</th>
                        <th style={{ width: '40px' }}>位置</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lineupData.away.start_xi.map((p, idx) => (
                        <tr key={idx}>
                          <td style={{ fontFamily: 'var(--font-mono)', textAlign: 'center' }}>{p.number}</td>
                          <td style={{ fontWeight: '600' }}>{p.name}</td>
                          <td style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.72rem' }}>{p.pos}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {lineupData.away.coach && (
                  <div className="lineup-coach">
                    <Shield size={11} style={{ display: 'inline', marginRight: '4px' }} />
                    主教练: {lineupData.away.coach}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
