import React, { useState, useEffect } from 'react';
import { TrendingUp, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { useT } from '../i18n.jsx';

export default function OddsPanel({ homeTeam, awayTeam, competition }) {
  const { t } = useT();
  const [oddsData, setOddsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [configured, setConfigured] = useState(true);
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    const fetchOdds = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `/api/odds/${encodeURIComponent(homeTeam)}/${encodeURIComponent(awayTeam)}?competition=${competition}`
        );
        const data = await res.json();
        setConfigured(data.configured);
        setOddsData(data);
      } catch (e) {
        console.error('Failed to fetch odds:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchOdds();
  }, [homeTeam, awayTeam, competition]);

  if (!configured) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '12px' }}>
          <TrendingUp size={16} style={{ color: 'var(--accent)' }} />
          {t('赔率对比与价值投注')}
        </h3>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '0.85rem' }}>
          {t('未配置 THE_ODDS_API_KEY，请在 .env 文件中设置。')}
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div className="loading-spinner-overlay" style={{ padding: '20px' }}>
          <div className="spinner"></div>
          <span>{t('正在获取赔率数据...')}</span>
        </div>
      </div>
    );
  }

  if (!oddsData || !oddsData.odds || oddsData.odds.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '12px' }}>
          <TrendingUp size={16} style={{ color: 'var(--accent)' }} />
          {t('赔率对比与价值投注')}
        </h3>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '0.85rem' }}>
          {t('暂无该比赛的赔率数据。')}
        </div>
      </div>
    );
  }

  const h2hOdds = oddsData.odds.filter(o => o.market === 'h2h');
  const valueBets = oddsData.value_bets || [];
  const positiveEV = valueBets.filter(v => v.is_value);

  return (
    <div className="glass-panel" style={{ padding: '20px' }}>
      <h3
        className="section-title"
        style={{ fontSize: '0.95rem', marginBottom: collapsed ? '0' : '16px', cursor: 'pointer', userSelect: 'none' }}
        onClick={() => setCollapsed(c => !c)}
      >
        <TrendingUp size={16} style={{ color: 'var(--accent)' }} />
        {t('赔率对比与价值投注分析')}
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {collapsed ? t('展开') : t('收起')}
          {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </span>
      </h3>

      {!collapsed && (<>
      {/* Odds Comparison Table */}
      {h2hOdds.length > 0 && (
        <div className="standings-container" style={{ marginBottom: '20px' }}>
          <table className="data-table" style={{ fontSize: '0.8rem' }}>
            <thead>
              <tr>
                <th>{t('博彩公司')}</th>
                <th>{homeTeam} {t('胜')}</th>
                <th>{t('平局')}</th>
                <th>{awayTeam} {t('胜')}</th>
              </tr>
            </thead>
            <tbody>
              {h2hOdds.map((entry, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: '600', textTransform: 'capitalize' }}>{entry.bookmaker}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--win-home)' }}>
                    {entry.home_odds?.toFixed(2) || '-'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--draw)' }}>
                    {entry.draw_odds?.toFixed(2) || '-'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--win-away)' }}>
                    {entry.away_odds?.toFixed(2) || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Value Bets */}
      {valueBets.length > 0 && (
        <div>
          <h4 style={{ fontSize: '0.85rem', fontWeight: '700', marginBottom: '12px', color: 'var(--text-secondary)' }}>
            <AlertTriangle size={14} style={{ color: 'var(--draw)', marginRight: '6px', verticalAlign: 'middle' }} />
            {t('价值投注机会 (EV > 0)')}
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {positiveEV.length > 0 ? positiveEV.map((vb, idx) => (
              <div key={idx} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 14px', borderRadius: '8px',
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
              }}>
                <div>
                  <span style={{ fontWeight: '700', fontSize: '0.85rem' }}>
                    {vb.outcome === 'home' ? homeTeam : vb.outcome === 'away' ? awayTeam : t('平局')}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '8px' }}>
                    @{vb.bookmaker}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '16px', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                  <span>{t('赔率: ')}{vb.decimal_odds.toFixed(2)}</span>
                  <span>{t('模型: ')}{(vb.model_prob * 100).toFixed(1)}%</span>
                  <span style={{ color: 'var(--win-home)', fontWeight: '700' }}>
                    EV: +{(vb.expected_value * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            )) : (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '12px', fontSize: '0.8rem' }}>
                {t('当前赔率与模型估值一致，暂无明显价值投注机会。')}
              </div>
            )}
          </div>
        </div>
      )}
      </>)}
    </div>
  );
}
