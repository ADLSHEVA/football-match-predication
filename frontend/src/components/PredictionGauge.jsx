import React from 'react';
import { useT } from '../i18n.jsx';

/**
 * PredictionGauge Component
 * Renders a segmented horizontal bar representing the probability percentages
 * for home win, draw, and away win with animated transitions.
 */
export default function PredictionGauge({ homeWinProb = 0.33, drawProb = 0.34, awayWinProb = 0.33 }) {
  const { t } = useT();
  // Ensure we normalize values to sum to 1 in case of minor floating point rounding
  const total = homeWinProb + drawProb + awayWinProb;
  const hPct = total > 0 ? (homeWinProb / total) * 100 : 33.3;
  const dPct = total > 0 ? (drawProb / total) * 100 : 33.3;
  const aPct = total > 0 ? (awayWinProb / total) * 100 : 33.3;

  return (
    <div className="prediction-gauge-wrapper">
      <div className="gauge-bar">
        <div
          className="gauge-segment home"
          style={{ width: `${hPct}%` }}
          title={`${t('主队胜率: ')}${hPct.toFixed(1)}%`}
        />
        <div
          className="gauge-segment draw"
          style={{ width: `${dPct}%` }}
          title={`${t('平局概率: ')}${dPct.toFixed(1)}%`}
        />
        <div
          className="gauge-segment away"
          style={{ width: `${aPct}%` }}
          title={`${t('客队胜率: ')}${aPct.toFixed(1)}%`}
        />
      </div>
      <div className="gauge-labels">
        <span className="gauge-label">
          <span className="label-dot home"></span>
          {t('主胜')} {hPct.toFixed(1)}%
        </span>
        <span className="gauge-label">
          <span className="label-dot draw"></span>
          {t('平局')} {dPct.toFixed(1)}%
        </span>
        <span className="gauge-label">
          <span className="label-dot away"></span>
          {t('客胜')} {aPct.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}
