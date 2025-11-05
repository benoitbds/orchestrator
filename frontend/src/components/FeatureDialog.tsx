"use client";
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { BacklogItem } from '@/models/backlogItem';
import { useItems } from '@/lib/hooks';
import { useBacklog } from '@/context/BacklogContext';
import { validateItem } from '@/lib/api';
import { TemplateSelector } from '@/components/TemplateSelector';
import { featureTemplates, getFeatureTemplate } from '@/lib/templates';
import dynamic from 'next/dynamic';
import { toast } from 'sonner';
import { mutate } from 'swr';

const Loader2 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Loader2 })),
  { ssr: false }
);
const Info = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Info })),
  { ssr: false }
);
const Plus = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Plus })),
  { ssr: false }
);
const X = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.X })),
  { ssr: false }
);
const Heart = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Heart })),
  { ssr: false }
);
const FileText = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.FileText })),
  { ssr: false }
);
const CheckCircle2 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.CheckCircle2 })),
  { ssr: false }
);
const Image = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Image })),
  { ssr: false }
);
const BarChart3 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.BarChart3 })),
  { ssr: false }
);

interface FeatureDialogProps {
  isOpen: boolean;
  onClose: () => void;
  item?: BacklogItem;
  projectId: number;
  onSave: (item: Partial<BacklogItem>) => Promise<void>;
}

