import React, { useState, useEffect } from 'react';
import { TrendingUp, BarChart2, Globe, Languages } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import MatchSimulator from './pages/MatchSimulator';
import Standings from './pages/Standings';
import WorldCup from './pages/WorldCup';
import { useT } from './i18n.jsx';

export default function App() {
  const { t, lang, setLang } = useT();
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'simulator' | 'standings' | 'worldcup'
  const [activeLeague, setActiveLeague] = useState('PL');
  const [selectedMatch, setSelectedMatch] = useState(null);

  // Update document title for SEO and user visibility
  useEffect(() => {
    let title = `EuroGoal Predictor - ${t('欧洲足球比赛胜率量化预测系统')}`;
    if (currentView === 'simulator' && selectedMatch) {
      title = `${selectedMatch.home_team} vs ${selectedMatch.away_team} - ${t('实时模拟预测')} - EuroGoal`;
    } else if (currentView === 'standings') {
      title = `${t('联赛积分战力分布')} - EuroGoal`;
    } else if (currentView === 'worldcup') {
      title = `${t('2026 世界杯全赛程量化模拟')} - EuroGoal`;
    }
    document.title = title;
  }, [currentView, selectedMatch, t]);

  const handleSelectMatch = (match) => {
    setSelectedMatch(match);
    setCurrentView('simulator');
  };

  const handleTabChange = (view) => {
    setCurrentView(view);
    if (view !== 'simulator') {
      setSelectedMatch(null);
    }
  };

  return (
    <div className="app-container">
      {/* App Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">EG</div>
          <div className="brand-text">
            <h1>
              EuroGoal Predictor
              <span className="brand-badge" id="app-quant-badge">{t('v3.0布莱顿量化版')}</span>
            </h1>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Top level Navigation */}
          <nav className="navigation-tabs">
            <button
              id="nav-tab-dashboard"
              className={`nav-tab ${currentView === 'dashboard' || currentView === 'simulator' ? 'active' : ''}`}
              onClick={() => handleTabChange('dashboard')}
            >
              <BarChart2 size={16} />
              {t('预测大厅')}
            </button>
            <button
              id="nav-tab-standings"
              className={`nav-tab ${currentView === 'standings' ? 'active' : ''}`}
              onClick={() => handleTabChange('standings')}
            >
              <TrendingUp size={16} />
              {t('战力与积分榜')}
            </button>
            <button
              id="nav-tab-worldcup"
              className={`nav-tab ${currentView === 'worldcup' ? 'active' : ''}`}
              onClick={() => handleTabChange('worldcup')}
            >
              <Globe size={16} />
              {t('世界杯 2026')}
            </button>
          </nav>

          {/* Language toggle */}
          <button
            className="lang-toggle"
            onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
            title={lang === 'zh' ? t('切换到英文') : t('切换到中文')}
          >
            <Languages size={15} />
            {lang === 'zh' ? 'EN' : '中'}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1 }}>
        {currentView === 'dashboard' && (
          <Dashboard
            activeLeague={activeLeague}
            setActiveLeague={setActiveLeague}
            onSelectMatch={handleSelectMatch}
            setView={setCurrentView}
          />
        )}

        {currentView === 'simulator' && selectedMatch && (
          <MatchSimulator
            match={selectedMatch}
            activeLeague={activeLeague}
            onBack={() => handleTabChange('dashboard')}
          />
        )}

        {currentView === 'standings' && (
          <Standings
            activeLeague={activeLeague}
            setActiveLeague={setActiveLeague}
          />
        )}

        {currentView === 'worldcup' && <WorldCup />}
      </main>

      {/* Premium Footer */}
      <footer style={{ marginTop: '50px', borderTop: '1px solid var(--border-light)', paddingTop: '20px', paddingBottom: '30px', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        <p>EuroGoal Predictor &copy; 2026. Powered by xG-Dixon-Coles &amp; Monte Carlo Vectorized Engine.</p>
        <p style={{ marginTop: '4px', fontSize: '0.75rem' }}>{t('由 Gemini 3.5 Flash 编写交互前端 · Claude 4.6 Opus 编写预测模型后端')}</p>
      </footer>
    </div>
  );
}
