import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { EN } from './translations';

/**
 * Lightweight i18n (no external dependency).
 *
 * The Chinese source string IS the key: `t('预测大厅')`. When the language is
 * English we look it up in the EN table; when it's Chinese (or a key is
 * missing) we return the original string. This keeps the JSX readable and
 * makes any untranslated string degrade gracefully to Chinese.
 */
const I18nContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    try { return localStorage.getItem('lang') || 'zh'; } catch { return 'zh'; }
  });

  useEffect(() => {
    document.documentElement.lang = lang === 'en' ? 'en' : 'zh-CN';
  }, [lang]);

  const setLang = useCallback((l) => {
    try { localStorage.setItem('lang', l); } catch { /* ignore */ }
    setLangState(l);
  }, []);

  const t = useCallback((s) => (lang === 'en' ? (EN[s] ?? s) : s), [lang]);

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useT() {
  const ctx = useContext(I18nContext);
  // Safe fallback if used outside the provider (renders Chinese).
  if (!ctx) return { lang: 'zh', setLang: () => {}, t: (s) => s };
  return ctx;
}
