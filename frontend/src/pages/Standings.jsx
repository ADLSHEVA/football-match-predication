import React, { useState, useEffect } from 'react';
import { RefreshCw, TrendingUp, Shield, BarChart2 } from 'lucide-react';
import LeagueSelector from '../components/LeagueSelector';

export default function Standings({ activeLeague, setActiveLeague }) {
  const [standings, setStandings] = useState([]);
  const [teamParams, setTeamParams] = useState({});
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const fetchStandings = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      // 1. Fetch standings table
      const standRes = await fetch(`/api/standings/${activeLeague}`);
      if (!standRes.ok) {
        throw new Error('无法获取积分榜数据，可能是 API Key 达到限制或网络问题');
      }
      const standData = await standRes.json();
      
      // 2. Fetch enriched teams info (ELO + Dixon-Coles params)
      const teamsRes = await fetch(`/api/teams?competition=${activeLeague}`);
      let paramsMap = {};
      if (teamsRes.ok) {
        const teamsData = await teamsRes.json();
        teamsData.teams.forEach(t => {
          paramsMap[t.name] = t;
        });
      }

      setStandings(standData.standings || []);
      setTeamParams(paramsMap);
    } catch (e) {
      console.error(e);
      setErrorMsg(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStandings();
  }, [activeLeague]);

  return (
    <div className="standings-page-wrapper">
      
      {/* League selection */}
      <div style={{ marginBottom: '24px' }}>
        <h2 className="section-title" style={{ marginBottom: '12px' }}>
          选择目标联赛积分榜
        </h2>
        <LeagueSelector activeLeague={activeLeague} onChange={setActiveLeague} />
      </div>

      {/* Main standings panel */}
      <div className="glass-panel">
        <div className="section-header">
          <div>
            <h2 className="section-title">
              <TrendingUp size={20} style={{ color: 'var(--accent)' }} />
              当前积分与量化指标对比
            </h2>
            <span className="section-subtitle">
              结合实时联赛积分，与 Dixon-Coles 拟合进攻/防守实力 (α, β) 和当前 ELO。
            </span>
          </div>
          <button 
            className="btn-action" 
            onClick={fetchStandings} 
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            {loading ? '刷新中...' : '刷新'}
          </button>
        </div>

        {errorMsg && (
          <div className="alert-banner warning" style={{ marginBottom: '16px' }}>
            错误: {errorMsg}
          </div>
        )}

        {loading ? (
          <div className="loading-spinner-overlay">
            <div className="spinner"></div>
            <span>正在载入联赛数据与拟合指标...</span>
          </div>
        ) : standings.length > 0 ? (
          <div className="standings-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="rank-cell">排名</th>
                  <th>球队</th>
                  <th style={{ textAlign: 'center' }}>已赛</th>
                  <th style={{ textAlign: 'center' }}>胜/平/负</th>
                  <th style={{ textAlign: 'center' }}>进/失/净</th>
                  <th style={{ textAlign: 'center' }}>积分</th>
                  <th style={{ textAlign: 'center', color: 'var(--accent)' }}>ELO 评分</th>
                  <th style={{ textAlign: 'center', color: 'var(--win-home)' }}>进攻强度 (α)</th>
                  <th style={{ textAlign: 'center', color: 'var(--win-away)' }}>防守强度 (β)</th>
                </tr>
              </thead>
              <tbody>
                {standings.map((row) => {
                  const param = teamParams[row.team] || {};
                  
                  return (
                    <tr key={row.team_id || row.team}>
                      <td className="rank-cell">{row.position}</td>
                      <td>
                        <span className="team-cell-name">
                          <span className="team-logo-placeholder" style={{ width: '28px', height: '28px', fontSize: '0.75rem' }}>
                            {row.team.substring(0, 2).toUpperCase()}
                          </span>
                          {row.team}
                        </span>
                      </td>
                      <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{row.played}</td>
                      <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                        {row.won} / {row.draw} / {row.lost}
                      </td>
                      <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                        {row.goals_for} / {row.goals_against} / <strong style={{ color: row.goal_difference >= 0 ? 'var(--win-home)' : 'var(--win-away)' }}>{row.goal_difference}</strong>
                      </td>
                      <td style={{ textAlign: 'center', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
                        {row.points}
                      </td>
                      
                      {/* ELO */}
                      <td style={{ textAlign: 'center' }}>
                        <span className="elo-val">
                          {param.elo_rating ? param.elo_rating.toFixed(0) : '1500'}
                        </span>
                      </td>

                      {/* Attack Param */}
                      <td style={{ textAlign: 'center', color: 'var(--win-home)', fontFamily: 'var(--font-mono)' }}>
                        {param.attack ? (
                          <span>{param.attack.toFixed(3)}</span>
                        ) : (
                          <span style={{ opacity: 0.35 }}>未拟合</span>
                        )}
                      </td>

                      {/* Defense Param */}
                      <td style={{ textAlign: 'center', color: 'var(--win-away)', fontFamily: 'var(--font-mono)' }}>
                        {param.defense ? (
                          <span>{param.defense.toFixed(3)}</span>
                        ) : (
                          <span style={{ opacity: 0.35 }}>未拟合</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            暂无当前联赛积分榜数据，请检查网络或在主页同步数据。
          </div>
        )}
      </div>

    </div>
  );
}
