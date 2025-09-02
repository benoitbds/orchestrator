'use client';
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { getDict } from '@/i18n/dictionary';

interface UploadDropzoneProps {
  onFilesAccepted: (files: File[]) => void;
}

export function UploadDropzone({ onFilesAccepted }: UploadDropzoneProps) {
  const { lang } = useLanguage();
  const t = getDict(lang);
  const [files, setFiles] = useState<File[]>([]);

  const onDrop = useCallback(
    (accepted: File[]) => {
      setFiles(prev => [...prev, ...accepted]);
      onFilesAccepted(accepted);
    },
    [onFilesAccepted]
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    multiple: true,
    noClick: true,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
  });

  const removeFile = (file: File) => {
    setFiles(prev => prev.filter(f => f !== file));
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps({
          className: `border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary ${
            isDragActive ? 'bg-muted' : ''
          }`,
          onClick: open,
          tabIndex: 0,
          onKeyDown: (e: any) => e.key === 'Enter' && open(),
        })}
      >
        <input {...getInputProps()} aria-label={t.chooseFile} />
        <p className="text-sm text-muted-foreground">
          {isDragActive ? t.dropHere : t.dragDropHint}
        </p>
      </div>
      {files.length > 0 && (
        <ul className="space-y-2 text-sm">
          {files.map(file => (
            <li key={file.name} className="flex items-center justify-between gap-2">
              <span>
                {file.name} ({Math.round(file.size / 1024)}KB)
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={lang === 'fr' ? 'Supprimer' : 'Remove'}
                onClick={() => removeFile(file)}
              >
                <X className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <Button type="button" onClick={open}>
        {t.chooseFile}
      </Button>
    </div>
  );
}