export function FeatureDialog({ isOpen, onClose, item, projectId, onSave }: FeatureDialogProps) {
  const { deleteItem, refreshItems } = useBacklog();
  const { data: items } = useItems(projectId);
  
  const [title, setTitle] = useState('');
  const [parentId, setParentId] = useState<number | null>(null);
  const [tags, setTags] = useState('');
  const [businessBenefit, setBusinessBenefit] = useState('');
  const [personas, setPersonas] = useState<string[]>(['']);
  const [expectedImpact, setExpectedImpact] = useState<'Faible' | 'Moyen' | 'Fort' | 'Critique'>('Moyen');
  const [description, setDescription] = useState('');
  const [mainFeatures, setMainFeatures] = useState<string[]>(['']);
  const [nonFunctionalReqs, setNonFunctionalReqs] = useState('');
  const [acceptanceCriteria, setAcceptanceCriteria] = useState<string[]>(['']);
  const [designLinks, setDesignLinks] = useState<string[]>(['']);
  const [priority, setPriority] = useState<'Must' | 'Should' | 'Could' | 'Won\'t'>('Should');
  const [businessValue, setBusinessValue] = useState<number>(5);
  const [effortEstimate, setEffortEstimate] = useState<'XS' | 'S' | 'M' | 'L' | 'XL'>('M');
  const [status, setStatus] = useState<'Backlog' | 'Analysis' | 'Ready' | 'In Progress' | 'Done'>('Backlog');
  const [releaseTarget, setReleaseTarget] = useState('');
  const [iteration, setIteration] = useState('');
  
  const [showMarkdownPreview, setShowMarkdownPreview] = useState(false);
  const [sectionBenefit, setSectionBenefit] = useState(true);
  const [sectionDescription, setSectionDescription] = useState(true);
  const [sectionCriteria, setSectionCriteria] = useState(true);
  const [sectionAssets, setSectionAssets] = useState(false);
  const [sectionPlanning, setSectionPlanning] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [validating, setValidating] = useState(false);

  const handleTemplateSelect = (templateKey: string) => {
    const template = getFeatureTemplate(templateKey);
    if (!template) return;

    setBusinessBenefit(template.businessBenefit);
    setPersonas(template.personas);
    setExpectedImpact(template.expectedImpact);
    setDescription(template.descriptionTemplate);
    setMainFeatures(template.mainFeatures);
    setNonFunctionalReqs(template.nonFunctionalReqs);
    setAcceptanceCriteria(template.acceptanceCriteria);

    toast.success(`Template "${template.name}" appliqué. Personnalisez les placeholders.`);
  };

  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setParentId(item.parent_id);
      setTags('');
      setBusinessBenefit(item.benefit_hypothesis || '');
      setDescription(item.description || '');
      
      const criteria = item.acceptance_criteria || '';
      setAcceptanceCriteria(criteria ? criteria.split('\n').filter(c => c.trim()) : ['']);
      
      setReleaseTarget(item.program_increment || '');
      setStatus('Backlog');
      setPriority('Should');
      setBusinessValue(5);
      setEffortEstimate('M');
      setExpectedImpact('Moyen');
      
      setPersonas(['']);
      setMainFeatures(['']);
      setNonFunctionalReqs('');
      setDesignLinks(['']);
      setIteration('');
    } else {
      setTitle('');
      setParentId(null);
      setTags('');
      setBusinessBenefit('');
      setPersonas(['']);
      setExpectedImpact('Moyen');
      setDescription('');
      setMainFeatures(['']);
      setNonFunctionalReqs('');
      setAcceptanceCriteria(['']);
      setDesignLinks(['']);
      setPriority('Should');
      setBusinessValue(5);
      setEffortEstimate('M');
      setStatus('Backlog');
      setReleaseTarget('');
      setIteration('');
    }
  }, [item, isOpen]);

  const handleSubmit = async () => {
    const featureData = {
      id: item?.id,
      title,
      type: 'Feature' as const,
      description,
      project_id: projectId,
      parent_id: parentId,
      benefit_hypothesis: businessBenefit || undefined,
      acceptance_criteria: acceptanceCriteria.filter(c => c.trim()).join('\n') || undefined,
      program_increment: releaseTarget || undefined,
    };

    await onSave(featureData);
    onClose();
  };

  const requiresValidation = !!item && (item.ia_review_status === 'pending' || item.generated_by_ai);

  const handleValidate = async () => {
    if (!item) return;
    try {
      setValidating(true);
      await validateItem(item.id);
      await refreshItems();
      const keys = ['all', 'pending', 'approved'].map((review) => `/items?project_id=${projectId}&review=${review}`);
      keys.forEach((key) => mutate(key));
      toast.success('Feature validée');
      onClose();
    } catch {
      toast.error('Impossible de valider cette Feature');
    } finally {
      setValidating(false);
    }
  };

  const epics = items?.filter(i => i.type === 'Epic' || i.type === 'Capability') || [];
  const criteriaCount = acceptanceCriteria.filter(c => c.trim()).length;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[700px] max-h-[90vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b flex-shrink-0">
          <DialogTitle>{item ? 'Modifier' : 'Créer'} Feature</DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="space-y-6">
            {!item && (
              <TemplateSelector
                templates={featureTemplates}
                onSelectTemplate={handleTemplateSelect}
                type="Feature"
              />
            )}
            
            <div className="space-y-4">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Info className="h-4 w-4" />
                Identification
              </h3>
              <div className="space-y-3 pl-6">
                <div className="space-y-2">
                  <Label htmlFor="title">Titre de la Feature <span className="text-red-500">*</span></Label>
                  <Input
                    id="title"
                    placeholder="Ex: Gestion du panier d'achat multi-devises"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    required
                    className={!title.trim() ? 'border-red-300' : ''}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="type">Type d&apos;item</Label>
                  <Input
                    id="type"
                    value="Feature"
                    disabled
                    className="bg-gray-100 dark:bg-gray-800 cursor-not-allowed"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="parent">Epic parent <span className="text-red-500">*</span></Label>
                  <Select value={parentId?.toString() || "null"} onValueChange={(v: string) => setParentId(v === "null" ? null : Number(v))}>
                    <SelectTrigger id="parent" className={!parentId ? 'border-red-300' : ''}>
                      <SelectValue placeholder="Sélectionner un Epic" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="null">Aucun</SelectItem>
                      {epics.map(epic => (
                        <SelectItem key={epic.id} value={epic.id.toString()}>
                          {epic.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Chaque Feature doit appartenir à un Epic</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tags">Tags / Labels</Label>
                  <Input
                    id="tags"
                    placeholder="Ex: paiement, e-commerce, critique"
                    value={tags}
                    onChange={e => setTags(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">Séparer par des virgules pour catégoriser</p>
                </div>
              </div>
            </div>

            <AccordionItem value="benefit">
              <AccordionTrigger onClick={() => setSectionBenefit(!sectionBenefit)} open={sectionBenefit}>
                <div className="flex items-center gap-2">
                  <Heart className="h-4 w-4" />
                  Bénéfice Utilisateur
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionBenefit}>
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <Label htmlFor="businessBenefit">Bénéfice métier <span className="text-red-500">*</span></Label>
                    <Textarea
                      id="businessBenefit"
                      placeholder="Quel problème métier cette feature résout-elle ?&#10;&#10;Ex: Permet aux clients internationaux de visualiser les prix et payer dans leur devise locale, réduisant ainsi les frictions à l'achat et augmentant le taux de conversion de 20%."
                      value={businessBenefit}
                      onChange={e => setBusinessBenefit(e.target.value)}
                      className="text-sm h-20 resize-none"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Personas concernés</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setPersonas([...personas, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {personas.map((persona, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Input
                            placeholder={`Ex: Client international, Vendeur multi-pays`}
                            value={persona}
                            onChange={e => {
                              const newPersonas = [...personas];
                              newPersonas[index] = e.target.value;
                              setPersonas(newPersonas);
                            }}
                            className="text-sm"
                          />
                          {personas.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newPersonas = personas.filter((_, i) => i !== index);
                                setPersonas(newPersonas.length > 0 ? newPersonas : ['']);
                              }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="impact">Impact attendu</Label>
                    <Select value={expectedImpact} onValueChange={(v: 'Faible' | 'Moyen' | 'Fort' | 'Critique') => setExpectedImpact(v)}>
                      <SelectTrigger id="impact">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Faible">
                          <span className="flex items-center gap-2">
                            <Badge className="w-2 h-2 p-0 rounded-full bg-gray-400" />
                            Faible
                          </span>
                        </SelectItem>
                        <SelectItem value="Moyen">
                          <span className="flex items-center gap-2">
                            <Badge className="w-2 h-2 p-0 rounded-full bg-yellow-500" />
                            Moyen
                          </span>
                        </SelectItem>
                        <SelectItem value="Fort">
                          <span className="flex items-center gap-2">
                            <Badge className="w-2 h-2 p-0 rounded-full bg-orange-500" />
                            Fort
                          </span>
                        </SelectItem>
                        <SelectItem value="Critique">
                          <span className="flex items-center gap-2">
                            <Badge variant="destructive" className="w-2 h-2 p-0 rounded-full" />
                            Critique
                          </span>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="description">
              <AccordionTrigger onClick={() => setSectionDescription(!sectionDescription)} open={sectionDescription}>
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Description Fonctionnelle
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionDescription}>
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="description">Description détaillée</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowMarkdownPreview(!showMarkdownPreview)}
                      >
                        {showMarkdownPreview ? 'Éditer' : 'Prévisualiser'}
                      </Button>
                    </div>
                    {showMarkdownPreview ? (
                      <div className="p-3 border rounded-md h-[250px] overflow-y-auto prose prose-sm max-w-none">
                        {description || <span className="text-gray-400">Aucune description</span>}
                      </div>
                    ) : (
                      <Textarea
                        id="description"
                        placeholder="Description complète de la Feature (supporte markdown)&#10;&#10;## Vue d'ensemble&#10;Cette feature permet...&#10;&#10;## Cas d'usage principaux&#10;1. Cas 1&#10;2. Cas 2"
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        className="font-mono text-sm h-[250px] resize-none"
                      />
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Fonctionnalités principales</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setMainFeatures([...mainFeatures, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {mainFeatures.map((feature, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Badge variant="outline" className="mt-2">{index + 1}</Badge>
                          <Input
                            placeholder="Ex: Détection automatique de la devise selon la localisation"
                            value={feature}
                            onChange={e => {
                              const newFeatures = [...mainFeatures];
                              newFeatures[index] = e.target.value;
                              setMainFeatures(newFeatures);
                            }}
                            className="text-sm"
                          />
                          {mainFeatures.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newFeatures = mainFeatures.filter((_, i) => i !== index);
                                setMainFeatures(newFeatures.length > 0 ? newFeatures : ['']);
                              }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="nfr">Exigences non-fonctionnelles</Label>
                    <Textarea
                      id="nfr"
                      placeholder="Performance, sécurité, scalabilité...&#10;&#10;Ex:&#10;- Conversion de devise en temps réel (<100ms)&#10;- Support de 50+ devises&#10;- Conformité PCI-DSS pour les transactions"
                      value={nonFunctionalReqs}
                      onChange={e => setNonFunctionalReqs(e.target.value)}
                      className="text-sm h-20 resize-none"
                    />
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="criteria">
              <AccordionTrigger onClick={() => setSectionCriteria(!sectionCriteria)} open={sectionCriteria}>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Acceptance Criteria
                  <Badge variant="outline" className="ml-2 text-xs">{criteriaCount} définis</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionCriteria}>
                <div className="space-y-3 pl-6">
                  <p className="text-xs text-muted-foreground">
                    Critères au niveau Feature (vue d&apos;ensemble). Les critères détaillés seront dans les User Stories.
                  </p>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Critères d&apos;acceptation</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setAcceptanceCriteria([...acceptanceCriteria, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {acceptanceCriteria.map((criterion, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Textarea
                            placeholder={`Critère ${index + 1}: Ex: Le système doit supporter au minimum EUR, USD, GBP, JPY, CHF`}
                            value={criterion}
                            onChange={e => {
                              const newCriteria = [...acceptanceCriteria];
                              newCriteria[index] = e.target.value;
                              setAcceptanceCriteria(newCriteria);
                            }}
                            className="text-sm h-16 resize-none"
                          />
                          {acceptanceCriteria.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newCriteria = acceptanceCriteria.filter((_, i) => i !== index);
                                setAcceptanceCriteria(newCriteria.length > 0 ? newCriteria : ['']);
                              }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="assets">
              <AccordionTrigger onClick={() => setSectionAssets(!sectionAssets)} open={sectionAssets}>
                <div className="flex items-center gap-2">
                  <Image className="h-4 w-4" />
                  Wireframes & Assets
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionAssets}>
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Liens vers designs / maquettes</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setDesignLinks([...designLinks, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">Figma, Sketch, wireframes, screenshots...</p>
                    <div className="space-y-2">
                      {designLinks.map((link, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Input
                            placeholder="https://figma.com/file/..."
                            value={link}
                            onChange={e => {
                              const newLinks = [...designLinks];
                              newLinks[index] = e.target.value;
                              setDesignLinks(newLinks);
                            }}
                            className="text-sm"
                          />
                          {designLinks.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newLinks = designLinks.filter((_, i) => i !== index);
                                setDesignLinks(newLinks.length > 0 ? newLinks : ['']);
                              }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="planning">
              <AccordionTrigger onClick={() => setSectionPlanning(!sectionPlanning)} open={sectionPlanning}>
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4" />
                  Planification
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionPlanning}>
                <div className="space-y-4 pl-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="priority">Priorité (MoSCoW)</Label>
                      <Select value={priority} onValueChange={(v: 'Must' | 'Should' | 'Could' | 'Won\'t') => setPriority(v)}>
                        <SelectTrigger id="priority">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Must">
                            <span className="flex items-center gap-2">
                              <Badge variant="destructive" className="w-2 h-2 p-0 rounded-full" />
                              Must Have
                            </span>
                          </SelectItem>
                          <SelectItem value="Should">
                            <span className="flex items-center gap-2">
                              <Badge className="w-2 h-2 p-0 rounded-full bg-orange-500" />
                              Should Have
                            </span>
                          </SelectItem>
                          <SelectItem value="Could">
                            <span className="flex items-center gap-2">
                              <Badge className="w-2 h-2 p-0 rounded-full bg-yellow-500" />
                              Could Have
                            </span>
                          </SelectItem>
                          <SelectItem value="Won't">
                            <span className="flex items-center gap-2">
                              <Badge className="w-2 h-2 p-0 rounded-full bg-gray-400" />
                              Won&apos;t Have
                            </span>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="businessValue">Valeur métier (1-10)</Label>
                      <div className="flex items-center gap-3">
                        <Input
                          id="businessValue"
                          type="range"
                          min="1"
                          max="10"
                          value={businessValue}
                          onChange={e => setBusinessValue(Number(e.target.value))}
                          className="flex-1"
                        />
                        <Badge variant="outline" className="w-8 text-center">
                          {businessValue}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="effort">Effort estimé (T-shirt sizing)</Label>
                      <Select value={effortEstimate} onValueChange={(v: 'XS' | 'S' | 'M' | 'L' | 'XL') => setEffortEstimate(v)}>
                        <SelectTrigger id="effort">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="XS">XS (1-2 jours)</SelectItem>
                          <SelectItem value="S">S (3-5 jours)</SelectItem>
                          <SelectItem value="M">M (1-2 semaines)</SelectItem>
                          <SelectItem value="L">L (2-4 semaines)</SelectItem>
                          <SelectItem value="XL">XL (&gt;1 mois)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="status">Statut</Label>
                      <Select value={status} onValueChange={(v: 'Backlog' | 'Analysis' | 'Ready' | 'In Progress' | 'Done') => setStatus(v)}>
                        <SelectTrigger id="status">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Backlog">Backlog</SelectItem>
                          <SelectItem value="Analysis">Analysis</SelectItem>
                          <SelectItem value="Ready">Ready</SelectItem>
                          <SelectItem value="In Progress">In Progress</SelectItem>
                          <SelectItem value="Done">Done</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="release">Release target</Label>
                      <Input
                        id="release"
                        placeholder="Ex: v2.1, Q3 2024, Sprint 15"
                        value={releaseTarget}
                        onChange={e => setReleaseTarget(e.target.value)}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="iteration">Itération planifiée</Label>
                      <Input
                        id="iteration"
                        placeholder="Ex: PI 2024.2, Sprint 12"
                        value={iteration}
                        onChange={e => setIteration(e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          </div>
        </div>

        <DialogFooter className="px-6 py-4 border-t flex-shrink-0">
          {item && (
            <Button variant="destructive" onClick={() => setShowDeleteConfirm(true)}>
              Supprimer
            </Button>
          )}
          {requiresValidation && (
            <Button
              variant="secondary"
              disabled={validating}
              onClick={handleValidate}
            >
              {validating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Validation…
                </>
              ) : (
                'Valider'
              )}
            </Button>
          )}
          <Button onClick={handleSubmit}>Enregistrer</Button>
        </DialogFooter>
      </DialogContent>

      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmation de suppression</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p>Voulez-vous vraiment supprimer cette Feature ?</p>
            <p className="text-sm text-muted-foreground mt-2">
              Cette action supprimera également toutes les User Stories associées.
            </p>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowDeleteConfirm(false)}>Annuler</Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (item) {
                  await deleteItem(item.id);
                  setShowDeleteConfirm(false);
                  onClose();
                }
              }}
            >
              Supprimer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Dialog>
  );
}
