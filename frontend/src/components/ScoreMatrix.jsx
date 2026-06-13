import React, { useState } from 'react';
import { useT } from '../i18n.jsx';

/**
 * ScoreMatrix Component
 * Renders an 8x8 heatmap representing the probability of exact match scores.
 * Rows represent Home goals (0-7), Columns represent Away goals (0-7).
 */
export default function ScoreMatrix({
  matrix = Array(8).fill(null).map(() => Array(8).fill(0)),
  homeTeam = '主队',
  awayTeam = '客队'
}) {
  const { t } = useT();
  const [hoveredCell, setHoveredCell] = useState(null);

  // Flatten the matrix to find the maximum value for color normalization
  const flatVals = matrix ? matrix.flat() : [];
  const maxVal = flatVals.length > 0 ? Math.max(...flatVals) : 1;

  // Render headers
  const awayGoalsHeaders = Array.from({ length: 8 }, (_, i) => i);
  const homeGoalsRows = Array.from({ length: 8 }, (_, i) => i);

  const getCellColor = (val) => {
    if (val === 0) return 'rgba(255, 255, 255, 0.02)';
    // Scale alpha between 0.05 and 0.95 based on maxVal
    const ratio = maxVal > 0 ? val / maxVal : 0;
    const alpha = 0.08 + ratio * 0.82;

    // Choose primary neon glow color (cyan for high probability, fading to dark blue-gray)
    return `rgba(6, 182, 212, ${alpha})`;
  };

  const handleCellHover = (homeGoals, awayGoals, prob) => {
    setHoveredCell({
      homeGoals,
      awayGoals,
      prob: (prob * 100).toFixed(2),
      // store the Chinese key; translated at render via t()
      outcome: homeGoals > awayGoals ? '主胜' : homeGoals === awayGoals ? '平局' : '客胜'
    });
  };

  return (
    <div className="heatmap-container">
      <div className="section-header" style={{ marginBottom: '8px' }}>
        <span className="section-title" style={{ fontSize: '1rem' }}>{t('比分概率分布图 (Heatmap)')}</span>
        {hoveredCell ? (
          <span className="section-subtitle" style={{ color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>
            {homeTeam} {hoveredCell.homeGoals} - {hoveredCell.awayGoals} {awayTeam} &rarr;{' '}
            <strong style={{ color: 'white' }}>{hoveredCell.prob}%</strong> ({t(hoveredCell.outcome)})
          </span>
        ) : (
          <span className="section-subtitle">{t('将鼠标悬停在单元格上以查看详细概率')}</span>
        )}
      </div>

      <div className="heatmap-scroll-wrapper">
        <div className="heatmap-grid-layout">
          {/* Top-left corner */}
          <div className="heatmap-label-cell corner">
            <span style={{ fontSize: '0.55rem', alignSelf: 'flex-end', paddingRight: '2px' }}>{t('客')} &rarr;</span>
            <span style={{ fontSize: '0.55rem', alignSelf: 'flex-start', paddingLeft: '2px' }}>&darr; {t('主')}</span>
          </div>

          {/* Away goals headers (columns) */}
          {awayGoalsHeaders.map((g) => (
            <div key={`away-h-${g}`} className="heatmap-label-cell">
              {g}
            </div>
          ))}

          {/* Matrix rows */}
          {homeGoalsRows.map((homeGoals) => (
            <React.Fragment key={`row-${homeGoals}`}>
              {/* Home goals header (row) */}
              <div className="heatmap-label-cell">
                {homeGoals}
              </div>

              {/* Score cells */}
              {awayGoalsHeaders.map((awayGoals) => {
                const prob = (matrix && matrix[homeGoals] && matrix[homeGoals][awayGoals]) || 0;
                const percent = prob * 100;
                const isHovered = hoveredCell && hoveredCell.homeGoals === homeGoals && hoveredCell.awayGoals === awayGoals;

                return (
                  <div
                    key={`cell-${homeGoals}-${awayGoals}`}
                    className="heatmap-cell"
                    style={{
                      backgroundColor: getCellColor(prob),
                      outline: isHovered ? '2px solid var(--text-primary)' : 'none'
                    }}
                    onMouseEnter={() => handleCellHover(homeGoals, awayGoals, prob)}
                    onMouseLeave={() => setHoveredCell(null)}
                  >
                    {percent > 0.05 ? (
                      <>
                        <span className="heatmap-cell-prob">{percent.toFixed(1)}%</span>
                      </>
                    ) : (
                      <span className="heatmap-cell-prob" style={{ opacity: 0.15 }}>-</span>
                    )}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}
