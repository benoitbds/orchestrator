'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Lang } from '@/i18n/dictionary';

type LanguageCtx = { lang: Lang; setLang: (lang: Lang) => void };

const LanguageContext = createContext<LanguageCtx | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>('fr');

  useEffect(() => {
    const stored = localStorage.getItem('lang') as Lang | null;
    if (stored) {
      setLangState(stored);
    }
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    localStorage.setItem('lang', l);
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
