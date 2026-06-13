import React, { useState, useEffect, useCallback } from 'react';
import { Globe, RefreshCw, Trophy, Users, GitBranch, AlertTriangle, Cpu, CalendarClock } from 'lucide-react';
import WCChampionshipOdds from '../components/WCChampionshipOdds';
import WCGroupStage from '../components/WCGroupStage';
import WCBracket from '../components/WCBracket';
import WCSchedule from '../components/WCSchedule';

const SIM_OPTIONS = [10000, 20000, 50000];

const SOURCE_LABELS = {
  live: { text: '实时数据', color: 'var(--win-home)' },
  hybrid: { text: '实时结果 + 种子实力', color: 'var(--accent)' },
  seed: { text: '内置种子数据', color: 'var(--draw)' },
};

export default function WorldCup() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [sims, setSims] = useState(20000);
  const [section, setSection] = useState('odds'); // 'odds' | 'groups' | 'bracket' | 'live'
  const [refreshNonce, setRefreshNonce] = useState(0); // bumped to refresh the live schedule

  const load = useCallback(async (refresh = false, n = sims) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/worldcup/simulate?num_simulations=${n}&refresh=${refresh}`);
      if (!res.ok) {
        let msg = `服务器错误 (HTTP ${res.status})`;
        try { msg = (await res.json()).detail || msg; } catch { /* ignore */ }
        throw new Error(msg);
      }
      setData(await res.json());
    } catch (e) {
      console.error(e);
      setErrorMsg(e.message || '无法连接到后端 API。');
    } finally {
      setLoading(false);
    }
  }, [sims]);

  useEffect(() => { load(false, sims); }, [sims, load]);

  const handleRefresh = () => {
    setRefreshNonce((n) => n + 1);  // refresh the live schedule component
    load(true, sims);               // refresh tournament state + re-simulate
  };

  const sourceMeta = data ? (SOURCE_LABELS[data.source] || SOURCE_LABELS.seed) : null;

  return (
    <div className="dashboard-main-wrapper">

      {/* Header */}
      <div className="section-header" style={{ marginBottom: '20px' }}>
        <div>
          <h2 className="section-title">
            <Globe size={22} style={{ color: 'var(--primary)' }} />
            2026 世界杯 · 全赛程量化模拟
            {data?.season && <span className="brand-badge">{data.season}</span>}
          </h2>
          <span className="section-subtitle">
            48 强 / 12 组 · 基于 Elo 实力先验的蒙特卡洛全赛事推演（小组赛 → 淘汰赛 → 夺冠）。
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <select
            value={sims}
            onChange={(e) => setSims(Number(e.target.value))}
            disabled={loading}
            style={{
              padding: '7px 10px', borderRadius: '8px', background: 'rgba(15,23,42,0.6)',
              border: '1px solid var(--border-light)', color: 'var(--text-primary)', fontSize: '0.8rem',
            }}
          >
            {SIM_OPTIONS.map((n) => (
              <option key={n} value={n}>{n.toLocaleString()} 次模拟</option>
            ))}
          </select>
          <button className="btn-action" onClick={handleRefresh} disabled={loading} title="刷新实时数据并重新模拟">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            {loading ? '模拟中...' : '刷新'}
          </button>
        </div>
      </div>

      {/* Status badges */}
      {data && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', marginBottom: '16px', fontSize: '0.8rem' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: sourceMeta.color }} />
            数据源: <strong style={{ color: sourceMeta.color }}>{sourceMeta.text}</strong>
          </span>
          <span style={{ color: 'var(--text-muted)' }}>已录入赛果: <strong style={{ color: 'var(--text-secondary)' }}>{data.matches_played}</strong> 场</span>
          <span style={{ color: 'var(--text-muted)' }}>模拟次数: <strong style={{ color: 'var(--text-secondary)' }}>{data.num_simulations?.toLocaleString()}</strong></span>
        </div>
      )}

      {/* Errors / seed-mode notice */}
      {errorMsg && (
        <div className="alert-banner warning" style={{ marginBottom: '16px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={18} /> {errorMsg}
          </span>
          <button className="btn-action" onClick={() => load(false, sims)} style={{ padding: '4px 10px' }}>重试</button>
        </div>
      )}
      {data && data.source === 'seed' && !errorMsg && (
        <div className="alert-banner info" style={{ marginBottom: '16px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={18} />
            当前使用内置 2026 种子数据（分组为示意，非官方抽签）。配置 API_FOOTBALL_KEY 后点击「刷新」即可接入真实赛程与赛果。
          </span>
        </div>
      )}

      {/* Section tabs */}
      <div className="navigation-tabs" style={{ display: 'inline-flex', marginBottom: '20px' }}>
        <button className={`nav-tab ${section === 'odds' ? 'active' : ''}`} onClick={() => setSection('odds')}>
          <Trophy size={15} /> 夺冠概率
        </button>
        <button className={`nav-tab ${section === 'groups' ? 'active' : ''}`} onClick={() => setSection('groups')}>
          <Users size={15} /> 小组赛
        </button>
        <button className={`nav-tab ${section === 'bracket' ? 'active' : ''}`} onClick={() => setSection('bracket')}>
          <GitBranch size={15} /> 淘汰赛对阵
        </button>
        <button className={`nav-tab ${section === 'live' ? 'active' : ''}`} onClick={() => setSection('live')}>
          <CalendarClock size={15} /> 实时赛况
        </button>
      </div>

      {/* Content */}
      {section === 'live' ? (
        <WCSchedule refreshNonce={refreshNonce} />
      ) : loading && !data ? (
        <div className="glass-panel loading-spinner-overlay" style={{ height: '300px' }}>
          <div className="spinner"></div>
          <span><Cpu size={14} className="animate-spin" /> 正在推演 {sims.toLocaleString()} 届世界杯...</span>
        </div>
      ) : data ? (
        <>
          {section === 'odds' && <WCChampionshipOdds teams={data.teams} />}
          {section === 'groups' && <WCGroupStage groups={data.groups} />}
          {section === 'bracket' && <WCBracket bracket={data.bracket} />}
        </>
      ) : null}
    </div>
  );
}
