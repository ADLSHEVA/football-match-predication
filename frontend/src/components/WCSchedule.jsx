import React, { useState, useEffect } from 'react';
import { CalendarClock, CheckCircle2, XCircle, Target, Activity, Gauge } from 'lucide-react';

const STAGE_LABEL = {
  GROUP_STAGE: '小组赛',
  LAST_32: '32 强',
  LAST_16: '16 强',
  QUARTER_FINALS: '1/4 决赛',
  SEMI_FINALS: '半决赛',
  THIRD_PLACE: '季军赛',
  FINAL: '决赛',
};

const RESULT_LABEL = { H: '主胜', D: '平局', A: '客胜' };

function predResultColor(r) {
  return r === 'H' ? 'var(--win-home)' : r === 'A' ? 'var(--win-away)' : 'var(--draw)';
}

/** One mini 1X2 probability bar (home/draw/away segments). */
function ProbBar({ p }) {
  if (!p) return null;
  const seg = (w, c) => ({ width: `${w * 100}%`, background: c, height: '100%' });
  return (
    <div style={{ display: 'flex', height: '5px', borderRadius: '3px', overflow: 'hidden', width: '100%', marginTop: '4px' }}>
      <div style={seg(p.p_home, 'var(--win-home)')} />
      <div style={seg(p.p_draw, 'var(--draw)')} />
      <div style={seg(p.p_away, 'var(--win-away)')} />
    </div>
  );
}

function FinishedRow({ f }) {
  const p = f.prediction;
  const homeWon = f.home_goals > f.away_goals;
  const awayWon = f.away_goals > f.home_goals;
  return (
    <div className="wc-fx-row wc-fx-finished">
      <span style={{ textAlign: 'right', fontWeight: homeWon ? 700 : 400, color: homeWon ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
        {f.home_team} {f.home_flag}
      </span>
      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '1rem', minWidth: '52px', textAlign: 'center' }}>
        {f.home_goals}-{f.away_goals}
      </span>
      <span style={{ fontWeight: awayWon ? 700 : 400, color: awayWon ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
        {f.away_flag} {f.away_team}
      </span>
      {p && (
        <span className="wc-fx-pred" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', justifyContent: 'flex-end' }}>
          <span title="赛前预测" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            预测 {RESULT_LABEL[p.pred_result]} {p.pred_home}-{p.pred_away}
          </span>
          {f.result_correct ? <CheckCircle2 size={15} style={{ color: 'var(--win-home)' }} /> : <XCircle size={15} style={{ color: 'var(--win-away)' }} />}
          {f.score_correct && <Target size={14} style={{ color: 'var(--accent)' }} title="精确比分命中" />}
        </span>
      )}
    </div>
  );
}

function UpcomingRow({ f }) {
  const p = f.prediction;
  return (
    <div className="wc-fx-row wc-fx-upcoming">
      <span className="wc-fx-time" style={{ fontSize: '0.72rem', color: f.live ? 'var(--win-away)' : 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontWeight: f.live ? 700 : 400 }}>
        {f.live ? '● 进行中' : f.cet}
      </span>
      <span style={{ textAlign: 'right' }}>{f.home_team} {f.home_flag}</span>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>vs</span>
      <span>{f.away_flag} {f.away_team}</span>
      {p ? (
        <span className="wc-fx-pred" style={{ fontSize: '0.7rem' }}>
          <span style={{ display: 'flex', justifyContent: 'space-between', gap: '6px' }}>
            <span style={{ color: predResultColor(p.pred_result), fontWeight: 700 }}>{RESULT_LABEL[p.pred_result]}</span>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{p.pred_home}-{p.pred_away}</span>
          </span>
          <ProbBar p={p} />
        </span>
      ) : <span />}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ flex: 1, textAlign: 'center' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 800, color: color || 'var(--text-primary)' }}>{value}</div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{label}</div>
    </div>
  );
}

