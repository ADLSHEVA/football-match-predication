import React, { useState, useEffect } from 'react';
import { RefreshCw, Play, BarChart2, Cpu, Database, Award, CheckCircle, AlertTriangle } from 'lucide-react';
import LeagueSelector from '../components/LeagueSelector';
import PredictionGauge from '../components/PredictionGauge';

export default function Dashboard({
  activeLeague,
  setActiveLeague,
  onSelectMatch,
  setView
}) {
  const [predictions, setPredictions] = useState([]);
  const [rawMatches, setRawMatches] = useState([]);
  const [accuracy, setAccuracy] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Sync / Train States
  const [syncLoading, setSyncLoading] = useState(false);
  const [trainLoading, setTrainLoading] = useState(false);
  const [logText, setLogText] = useState('系统就绪。点击同步或训练按钮开始。\n');
  const [modelFitted, setModelFitted] = useState(false);
  const [apiKeyConfigured, setApiKeyConfigured] = useState(true);

  // Manual prediction states
  const [teams, setTeams] = useState([]);
  const [manualHome, setManualHome] = useState('');
  const [manualAway, setManualAway] = useState('');
  const [manualPredLoading, setManualPredLoading] = useState(false);
  const [manualPredResult, setManualPredResult] = useState(null);

  // Batch odds state
  const [batchOdds, setBatchOdds] = useState({});

  // Load predictions and stats
  const fetchData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      // 1. Check health to see if model is fitted
      const healthRes = await fetch('/api/health');
      const healthData = await healthRes.json();
      setModelFitted(healthData.model_fitted);
      setApiKeyConfigured(healthData.api_key_configured !== false);

      // 2. Fetch upcoming predictions
      const predRes = await fetch(`/api/predictions/upcoming?competition=${activeLeague}`);
      if (predRes.ok) {
        const predData = await predRes.json();
        setPredictions(predData.predictions || []);
      } else {
        // If predictions fail (e.g. model not fitted), fetch raw upcoming matches
        const rawRes = await fetch(`/api/matches/upcoming?competition=${activeLeague}`);
        const rawData = await rawRes.json();
        setRawMatches(rawData.matches || []);
        setPredictions([]);
      }

      // 3. Fetch accuracy stats
      const accRes = await fetch('/api/model/accuracy');
      if (accRes.ok) {
        const accData = await accRes.json();
        setAccuracy(accData);
      }

      // 4. Fetch teams for manual prediction
      const teamsRes = await fetch(`/api/teams?competition=${activeLeague}`);
      if (teamsRes.ok) {
        const teamsData = await teamsRes.json();
        setTeams(teamsData.teams || []);
      }

      // 5. Fetch batch odds for value bet badges
      try {
        const oddsRes = await fetch(`/api/odds/batch?competition=${activeLeague}`);
        if (oddsRes.ok) {
          const oddsBatchData = await oddsRes.json();
          setBatchOdds(oddsBatchData.matches || {});
        }
      } catch {
        // Non-critical, ignore
      }
    } catch (e) {
      console.error(e);
      setErrorMsg('无法连接到 API 后端，请确保 FastAPI 服务器已正常启动。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeLeague]);

  const handleSync = async () => {
    setSyncLoading(true);
    setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 开始同步 ${activeLeague} 联赛数据...\n`);
    try {
      const res = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ competition: activeLeague, season: '2025' })
      });
      const data = await res.json();
      if (res.ok) {
        setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 同步成功！新增比赛/xG数据: ${JSON.stringify(data.report)}\n`);
        if (data.report?.warning) {
          setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 提示: ${data.report.warning}\n`);
        }
      } else {
        setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 同步失败: ${data.detail}\n`);
      }
    } catch (e) {
      setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 同步出错: ${e.message}\n`);
    } finally {
      setSyncLoading(false);
      fetchData(); // reload
    }
  };

  const handleManualPredict = async () => {
    if (!manualHome || !manualAway || manualHome === manualAway) return;
    setManualPredLoading(true);
    setManualPredResult(null);
    try {
      const res = await fetch(`/api/predict/${encodeURIComponent(manualHome)}/${encodeURIComponent(manualAway)}?competition=${activeLeague}`);
      if (res.ok) {
        const data = await res.json();
        setManualPredResult(data);
      } else {
        const err = await res.json();
        setManualPredResult({ error: err.detail || '预测失败' });
      }
    } catch (e) {
      setManualPredResult({ error: e.message });
    } finally {
      setManualPredLoading(false);
    }
  };

  const handleTrain = async () => {
    setTrainLoading(true);
    setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 开始基于历史 xG 数据拟合 Dixon-Coles 模型与 ELO...\n`);
    try {
      const res = await fetch(`/api/model/fit?competition=${activeLeague}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (res.ok) {
        setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 模型训练完成！\n` + 
          `- 拟合球队数量: ${data.teams_fitted}\n` +
          `- 主场优势因子 (Home Adv): ${data.home_advantage?.toFixed(4)}\n` +
          `- 低进球相关修正 (Rho): ${data.rho?.toFixed(4)}\n`);
        setModelFitted(true);
      } else {
        setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 训练失败: ${data.detail}\n`);
      }
    } catch (e) {
      setLogText((prev) => prev + `[${new Date().toLocaleTimeString()}] 训练出错: ${e.message}\n`);
    } finally {
      setTrainLoading(false);
      fetchData(); // reload
    }
  };

  return (
    <div className="dashboard-main-wrapper">
      
      {/* Alert Banner if Backend connection fails or model is not fitted */}
      {errorMsg && (
        <div className="alert-banner warning">
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={18} />
            {errorMsg}
          </span>
          <button className="btn-action" onClick={fetchData} style={{ padding: '4px 10px' }}>重试</button>
        </div>
      )}

      {!errorMsg && !modelFitted && (
        <div className="alert-banner info">
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={18} className="animate-spin" />
            系统警告: {activeLeague} 联赛的 Dixon-Coles 实力估值模型尚未训练！请在右侧控制面板进行「同步」与「训练」。
          </span>
        </div>
      )}

      {!errorMsg && !apiKeyConfigured && (
        <div className="alert-banner warning">
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={18} />
            未配置 Football-Data.org API Key。历史数据将从免费CSV源加载，但无法获取未来赛程。
            请在项目根目录 .env 文件中设置 FOOTBALL_DATA_API_KEY（免费注册: https://www.football-data.org/）
          </span>
        </div>
      )}

      {/* League Selection */}
      <div style={{ marginBottom: '24px' }}>
        <h2 className="section-title" style={{ marginBottom: '12px' }}>
          <Database size={20} style={{ color: 'var(--primary)' }} />
          选择目标联赛
        </h2>
        <LeagueSelector activeLeague={activeLeague} onChange={setActiveLeague} />
      </div>

      {/* Main Grid */}
      <div className="dashboard-grid">
        
        {/* Matches Area */}
        <div className="dashboard-main">
          <div className="section-header">
            <div>
              <h2 className="section-title">
                <BarChart2 size={20} style={{ color: 'var(--accent)' }} />
                赛程与胜率预测 (Dixon-Coles 基准)
              </h2>
              <span className="section-subtitle">展示未来即将进行的比赛。点击「模拟微调」进入星蜥定量面板。</span>
            </div>
            <button 
              className="btn-action" 
              onClick={fetchData} 
              disabled={loading}
              title="刷新数据"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              {loading ? '刷新中...' : '刷新'}
            </button>
          </div>

          {loading ? (
            <div className="glass-panel loading-spinner-overlay">
              <div className="spinner"></div>
              <span>正在拉取赛事数据...</span>
            </div>
          ) : predictions.length > 0 ? (
            <div className="matches-grid">
              {predictions.map((match) => (
                <div key={match.match_id} className="glass-panel match-card">
                  <div className="match-meta">
                    <span className="match-badge">ID: {match.match_id}</span>
                    <span>{match.date ? new Date(match.date).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '未定'}</span>
                    {batchOdds[`${match.home_team}|${match.away_team}`] && (
                      <span className="value-badge positive">赔率可用</span>
                    )}
                  </div>

                  <div className="match-teams">
                    <div className="team-display">
                      <div className="team-logo-placeholder">
                        {match.home_team.substring(0, 2).toUpperCase()}
                      </div>
                      <span className="team-name" title={match.home_team}>{match.home_team}</span>
                      <span className="sim-team-elo">ELO: {match.home_elo?.toFixed(0)}</span>
                    </div>

                    <div className="match-vs">VS</div>

                    <div className="team-display">
                      <div className="team-logo-placeholder">
                        {match.away_team.substring(0, 2).toUpperCase()}
                      </div>
                      <span className="team-name" title={match.away_team}>{match.away_team}</span>
                      <span className="sim-team-elo">ELO: {match.away_elo?.toFixed(0)}</span>
                    </div>
                  </div>

                  {/* Prediction Gauge */}
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      <span>Dixon-Coles 胜率:</span>
                      <span>均值: {match.expected_home_goals?.toFixed(1)} - {match.expected_away_goals?.toFixed(1)}</span>
                    </div>
                    <PredictionGauge 
                      homeWinProb={match.home_win} 
                      drawProb={match.draw} 
                      awayWinProb={match.away_win} 
                    />
                  </div>

                  <div className="match-footer">
                    <span className="elo-comparison">
                      ELO 胜率: {(match.elo_home_win * 100).toFixed(0)}% 主胜
                    </span>
                    <button 
                      className="btn-action"
                      onClick={() => onSelectMatch(match)}
                    >
                      <Play size={12} />
                      模拟微调
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : rawMatches.length > 0 ? (
            <div>
              <div className="alert-banner warning" style={{ marginBottom: '16px' }}>
                已获取赛程，但由于实力估值模型未训练，无法显示胜率预测。请在右侧控制面板点击「同步」和「拟合模型」。
              </div>
              <div className="matches-grid">
                {rawMatches.map((match) => (
                  <div key={match.id} className="glass-panel match-card">
                    <div className="match-meta">
                      <span className="match-badge">ID: {match.id}</span>
                      <span>{match.date ? new Date(match.date).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '未定'}</span>
                    </div>

                    <div className="match-teams">
                      <div className="team-display">
                        <div className="team-logo-placeholder">
                          {match.home_team.substring(0, 2).toUpperCase()}
                        </div>
                        <span className="team-name">{match.home_team}</span>
                      </div>

                      <div className="match-vs">VS</div>

                      <div className="team-display">
                        <div className="team-logo-placeholder">
                          {match.away_team.substring(0, 2).toUpperCase()}
                        </div>
                        <span className="team-name">{match.away_team}</span>
                      </div>
                    </div>

                    <div className="match-footer">
                      <span className="elo-comparison">基准数据未加载</span>
                      <button 
                        className="btn-action"
                        onClick={() => onSelectMatch({
                          home_team: match.home_team,
                          away_team: match.away_team,
                          home_elo: 1500,
                          away_elo: 1500,
                          expected_home_goals: 1.0,
                          expected_away_goals: 1.0
                        })}
                      >
                        强制模拟
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="glass-panel" style={{ padding: '32px' }}>
              <div style={{ textAlign: 'center', color: 'var(--text-secondary)', marginBottom: '24px' }}>
                {activeLeague === 'CL'
                  ? '欧冠当前无已安排的比赛，或赛季间歇期。'
                  : `${activeLeague} 赛季已结束或暂无未来赛程。`}
                <div style={{ marginTop: '8px', fontSize: '0.8rem' }}>
                  你可以在下方手动选择两支球队进行预测，或切换到其他联赛。
                </div>
              </div>

              {/* Manual Prediction */}
              {modelFitted && teams.length > 0 && (
                <div style={{ maxWidth: '480px', margin: '0 auto' }}>
                  <h3 className="section-title" style={{ fontSize: '0.95rem', marginBottom: '12px', textAlign: 'center' }}>
                    <Play size={16} style={{ color: 'var(--accent)' }} />
                    手动选择比赛进行预测
                  </h3>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '12px' }}>
                    <select
                      value={manualHome}
                      onChange={(e) => { setManualHome(e.target.value); setManualPredResult(null); }}
                      style={{ flex: 1, padding: '8px 12px', borderRadius: '8px', background: 'rgba(15,23,42,0.6)', border: '1px solid var(--border-light)', color: 'var(--text-primary)' }}
                    >
                      <option value="">选择主队</option>
                      {teams.map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
                    </select>
                    <span style={{ fontWeight: 700, color: 'var(--text-muted)' }}>VS</span>
                    <select
                      value={manualAway}
                      onChange={(e) => { setManualAway(e.target.value); setManualPredResult(null); }}
                      style={{ flex: 1, padding: '8px 12px', borderRadius: '8px', background: 'rgba(15,23,42,0.6)', border: '1px solid var(--border-light)', color: 'var(--text-primary)' }}
                    >
                      <option value="">选择客队</option>
                      {teams.filter(t => t.name !== manualHome).map(t => <option key={t.name} value={t.name}>{t.name}</option>)}
                    </select>
                    <button
                      className="btn-action btn-primary-gradient"
                      onClick={handleManualPredict}
                      disabled={!manualHome || !manualAway || manualPredLoading}
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      {manualPredLoading ? '...' : '预测'}
                    </button>
                  </div>

                  {/* Result */}
                  {manualPredResult && !manualPredResult.error && (
                    <div style={{ marginTop: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                        <span>{manualPredResult.home_team} vs {manualPredResult.away_team}</span>
                        <span>期望进球: {manualPredResult.dixon_coles?.expected_home_goals?.toFixed(2)} - {manualPredResult.dixon_coles?.expected_away_goals?.toFixed(2)}</span>
                      </div>
                      <PredictionGauge
                        homeWinProb={manualPredResult.dixon_coles?.home_win || 0}
                        drawProb={manualPredResult.dixon_coles?.draw || 0}
                        awayWinProb={manualPredResult.dixon_coles?.away_win || 0}
                      />
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>ELO: {manualPredResult.elo?.home_rating?.toFixed(0)} vs {manualPredResult.elo?.away_rating?.toFixed(0)}</span>
                        <span>ELO 胜率: {(manualPredResult.elo?.home_win * 100)?.toFixed(0)}% 主胜</span>
                      </div>
                      <button
                        className="btn-action"
                        style={{ width: '100%', marginTop: '12px' }}
                        onClick={() => onSelectMatch({
                          home_team: manualPredResult.home_team,
                          away_team: manualPredResult.away_team,
                          home_elo: manualPredResult.elo?.home_rating || 1500,
                          away_elo: manualPredResult.elo?.away_rating || 1500,
                          expected_home_goals: manualPredResult.dixon_coles?.expected_home_goals || 1.0,
                          expected_away_goals: manualPredResult.dixon_coles?.expected_away_goals || 1.0
                        })}
                      >
                        <Play size={12} /> 进入模拟微调面板
                      </button>
                    </div>
                  )}
                  {manualPredResult?.error && (
                    <div style={{ marginTop: '12px', padding: '10px', borderRadius: '8px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', fontSize: '0.85rem', textAlign: 'center' }}>
                      {manualPredResult.error}
                    </div>
                  )}
                </div>
              )}

              <div style={{ marginTop: '20px', textAlign: 'center' }}>
                <button className="btn-action" onClick={handleSync}>
                  <RefreshCw size={14} /> 重新同步
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar Controls & Accuracy */}
        <div className="dashboard-sidebar">
          
          {/* Controls Panel */}
          <div className="glass-panel">
            <h3 className="section-title" style={{ fontSize: '1.05rem', marginBottom: '16px' }}>
              <Cpu size={18} style={{ color: 'var(--primary)' }} />
              数据同步与模型训练
            </h3>
            
            <div className="control-panel">
              <div className="status-indicator">
                <span className={`status-dot ${modelFitted ? 'active' : ''}`}></span>
                <span>当前联赛实力估值模型: {modelFitted ? '已训练 (Fitted)' : '未准备 (Not Fitted)'}</span>
              </div>

              <button 
                className="control-btn"
                onClick={handleSync}
                disabled={syncLoading || trainLoading}
              >
                <Database size={16} />
                {syncLoading ? '正在同步数据...' : '1. 同步英超/西甲数据'}
              </button>

              <button 
                className="control-btn btn-primary-gradient"
                onClick={handleTrain}
                disabled={syncLoading || trainLoading}
              >
                <Cpu size={16} />
                {trainLoading ? '正在训练拟合中...' : '2. 拟合 Dixon-Coles 模型'}
              </button>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>系统实时运行日志:</span>
                <div className="console-output">
                  {logText}
                </div>
              </div>
            </div>
          </div>

          {/* Accuracy Stats Panel */}
          {accuracy && (
            <div className="glass-panel" style={{ background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.45), rgba(6, 182, 212, 0.05))' }}>
              <h3 className="section-title" style={{ fontSize: '1.05rem', marginBottom: '12px' }}>
                <Award size={18} style={{ color: 'var(--accent)' }} />
                布莱顿量化回测效果
              </h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>模型回测预测总数:</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700' }}>{accuracy.total_predictions} 场</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>主平客准确预测:</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', color: 'var(--win-home)' }}>{accuracy.correct} 场</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-light)', paddingTop: '10px' }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: '600' }}>总体基准胜率 (Hit Rate):</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.3rem', fontWeight: '800', color: 'var(--accent)' }}>
                    {(accuracy.accuracy * 100).toFixed(1)}%
                  </span>
                </div>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: '1.3' }}>
                  * 注: 对于三项胜率预测(主胜/平局/客胜)，命中率高于 52% 即可跑赢庄家，55% 以上属于专业基金量化水平。
                </span>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
