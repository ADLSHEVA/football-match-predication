import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Play, Shield, TrendingUp, Cpu, Award } from 'lucide-react';
import DynamicSliders from '../components/DynamicSliders';
import PredictionGauge from '../components/PredictionGauge';
import ScoreMatrix from '../components/ScoreMatrix';
import OddsPanel from '../components/OddsPanel';
import H2HPanel from '../components/H2HPanel';
import LineupPanel from '../components/LineupPanel';

const DEFAULT_ADJUSTMENTS = {
  home_attack_adj: 1.0,
  home_defense_adj: 1.0,
  away_attack_adj: 1.0,
  away_defense_adj: 1.0,
  stamina_decay_home: 0.0,
  stamina_decay_away: 0.0,
  park_the_bus_enabled: false,
  park_the_bus_minute: 75,
  tactical_conservatism: 1.0
};

export default function MatchSimulator({ match, activeLeague, onBack }) {
  const [adjustments, setAdjustments] = useState(DEFAULT_ADJUSTMENTS);
  const [simulation, setSimulation] = useState(null);
  const [baseline, setBaseline] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Ref to hold the active AbortController for debounce/cancelling ongoing fetches
  const abortControllerRef = useRef(null);

  // Trigger simulation when adjustments change
  useEffect(() => {
    const runSimulation = async () => {
      // Cancel previous pending request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setLoading(true);
      setErrorMsg(null);

      // Prepare request body mapping
      const reqBody = {
        home_team: match.home_team,
        away_team: match.away_team,
        competition: activeLeague,
        adjustments: {
          home_attack_adj: adjustments.home_attack_adj,
          home_defense_adj: adjustments.home_defense_adj,
          away_attack_adj: adjustments.away_attack_adj,
          away_defense_adj: adjustments.away_defense_adj,
          stamina_decay_home: adjustments.stamina_decay_home,
          stamina_decay_away: adjustments.stamina_decay_away,
          park_the_bus_minute: adjustments.park_the_bus_enabled ? parseInt(adjustments.park_the_bus_minute) : null,
          tactical_conservatism: adjustments.tactical_conservatism
        }
      };

      try {
        const res = await fetch('/api/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(reqBody),
          signal: controller.signal
        });

        if (!res.ok) {
          let errMsg = '模拟失败，后端返回错误';
          try {
            const errData = await res.json();
            errMsg = errData.detail || errMsg;
          } catch {
            errMsg = `服务器错误 (HTTP ${res.status})`;
          }
          throw new Error(errMsg);
        }

        const data = await res.json();
        setSimulation(data.simulation);
        setBaseline(data.dixon_coles_baseline);
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error(err);
          setErrorMsg(err.message);
        }
      } finally {
        // Only set loading to false if this was the last request
        if (abortControllerRef.current === controller) {
          setLoading(false);
        }
      }
    };

    runSimulation();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [adjustments, match, activeLeague]);

  const handleReset = () => {
    setAdjustments(DEFAULT_ADJUSTMENTS);
  };

  return (
    <div className="simulator-page-wrapper">
      
      {/* Back Link */}
      <div className="back-link" onClick={onBack}>
        <ArrowLeft size={16} />
        返回赛程控制台 (Dashboard)
      </div>

      {/* Simulator Header */}
      <div className="simulator-header-block">
        <div className="glass-panel simulator-header-card">
          <div className="sim-team-big">
            <div className="sim-team-logo" style={{ borderColor: 'var(--win-home)' }}>
              {match.home_team.substring(0, 2).toUpperCase()}
            </div>
            <span className="sim-team-name">{match.home_team}</span>
            <span className="sim-team-elo">ELO: {match.home_elo?.toFixed(0) || 1500}</span>
          </div>

          <div className="sim-vs-big">
            <span className="sim-vs-text">VS</span>
            {simulation && (
              <span className="expected-goals-badge">
                xG 期望: {simulation.expected_home_goals?.toFixed(2)} - {simulation.expected_away_goals?.toFixed(2)}
              </span>
            )}
            {baseline && (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                基准 xG: {baseline.expected_home_goals?.toFixed(2)} - {baseline.expected_away_goals?.toFixed(2)}
              </span>
            )}
          </div>

          <div className="sim-team-big">
            <div className="sim-team-logo" style={{ borderColor: 'var(--win-away)' }}>
              {match.away_team.substring(0, 2).toUpperCase()}
            </div>
            <span className="sim-team-name">{match.away_team}</span>
            <span className="sim-team-elo">ELO: {match.away_elo?.toFixed(0) || 1500}</span>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="alert-banner warning" style={{ marginBottom: '24px' }}>
          模拟出错: {errorMsg}。请确保模型已拟合，或者返回主页重试。
        </div>
      )}

      {/* Simulator Core Layout */}
      <div className="simulator-layout">
        
        {/* Left Slider Column */}
        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 className="section-title" style={{ fontSize: '1.1rem', margin: 0 }}>
              <Cpu size={18} style={{ color: 'var(--primary)' }} />
              星蜥定量微调层
            </h2>
            <button className="btn-action" onClick={handleReset} style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
              重置
            </button>
          </div>
          <DynamicSliders 
            adjustments={adjustments} 
            onChange={setAdjustments} 
            homeTeam={match.home_team}
            awayTeam={match.away_team}
          />
        </div>

        {/* Right Output Column */}
        <div className="simulator-results">

          {/* Lineup & Formation Panel */}
          <LineupPanel
            homeTeam={match.home_team}
            awayTeam={match.away_team}
            competition={activeLeague}
          />

          {/* Odds Comparison Panel */}
          <OddsPanel
            homeTeam={match.home_team}
            awayTeam={match.away_team}
            competition={activeLeague}
          />

          {/* Head-to-Head Panel */}
          <H2HPanel
            homeTeam={match.home_team}
            awayTeam={match.away_team}
          />

          {simulation ? (
            <>
              {/* Probabilities Output */}
              <div className="glass-panel probabilities-box">
                <div className="prob-title-row">
                  <span className="section-title">
                    <TrendingUp size={18} style={{ color: 'var(--accent)' }} />
                    蒙特卡洛仿真输出 (基于 10,000 次时间步迭代)
                  </span>
                  {loading && <span className="brand-badge animate-spin">REFRESHING</span>}
                </div>

                <div className="prob-percentage-display" style={{ marginBottom: '24px' }}>
                  <div className="prob-card home">
                    <span className="prob-label">{match.home_team} 胜率</span>
                    <span className="prob-val">{(simulation.home_win_prob * 100).toFixed(1)}%</span>
                  </div>
                  <div className="prob-card draw">
                    <span className="prob-label">平局概率</span>
                    <span className="prob-val">{(simulation.draw_prob * 100).toFixed(1)}%</span>
                  </div>
                  <div className="prob-card away">
                    <span className="prob-label">{match.away_team} 胜率</span>
                    <span className="prob-val">{(simulation.away_win_prob * 100).toFixed(1)}%</span>
                  </div>
                </div>

                <PredictionGauge 
                  homeWinProb={simulation.home_win_prob} 
                  drawProb={simulation.draw_prob} 
                  awayWinProb={simulation.away_win_prob} 
                />
              </div>

              {/* Exact Score Matrix Heatmap */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <ScoreMatrix 
                  matrix={simulation.score_matrix} 
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                />
              </div>

              {/* Exact Scores & Over/Under columns */}
              <div className="prediction-details-grid">
                
                {/* Top 5 Scores */}
                <div className="glass-panel" style={{ padding: '20px' }}>
                  <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '16px' }}>
                    <Award size={16} style={{ color: 'var(--accent)' }} />
                    最可能出现的精确比分 (Top 5)
                  </h3>
                  <div className="top-scores-list">
                    {simulation.most_likely_scores && simulation.most_likely_scores.map((item, idx) => {
                      const [hGoals, aGoals, prob] = item;
                      const percentage = prob * 100;
                      return (
                        <div key={idx} className="top-score-row">
                          <span className="top-score-num">
                            {match.home_team} {hGoals} - {aGoals} {match.away_team}
                          </span>
                          <div className="top-score-bar-bg">
                            <div 
                              className="top-score-bar-fill" 
                              style={{ width: `${(prob / simulation.most_likely_scores[0][2]) * 100}%` }}
                            />
                          </div>
                          <span className="top-score-pct">{percentage.toFixed(1)}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Over Under Lines */}
                <div className="glass-panel" style={{ padding: '20px' }}>
                  <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '16px' }}>
                    <Shield size={16} style={{ color: 'var(--accent)' }} />
                    进球数大小盘口概率 (Over/Under)
                  </h3>
                  <div className="standings-container">
                    <table className="data-table" style={{ fontSize: '0.8rem' }}>
                      <thead>
                        <tr>
                          <th>进球盘口</th>
                          <th>大球概率 (Over)</th>
                          <th>小球概率 (Under)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {['1.5', '2.5', '3.5'].map((line) => {
                          const overKey = `O${line}`;
                          const underKey = `U${line}`;
                          const overProb = simulation.over_under ? simulation.over_under[overKey] : 0;
                          const underProb = simulation.over_under ? simulation.over_under[underKey] : 0;
                          
                          return (
                            <tr key={line}>
                              <td style={{ fontWeight: '700', fontFamily: 'var(--font-mono)' }}>{line} 球</td>
                              <td style={{ color: 'var(--win-home)', fontFamily: 'var(--font-mono)' }}>
                                {(overProb * 100).toFixed(1)}%
                              </td>
                              <td style={{ color: 'var(--win-away)', fontFamily: 'var(--font-mono)' }}>
                                {(underProb * 100).toFixed(1)}%
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            </>
          ) : (
            <div className="glass-panel loading-spinner-overlay" style={{ height: '300px' }}>
              <div className="spinner"></div>
              <span>正在计算蒙特卡洛赔率...</span>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
