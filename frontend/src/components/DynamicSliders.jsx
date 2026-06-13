import React from 'react';
import { useT } from '../i18n.jsx';

/**
 * DynamicSliders Component
 * Interactive sliders and toggles for the Starlizard-style analyst panel (Human-in-the-Loop).
 * Updates parent state on change.
 */
export default function DynamicSliders({ adjustments, onChange, homeTeam = '主队', awayTeam = '客队' }) {
  const { t } = useT();
  const handleSliderChange = (field, val) => {
    onChange({
      ...adjustments,
      [field]: parseFloat(val)
    });
  };

  const handleToggleChange = (field, checked) => {
    onChange({
      ...adjustments,
      [field]: checked
    });
  };

  return (
    <div className="adjustments-panel">

      {/* Home Team Section */}
      <div className="adj-section">
        <h3 className="adj-section-title" style={{ color: 'var(--win-home)' }}>{homeTeam} {t('临场状态')}</h3>
        <div className="slider-group">

          {/* Attack Adjustment */}
          <div className="slider-item">
            <div className="slider-label-row">
              <span>{t('进攻系数 (Attack Modifier)')}</span>
              <span>{adjustments.home_attack_adj.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              className="input-slider"
              min="0.5"
              max="1.5"
              step="0.05"
              value={adjustments.home_attack_adj}
              onChange={(e) => handleSliderChange('home_attack_adj', e.target.value)}
              style={{ accentColor: 'var(--win-home)' }}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {t('1.0=基准 | 0.8=主力缺阵 | 1.2=状态爆棚')}
            </span>
          </div>

          {/* Defense Adjustment */}
          <div className="slider-item">
            <div className="slider-label-row">
              <span>{t('防守系数 (Defense Modifier)')}</span>
              <span>{adjustments.home_defense_adj.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              className="input-slider"
              min="0.5"
              max="1.5"
              step="0.05"
              value={adjustments.home_defense_adj}
              onChange={(e) => handleSliderChange('home_defense_adj', e.target.value)}
              style={{ accentColor: 'var(--win-home)' }}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {t('1.0=基准 | 1.2=漏斗防线 | 0.8=防守铜墙铁壁')}
            </span>
          </div>

          {/* Stamina Decay */}
          <div className="slider-item">
            <div className="slider-label-row">
              <span>{t('体能衰减 (Stamina Decay)')}</span>
              <span>{(adjustments.stamina_decay_home * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              className="input-slider"
              min="0.0"
              max="0.3"
              step="0.05"
              value={adjustments.stamina_decay_home}
              onChange={(e) => handleSliderChange('stamina_decay_home', e.target.value)}
              style={{ accentColor: 'var(--win-home)' }}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {t('后半场疲劳度。0=正常 | 0.15=双线作战/体能危机')}
            </span>
          </div>

        </div>
      </div>

      {/* Away Team Section */}
      <div className="adj-section">
        <h3 className="adj-section-title" style={{ color: 'var(--win-away)' }}>{awayTeam} {t('临场状态')}</h3>
        <div className="slider-group">

          {/* Attack Adjustment */}
          <div className="slider-item">
            <div className="slider-label-row">
              <span>{t('进攻系数 (Attack Modifier)')}</span>
              <span>{adjustments.away_attack_adj.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              className="input-slider"
              min="0.5"
              max="1.5"
              step="0.05"
              value={adjustments.away_attack_adj}
              onChange={(e) => handleSliderChange('away_attack_adj', e.target.value)}
              style={{ accentColor: 'var(--win-away)' }}
            />
          </div>

          {/* Defense Adjustment */}
          <div className="slider-item">
            <div className="slider-label-row">
              <span>{t('防守系数 (Defense Modifier)')}</span>
              <span>{adjustments.away_defense_adj.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              className="input-slider"
              min="0.5"
              max="1.5"
              step="0.05"
              value={adjustments.away_defense_adj}
              onChange={(e) => handleSliderChange('away_defense_adj', e.target.value)}
              style={{ accentColor: 'var(--win-away)' }}
            />
          </div>

          {/* Stamina Decay */}
          <div className="slider-item">
            <div className="slider-label-row">
              <span>{t('体能衰减 (Stamina Decay)')}</span>
              <span>{(adjustments.stamina_decay_away * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range"
              className="input-slider"
              min="0.0"
              max="0.3"
              step="0.05"
              value={adjustments.stamina_decay_away}
              onChange={(e) => handleSliderChange('stamina_decay_away', e.target.value)}
              style={{ accentColor: 'var(--win-away)' }}
            />
          </div>

        </div>
      </div>

      {/* General / Tactical Section */}
      <div className="adj-section">
        <h3 className="adj-section-title" style={{ color: 'var(--accent)' }}>{t('比赛全局战术')}</h3>
        <div className="slider-group">

          {/* Tactical Conservatism */}
          <div className="slider-item">
            <div className="slider-label-row">
              <span>{t('战术保守度 (Tempo / Openness)')}</span>
              <span>{adjustments.tactical_conservatism.toFixed(2)}x</span>
            </div>
            <input
              type="range"
              className="input-slider"
              min="0.5"
              max="1.5"
              step="0.05"
              value={adjustments.tactical_conservatism}
              onChange={(e) => handleSliderChange('tactical_conservatism', e.target.value)}
              style={{ accentColor: 'var(--accent)' }}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {t('两队进球倾向。0.7=沉闷防守大战 | 1.3=对攻大球局')}
            </span>
          </div>

          {/* Park the Bus Toggle & Minute */}
          <div className="switch-item">
            <div className="switch-label-block">
              <span className="switch-title">{t('领先队死守战术 (Park the Bus)')}</span>
              <span className="switch-desc">{t('领先一球后是否收缩防守')}</span>
            </div>
            <label className="switch-control">
              <input
                type="checkbox"
                checked={adjustments.park_the_bus_enabled}
                onChange={(e) => handleToggleChange('park_the_bus_enabled', e.target.checked)}
              />
              <span className="switch-slider"></span>
            </label>
          </div>

          {adjustments.park_the_bus_enabled && (
            <div className="slider-item" style={{ animation: 'pulse 1s ease-out 1' }}>
              <div className="slider-label-row">
                <span>{t('死守触发时间 (Trigger Minute)')}</span>
                <span>{t('第 ')}{adjustments.park_the_bus_minute}{t(' 分钟')}</span>
              </div>
              <input
                type="range"
                className="input-slider"
                min="45"
                max="85"
                step="5"
                value={adjustments.park_the_bus_minute}
                onChange={(e) => handleSliderChange('park_the_bus_minute', e.target.value)}
                style={{ accentColor: 'var(--primary)' }}
              />
            </div>
          )}

        </div>
      </div>

    </div>
  );
}