export default function WCSchedule({ refreshNonce = 0 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAllUpcoming, setShowAllUpcoming] = useState(false);
  const [showAllFinished, setShowAllFinished] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/worldcup/schedule?refresh=${refreshNonce > 0}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [refreshNonce]);

  if (loading && !data) {
    return (
      <div className="glass-panel loading-spinner-overlay" style={{ height: '200px' }}>
        <div className="spinner"></div><span>正在加载真实赛程与赛果...</span>
      </div>
    );
  }
  if (error) return <div className="alert-banner warning">加载赛程失败: {error}</div>;
  if (!data) return null;

  const fixtures = data.fixtures || [];
  const acc = data.accuracy || {};
  const calib = data.calibration || {};
  const finished = fixtures.filter((f) => f.finished).reverse();
  const upcoming = fixtures.filter((f) => !f.finished && f.home_team && f.away_team);

  const upcomingShown = showAllUpcoming ? upcoming : upcoming.slice(0, 20);
  const finishedShown = showAllFinished ? finished : finished.slice(0, 20);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {data.source === 'seed' && (
        <div className="alert-banner info">
          未获取到实时赛程（检查 FOOTBALL_DATA_API_KEY）。当前展示内置数据，无真实赛果与开赛时间。
        </div>
      )}

      {/* Accuracy & calibration scoreboard */}
      <div className="glass-panel" style={{ padding: '18px' }}>
        <h3 className="section-title" style={{ fontSize: '1rem', marginBottom: '14px' }}>
          <Gauge size={18} style={{ color: 'var(--accent)' }} />
          模型预测准确度 (随真实赛果自我校准)
        </h3>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <Stat label={`胜平负命中 (${acc.result_correct || 0}/${acc.n || 0})`} value={acc.result_hit_rate != null ? `${(acc.result_hit_rate * 100).toFixed(0)}%` : '—'} color="var(--win-home)" />
          <Stat label={`精确比分命中 (${acc.score_correct || 0}/${acc.n || 0})`} value={acc.score_hit_rate != null ? `${(acc.score_hit_rate * 100).toFixed(0)}%` : '—'} color="var(--accent)" />
          <Stat label="Brier 分 (越低越准)" value={acc.brier != null ? acc.brier.toFixed(3) : '—'} color="var(--draw)" />
          <Stat label="已校准场均进球" value={calib.base_goals != null ? calib.base_goals.toFixed(2) : '—'} />
          <Stat label="实测场均进球/队" value={calib.obs_goals_per_team != null ? calib.obs_goals_per_team.toFixed(2) : '—'} />
        </div>
        <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '10px' }}>
          每场赛前用「截至该场之前」的实力做预测并锁定；赛后与真实比分对比。Elo 随每场结果更新，进球模型按实测比分收缩校准——这就是「基于实际结果改进预测」。
        </p>
      </div>

      {/* Upcoming */}
      <div className="glass-panel" style={{ padding: '18px' }}>
        <h3 className="section-title" style={{ fontSize: '1rem', marginBottom: '4px' }}>
          <CalendarClock size={18} style={{ color: 'var(--primary)' }} />
          即将开赛 · 赛前预测 ({upcoming.length})
        </h3>
        <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '8px' }}>开赛时间为中欧夏令时 (CEST, UTC+2)。颜色条为主胜/平/客胜概率。</p>
        {upcomingShown.map((f) => <UpcomingRow key={f.fd_id} f={f} />)}
        {upcoming.length > 20 && (
          <button className="btn-action" onClick={() => setShowAllUpcoming((v) => !v)} style={{ marginTop: '10px', width: '100%', justifyContent: 'center', display: 'flex' }}>
            {showAllUpcoming ? '收起' : `显示全部 ${upcoming.length} 场`}
          </button>
        )}
      </div>

      {/* Finished */}
      <div className="glass-panel" style={{ padding: '18px' }}>
        <h3 className="section-title" style={{ fontSize: '1rem', marginBottom: '4px' }}>
          <Activity size={18} style={{ color: 'var(--win-home)' }} />
          已结束 · 预测 vs 实际 ({finished.length})
        </h3>
        <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
          <CheckCircle2 size={12} style={{ color: 'var(--win-home)', verticalAlign: 'middle' }} /> 胜平负命中 ·
          <Target size={12} style={{ color: 'var(--accent)', verticalAlign: 'middle' }} /> 精确比分命中
        </p>
        {finished.length === 0
          ? <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '8px 0' }}>暂无已结束的比赛。</p>
          : finishedShown.map((f) => <FinishedRow key={f.fd_id} f={f} />)}
        {finished.length > 20 && (
          <button className="btn-action" onClick={() => setShowAllFinished((v) => !v)} style={{ marginTop: '10px', width: '100%', justifyContent: 'center', display: 'flex' }}>
            {showAllFinished ? '收起' : `显示全部 ${finished.length} 场`}
          </button>
        )}
      </div>
    </div>
  );
}
