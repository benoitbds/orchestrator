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
import { useBacklog } from '@/context/BacklogContext';
import { validateItem } from '@/lib/api';
import { TemplateSelector } from '@/components/TemplateSelector';
import { epicTemplates, getEpicTemplate } from '@/lib/templates';
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
const Lightbulb = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Lightbulb })),
  { ssr: false }
);
const FileText = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.FileText })),
  { ssr: false }
);
const BarChart3 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.BarChart3 })),
  { ssr: false }
);
const TrendingUp = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.TrendingUp })),
  { ssr: false }
);

interface EpicDialogProps {
  isOpen: boolean;
  onClose: () => void;
  item?: BacklogItem;
  projectId: number;
  onSave: (item: Partial<BacklogItem>) => Promise<void>;
}

export function EpicDialog({ isOpen, onClose, item, projectId, onSave }: EpicDialogProps) {
  const { deleteItem, refreshItems } = useBacklog();
  
  const [title, setTitle] = useState('');
  const [portfolio, setPortfolio] = useState('');
  const [vision, setVision] = useState('');
  const [objectives, setObjectives] = useState<string[]>(['']);
  const [valueHypothesis, setValueHypothesis] = useState('');
  const [description, setDescription] = useState('');
  const [inScope, setInScope] = useState<string[]>(['']);
  const [outOfScope, setOutOfScope] = useState<string[]>(['']);
  const [leadingIndicators, setLeadingIndicators] = useState<string[]>(['']);
  const [laggingIndicators, setLaggingIndicators] = useState<string[]>(['']);
  const [successDefinition, setSuccessDefinition] = useState('');
  const [priority, setPriority] = useState<'Critical' | 'High' | 'Medium' | 'Low'>('Medium');
  const [businessValue, setBusinessValue] = useState<number>(5);
  const [estimatedBudget, setEstimatedBudget] = useState('');
  const [estimatedDuration, setEstimatedDuration] = useState('');
  const [status, setStatus] = useState<'Backlog' | 'En cours' | 'Livré' | 'Abandonné'>('Backlog');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  const [showMarkdownPreview, setShowMarkdownPreview] = useState(false);
  const [sectionVision, setSectionVision] = useState(true);
  const [sectionScope, setSectionScope] = useState(true);
  const [sectionMetrics, setSectionMetrics] = useState(false);
  const [sectionPlanning, setSectionPlanning] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [validating, setValidating] = useState(false);

  const handleTemplateSelect = (templateKey: string) => {
    const template = getEpicTemplate(templateKey);
    if (!template) return;

    setVision(template.vision);
    setObjectives(template.objectives);
    setValueHypothesis(template.valueHypothesis);
    setDescription(template.descriptionTemplate);
    setInScope(template.inScope);
    setOutOfScope(template.outOfScope);
    setLeadingIndicators(template.leadingIndicators);
    setLaggingIndicators(template.laggingIndicators);
    setSuccessDefinition(template.successDefinition);

    toast.success(`Template "${template.name}" appliqué. Personnalisez les placeholders.`);
  };

  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setPortfolio('');
      setVision(item.description || '');
      setValueHypothesis(item.benefit_hypothesis || '');
      setDescription(item.description || '');
      setSuccessDefinition(item.mvp_definition || '');
      setPriority('Medium');
      setBusinessValue(5);
      setStatus('Backlog');
      
      const leadingStr = item.leading_indicators || '';
      setLeadingIndicators(leadingStr ? leadingStr.split('\n').filter(s => s.trim()) : ['']);
      
      setObjectives(['']);
      setInScope(['']);
      setOutOfScope(['']);
      setLaggingIndicators(['']);
    } else {
      setTitle('');
      setPortfolio('');
      setVision('');
      setObjectives(['']);
      setValueHypothesis('');
      setDescription('');
      setInScope(['']);
      setOutOfScope(['']);
      setLeadingIndicators(['']);
      setLaggingIndicators(['']);
      setSuccessDefinition('');
      setPriority('Medium');
      setBusinessValue(5);
      setEstimatedBudget('');
      setEstimatedDuration('');
      setStatus('Backlog');
      setStartDate('');
      setEndDate('');
    }
  }, [item, isOpen]);

  const handleSubmit = async () => {
    const epicData = {
      id: item?.id,
      title,
      type: 'Epic' as const,
      description: vision,
      project_id: projectId,
      state: status,
      benefit_hypothesis: valueHypothesis || undefined,
      leading_indicators: leadingIndicators.filter(i => i.trim()).join('\n') || undefined,
      mvp_definition: successDefinition || undefined,
    };

    await onSave(epicData);
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
      toast.success('Epic validé');
      onClose();
    } catch {
      toast.error('Impossible de valider cet Epic');
    } finally {
      setValidating(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[700px] max-h-[90vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b flex-shrink-0">
          <DialogTitle>{item ? 'Modifier' : 'Créer'} Epic</DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="space-y-6">
            {!item && (
              <TemplateSelector
                templates={epicTemplates}
                onSelectTemplate={handleTemplateSelect}
                type="Epic"
              />
            )}
            
            <div className="space-y-4">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Info className="h-4 w-4" />
                Identification
              </h3>
              <div className="space-y-3 pl-6">
                <div className="space-y-2">
                  <Label htmlFor="title">Titre de l&apos;Epic <span className="text-red-500">*</span></Label>
                  <Input
                    id="title"
                    placeholder="Ex: Nouveau système de paiement en ligne"
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
                    value="Epic"
                    disabled
                    className="bg-gray-100 dark:bg-gray-800 cursor-not-allowed"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="portfolio">Portfolio/Programme</Label>
                  <Input
                    id="portfolio"
                    placeholder="Ex: Digital Transformation, Customer Experience"
                    value={portfolio}
                    onChange={e => setPortfolio(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">Optionnel - Pour regrouper les Epics par initiative stratégique</p>
                </div>
              </div>
            </div>

            <AccordionItem value="vision">
              <AccordionTrigger onClick={() => setSectionVision(!sectionVision)} open={sectionVision}>
                <div className="flex items-center gap-2">
                  <Lightbulb className="h-4 w-4" />
                  Vision & Objectifs
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionVision}>
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <Label htmlFor="vision">Vision de l&apos;Epic <span className="text-red-500">*</span></Label>
                    <Textarea
                      id="vision"
                      placeholder="Quelle est la vision stratégique de cet Epic ?&#10;&#10;Ex: Permettre aux clients de payer en ligne de manière sécurisée et rapide, en supportant plusieurs modes de paiement (CB, PayPal, Apple Pay) pour augmenter le taux de conversion de 25%."
                      value={vision}
                      onChange={e => setVision(e.target.value)}
                      className="text-sm h-24 resize-none"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Objectifs métier</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setObjectives([...objectives, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {objectives.map((objective, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Badge variant="outline" className="mt-2">{index + 1}</Badge>
                          <Input
                            placeholder={`Objectif ${index + 1}: Ex: Réduire le taux d'abandon de panier de 40% à 25%`}
                            value={objective}
                            onChange={e => {
                              const newObjectives = [...objectives];
                              newObjectives[index] = e.target.value;
                              setObjectives(newObjectives);
                            }}
                            className="text-sm"
                          />
                          {objectives.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newObjectives = objectives.filter((_, i) => i !== index);
                                setObjectives(newObjectives.length > 0 ? newObjectives : ['']);
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
                    <Label htmlFor="valueHypothesis">Hypothèse de valeur</Label>
                    <Textarea
                      id="valueHypothesis"
                      placeholder="Quelle valeur métier cet Epic apporte-t-il ?&#10;&#10;Ex: En simplifiant le processus de paiement, nous pensons augmenter le taux de conversion de 15% et générer 500k€ de revenus supplémentaires par trimestre."
                      value={valueHypothesis}
                      onChange={e => setValueHypothesis(e.target.value)}
                      className="text-sm h-20 resize-none"
                    />
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="scope">
              <AccordionTrigger onClick={() => setSectionScope(!sectionScope)} open={sectionScope}>
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Périmètre
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionScope}>
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
                      <div className="p-3 border rounded-md h-[300px] overflow-y-auto prose prose-sm max-w-none">
                        {description || <span className="text-gray-400">Aucune description</span>}
                      </div>
                    ) : (
                      <Textarea
                        id="description"
                        placeholder="Description complète de l'Epic (supporte markdown)&#10;&#10;## Contexte&#10;- Point clé 1&#10;- Point clé 2&#10;&#10;## Architecture envisagée&#10;..."
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        className="font-mono text-sm h-[300px] resize-none"
                      />
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Dans le scope</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setInScope([...inScope, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {inScope.map((item, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <span className="text-green-600 mt-2">✓</span>
                          <Input
                            placeholder="Ex: Support des cartes de crédit Visa/Mastercard"
                            value={item}
                            onChange={e => {
                              const newInScope = [...inScope];
                              newInScope[index] = e.target.value;
                              setInScope(newInScope);
                            }}
                            className="text-sm"
                          />
                          {inScope.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newInScope = inScope.filter((_, i) => i !== index);
                                setInScope(newInScope.length > 0 ? newInScope : ['']);
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
                    <div className="flex items-center justify-between">
                      <Label>Hors scope / Exclusions</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setOutOfScope([...outOfScope, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {outOfScope.map((item, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <span className="text-red-600 mt-2">✗</span>
                          <Input
                            placeholder="Ex: Paiement en cryptomonnaie (prévu pour v2)"
                            value={item}
                            onChange={e => {
                              const newOutOfScope = [...outOfScope];
                              newOutOfScope[index] = e.target.value;
                              setOutOfScope(newOutOfScope);
                            }}
                            className="text-sm"
                          />
                          {outOfScope.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newOutOfScope = outOfScope.filter((_, i) => i !== index);
                                setOutOfScope(newOutOfScope.length > 0 ? newOutOfScope : ['']);
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

            <AccordionItem value="metrics">
              <AccordionTrigger onClick={() => setSectionMetrics(!sectionMetrics)} open={sectionMetrics}>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Success Metrics
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionMetrics}>
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Leading Indicators (métriques prédictives)</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setLeadingIndicators([...leadingIndicators, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">Métriques mesurables pendant le développement</p>
                    <div className="space-y-2">
                      {leadingIndicators.map((indicator, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Input
                            placeholder="Ex: Nombre de tests utilisateurs réalisés (target: 50)"
                            value={indicator}
                            onChange={e => {
                              const newIndicators = [...leadingIndicators];
                              newIndicators[index] = e.target.value;
                              setLeadingIndicators(newIndicators);
                            }}
                            className="text-sm"
                          />
                          {leadingIndicators.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newIndicators = leadingIndicators.filter((_, i) => i !== index);
                                setLeadingIndicators(newIndicators.length > 0 ? newIndicators : ['']);
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
                    <div className="flex items-center justify-between">
                      <Label>Lagging Indicators (métriques de résultat)</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setLaggingIndicators([...laggingIndicators, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">Métriques mesurables après la livraison</p>
                    <div className="space-y-2">
                      {laggingIndicators.map((indicator, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Input
                            placeholder="Ex: Taux de conversion panier (baseline: 15%, target: 25%)"
                            value={indicator}
                            onChange={e => {
                              const newIndicators = [...laggingIndicators];
                              newIndicators[index] = e.target.value;
                              setLaggingIndicators(newIndicators);
                            }}
                            className="text-sm"
                          />
                          {laggingIndicators.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newIndicators = laggingIndicators.filter((_, i) => i !== index);
                                setLaggingIndicators(newIndicators.length > 0 ? newIndicators : ['']);
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
                    <Label htmlFor="successDefinition">Définition du succès</Label>
                    <Textarea
                      id="successDefinition"
                      placeholder="Quand considère-t-on cet Epic comme un succès ?&#10;&#10;Ex: L'Epic sera considéré comme un succès si:&#10;- Le taux de conversion augmente de 10 points&#10;- 80% des paiements sont traités en moins de 3 secondes&#10;- Le Net Promoter Score dépasse 8/10"
                      value={successDefinition}
                      onChange={e => setSuccessDefinition(e.target.value)}
                      className="text-sm h-24 resize-none"
                    />
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
                      <Label htmlFor="priority">Priorité stratégique <span className="text-red-500">*</span></Label>
                      <Select value={priority} onValueChange={(v: 'Critical' | 'High' | 'Medium' | 'Low') => setPriority(v)}>
                        <SelectTrigger id="priority">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Critical">
                            <span className="flex items-center gap-2">
                              <Badge variant="destructive" className="w-2 h-2 p-0 rounded-full" />
                              Critique
                            </span>
                          </SelectItem>
                          <SelectItem value="High">
                            <span className="flex items-center gap-2">
                              <Badge className="w-2 h-2 p-0 rounded-full bg-orange-500" />
                              Haute
                            </span>
                          </SelectItem>
                          <SelectItem value="Medium">
                            <span className="flex items-center gap-2">
                              <Badge className="w-2 h-2 p-0 rounded-full bg-yellow-500" />
                              Moyenne
                            </span>
                          </SelectItem>
                          <SelectItem value="Low">
                            <span className="flex items-center gap-2">
                              <Badge className="w-2 h-2 p-0 rounded-full bg-gray-400" />
                              Basse
                            </span>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="businessValue">Valeur métier (1-10) <span className="text-red-500">*</span></Label>
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
                      <Label htmlFor="budget">Budget estimé</Label>
                      <Input
                        id="budget"
                        type="text"
                        placeholder="Ex: 150 000 € ou 200k"
                        value={estimatedBudget}
                        onChange={e => setEstimatedBudget(e.target.value)}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="duration">Durée estimée</Label>
                      <Input
                        id="duration"
                        type="text"
                        placeholder="Ex: 6 sprints ou 3 mois"
                        value={estimatedDuration}
                        onChange={e => setEstimatedDuration(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="status">Statut</Label>
                    <Select value={status} onValueChange={(v: 'Backlog' | 'En cours' | 'Livré' | 'Abandonné') => setStatus(v)}>
                      <SelectTrigger id="status">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Backlog">Backlog</SelectItem>
                        <SelectItem value="En cours">En cours</SelectItem>
                        <SelectItem value="Livré">Livré</SelectItem>
                        <SelectItem value="Abandonné">Abandonné</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="startDate">Date de début prévue</Label>
                      <Input
                        id="startDate"
                        type="date"
                        value={startDate}
                        onChange={e => setStartDate(e.target.value)}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="endDate">Date de fin prévue</Label>
                      <Input
                        id="endDate"
                        type="date"
                        value={endDate}
                        onChange={e => setEndDate(e.target.value)}
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
            <p>Voulez-vous vraiment supprimer cet Epic ?</p>
            <p className="text-sm text-muted-foreground mt-2">
              Cette action supprimera également toutes les Features et User Stories associées.
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
