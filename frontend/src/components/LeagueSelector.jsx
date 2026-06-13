import React from 'react';
import { useT } from '../i18n.jsx';

const LEAGUES = [
  { code: 'PL', name: '英超 (Premier League)', country: '🏴󠁧󠁢󠁥󠁮󠁧󠁿 英格兰' },
  { code: 'PD', name: '西甲 (La Liga)', country: '🇪🇸 西班牙' },
  { code: 'BL1', name: '德甲 (Bundesliga)', country: '🇩🇪 德国' },
  { code: 'SA', name: '意甲 (Serie A)', country: '🇮🇹 意大利' },
  { code: 'FL1', name: '法甲 (Ligue 1)', country: '🇫🇷 法国' },
  { code: 'CL', name: '欧冠 (Champions League)', country: '🇪🇺 欧洲' },
];

/**
 * LeagueSelector Component
 * Horizontal scrolling list of leagues to filter matches and standings.
 */
export default function LeagueSelector({ activeLeague = 'PL', onChange }) {
  const { t } = useT();
  return (
    <div className="league-selector-container">
      {LEAGUES.map((league) => {
        const isActive = league.code === activeLeague;
        return (
          <div
            key={league.code}
            className={`league-card ${isActive ? 'active' : ''}`}
            onClick={() => onChange(league.code)}
          >
            <div className="league-icon">
              {league.code}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span className="league-name">{t(league.name)}</span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{t(league.country)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
export { LEAGUES };
