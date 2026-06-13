import React, { useState, useEffect } from 'react';
import { Users, ChevronDown, ChevronUp } from 'lucide-react';
import { useT } from '../i18n.jsx';

export default function H2HPanel({ homeTeam, awayTeam }) {
  const { t } = useT();
  const [h2hData, setH2hData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [configured, setConfigured] = useState(true);
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    const fetchH2H = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `/api/h2h/${encodeURIComponent(homeTeam)}/${encodeURIComponent(awayTeam)}`
        );
        const data = await res.json();
        setConfigured(data.configured);
        setH2hData(data);
      } catch (e) {
        console.error('Failed to fetch H2H:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchH2H();
  }, [homeTeam, awayTeam]);

  if (!configured) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '12px' }}>
          <Users size={16} style={{ color: 'var(--accent)' }} />
          {t('历史交锋记录 (H2H)')}
        </h3>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '0.85rem' }}>
          {t('未配置 API_FOOTBALL_KEY，请在 .env 文件中设置。')}
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div className="loading-spinner-overlay" style={{ padding: '20px' }}>
          <div className="spinner"></div>
          <span>{t('正在查询历史交锋...')}</span>
        </div>
      </div>
    );
  }

  if (!h2hData || h2hData.total_matches === 0) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '12px' }}>
          <Users size={16} style={{ color: 'var(--accent)' }} />
          {t('历史交锋记录 (H2H)')}
        </h3>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '0.85rem' }}>
          {t('暂无历史交锋数据。')}
        </div>
      </div>
    );
  }

  const total = h2hData.total_matches || 1;

  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      <h3
        className="section-title"
        style={{ fontSize: '0.95rem', marginBottom: collapsed ? '0' : '16px', cursor: 'pointer', userSelect: 'none' }}
        onClick={() => setCollapsed(c => !c)}
      >
        <Users size={16} style={{ color: 'var(--accent)' }} />
        {t('历史交锋记录 (近 ')}{h2hData.total_matches}{t(' 场)')}
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {collapsed ? t('展开') : t('收起')}
          {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </span>
      </h3>

      {!collapsed && (<>
      {/* Summary Stats */}
      <div className="prob-percentage-display" style={{ marginBottom: '20px' }}>
        <div className="prob-card home">
          <span className="prob-label">{homeTeam} {t('胜')}</span>
          <span className="prob-val">{h2hData.home_wins}</span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            {((h2hData.home_wins / total) * 100).toFixed(0)}%
          </span>
        </div>
        <div className="prob-card draw">
          <span className="prob-label">{t('平局')}</span>
          <span className="prob-val">{h2hData.draws}</span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            {((h2hData.draws / total) * 100).toFixed(0)}%
          </span>
        </div>
        <div className="prob-card away">
          <span className="prob-label">{awayTeam} {t('胜')}</span>
          <span className="prob-val">{h2hData.away_wins}</span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            {((h2hData.away_wins / total) * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Avg Goals */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '24px', marginBottom: '16px', fontSize: '0.85rem' }}>
        <span style={{ color: 'var(--text-secondary)' }}>
          {t('场均进球: ')}<span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--accent)' }}>
            {h2hData.avg_home_goals} - {h2hData.avg_away_goals}
          </span>
        </span>
      </div>

      {/* Recent Results List */}
      <div className="standings-container">
        <table className="data-table" style={{ fontSize: '0.8rem' }}>
          <thead>
            <tr>
              <th>{t('日期')}</th>
              <th>{t('主队')}</th>
              <th>{t('比分')}</th>
              <th>{t('客队')}</th>
            </tr>
          </thead>
          <tbody>
            {h2hData.recent_results.slice(0, 8).map((r, idx) => {
              const dateStr = r.fixture_date ? new Date(r.fixture_date).toLocaleDateString(undefined) : '-';
              const hg = r.home_goals ?? '-';
              const ag = r.away_goals ?? '-';
              const isDraw = hg === ag;
              const homeWin = hg > ag;
              return (
                <tr key={idx}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{dateStr}</td>
                  <td style={{ fontWeight: '600', color: homeWin ? 'var(--win-home)' : 'var(--text-primary)' }}>
                    {r.home_team}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', textAlign: 'center' }}>
                    {hg} - {ag}
                  </td>
                  <td style={{ fontWeight: '600', color: !isDraw && !homeWin ? 'var(--win-away)' : 'var(--text-primary)' }}>
                    {r.away_team}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      </>)}
    </div>
  );
}
