'use client';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useLanguage } from '@/context/LanguageContext';

export function LanguageToggle() {
  const { lang, setLang } = useLanguage();
  return (
    <div role="group" aria-label="language selector" className="inline-flex rounded-md shadow-soft">
      <Button
        type="button"
        variant={lang === 'fr' ? 'default' : 'secondary'}
        className={cn('px-3 py-1 rounded-l-md', lang !== 'fr' && 'bg-muted')}
        aria-pressed={lang === 'fr'}
        onClick={() => setLang('fr')}
      >
        FR
      </Button>
      <Button
        type="button"
        variant={lang === 'en' ? 'default' : 'secondary'}
        className={cn('px-3 py-1 rounded-r-md', lang !== 'en' && 'bg-muted')}
        aria-pressed={lang === 'en'}
        onClick={() => setLang('en')}
      >
        EN
      </Button>
    </div>
  );
}
