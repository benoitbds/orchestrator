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
import { BacklogItem, isEpic, isCapability, isFeature, isUS, isUC } from '@/models/backlogItem';
import { useItems } from '@/lib/hooks';
import { useBacklog } from '@/context/BacklogContext';
import { apiFetch, validateItem } from '@/lib/api';
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
const CheckCircle2 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.CheckCircle2 })),
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
const Target = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Target })),
  { ssr: false }
);
const Edit3 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Edit3 })),
  { ssr: false }
);

interface ItemDialogProps {
  isOpen: boolean;
  onClose: () => void;
  item?: BacklogItem;
  projectId: number;
  onSave: (item: Partial<BacklogItem>) => Promise<void>;
}

export function ItemDialog({ isOpen, onClose, item, projectId, onSave }: ItemDialogProps) {
  const { deleteItem, refreshItems } = useBacklog();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<'Epic' | 'Capability' | 'Feature' | 'US' | 'UC'>('US');
  const [parentId, setParentId] = useState<number | null>(null);
  const [state, setState] = useState('Funnel');
  const [benefitHypothesis, setBenefitHypothesis] = useState('');
  const [leadingIndicators, setLeadingIndicators] = useState('');
  const [mvpDefinition, setMvpDefinition] = useState('');
  const [wsjf, setWsjf] = useState<number | null>(null);
  const [acceptanceCriteria, setAcceptanceCriteria] = useState<string[]>(['']);
  const [storyPoints, setStoryPoints] = useState<number | null>(null);
  const [programIncrement, setProgramIncrement] = useState('');
  const [iteration, setIteration] = useState('');
  const [owner, setOwner] = useState('');
  const [investCompliant, setInvestCompliant] = useState(false);
  
  const [userRole, setUserRole] = useState('');
  const [userAction, setUserAction] = useState('');
  const [userBenefit, setUserBenefit] = useState('');
  const [priority, setPriority] = useState<'Critical' | 'High' | 'Medium' | 'Low'>('Medium');
  const [businessValue, setBusinessValue] = useState<number>(5);
  const [showMarkdownPreview, setShowMarkdownPreview] = useState(false);
  
  const [sectionUserStory, setSectionUserStory] = useState(true);
  const [sectionDescription, setSectionDescription] = useState(true);
  const [sectionPlanning, setSectionPlanning] = useState(false);
  const [sectionQuality, setSectionQuality] = useState(false);
  
  const { data: items } = useItems(projectId);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isGeneratingFeatures, setIsGeneratingFeatures] = useState(false);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setDescription(item.description || '');
      setType(item.type);
      setParentId(item.parent_id);
      setState((isEpic(item) || isCapability(item)) ? (item.state || '') : '');
      setBenefitHypothesis((isEpic(item) || isCapability(item) || isFeature(item)) ? (item.benefit_hypothesis || '') : '');
      setLeadingIndicators((isEpic(item) || isCapability(item)) ? (item.leading_indicators || '') : '');
      setMvpDefinition((isEpic(item) || isCapability(item)) ? (item.mvp_definition || '') : '');
      setWsjf((isEpic(item) || isCapability(item) || isFeature(item)) ? (item.wsjf ?? null) : null);
      const criteria = (isFeature(item) || isUS(item) || isUC(item)) ? (item.acceptance_criteria || '') : '';
      setAcceptanceCriteria(criteria ? criteria.split('\n').filter(c => c.trim()) : ['']);
      
      if ((isUS(item) || isUC(item)) && item.description) {
        const match = item.description.match(/En tant que (.+), je veux (.+) afin de (.+)/);
        if (match) {
          setUserRole(match[1]);
          setUserAction(match[2]);
          setUserBenefit(match[3]);
        }
      }
      setStoryPoints((isUS(item) || isUC(item)) ? item.story_points : 0);
      setProgramIncrement(isFeature(item) ? (item.program_increment || '') : '');
      setIteration((isUS(item) || isUC(item)) ? (item.iteration || '') : '');
      setOwner(isFeature(item) ? (item.owner || '') : '');
      setInvestCompliant((isUS(item) || isUC(item)) ? (item.invest_compliant || false) : false);
    } else {
      setTitle('');
      setDescription('');
      setType('US');
      setParentId(null);
      setState('Todo');
      setBenefitHypothesis('');
      setLeadingIndicators('');
      setMvpDefinition('');
      setWsjf(null);
      setAcceptanceCriteria(['']);
      setUserRole('');
      setUserAction('');
      setUserBenefit('');
      setPriority('Medium');
      setBusinessValue(5);
      setStoryPoints(null);
      setProgramIncrement('');
      setIteration('');
      setOwner('');
      setInvestCompliant(false);
    }
  }, [item, isOpen]);

  const handleSubmit = async () => {
    const baseData = {
      id: item?.id,
      title,
      description,
      type,
      parent_id: parentId,
      project_id: projectId,
    };

    let finalDescription = description;
    if ((type === 'US' || type === 'UC') && userRole && userAction && userBenefit) {
      finalDescription = `En tant que ${userRole}, je veux ${userAction} afin de ${userBenefit}\n\n${description}`;
    }
    
    let extraData: Record<string, unknown> = {};
    
    if (type === 'Epic' || type === 'Capability') {
      extraData = {
        state: state || 'Funnel',
        benefit_hypothesis: benefitHypothesis || undefined,
        leading_indicators: leadingIndicators || undefined,
        mvp_definition: mvpDefinition || undefined,
        wsjf: wsjf || undefined,
      };
    } else if (type === 'Feature') {
      extraData = {
        benefit_hypothesis: benefitHypothesis || undefined,
        acceptance_criteria: acceptanceCriteria.filter(c => c.trim()).join('\n') || undefined,
        wsjf: wsjf || undefined,
        program_increment: programIncrement || undefined,
        owner: owner || undefined,
      };
    } else if (type === 'US' || type === 'UC') {
      extraData = {
        story_points: storyPoints || undefined,
        acceptance_criteria: acceptanceCriteria.filter(c => c.trim()).join('\n') || undefined,
        invest_compliant: investCompliant,
        iteration: iteration || undefined,
        status: state || 'Todo',
      };
    }
    
    baseData.description = finalDescription;

    await onSave({ ...baseData, ...extraData });
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
      toast.success('Item validé');
      onClose();
    } catch {
      toast.error('Impossible de valider cet item');
    } finally {
      setValidating(false);
    }
  };

  const getPossibleParents = () => {
    if (!items) return [];
    
    switch (type) {
      case 'Capability':
        return items.filter(i => i.type === 'Epic');
      case 'Feature':
        return items.filter(i => i.type === 'Epic' || i.type === 'Capability');
      case 'US':
        return items.filter(i => i.type === 'Feature');
      case 'UC':
        return items.filter(i => i.type === 'US');
      case 'Epic':
      default:
        return [];
    }
  };
  
  const possibleParents = getPossibleParents();

  const getDescendants = (rootId: number): BacklogItem[] => {
    const result: BacklogItem[] = [];
    const traverse = (parentId: number) => {
      items?.forEach(i => {
        if (i.parent_id === parentId) {
          result.push(i);
          traverse(i.id);
        }
      });
    };
    traverse(rootId);
    return result;
  };
  const descendants = item ? getDescendants(item.id) : [];

  const criteriaCount = acceptanceCriteria.filter(c => c.trim()).length;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[650px] max-h-[90vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b flex-shrink-0">
          <DialogTitle>{item ? 'Modifier' : 'Créer'} {type === 'US' ? 'User Story' : type === 'UC' ? 'Use Case' : type === 'Feature' ? 'Feature' : type === 'Epic' ? 'Epic' : 'Capability'}</DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="space-y-6">
            <div className="space-y-4">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Info className="h-4 w-4" />
                Identification
              </h3>
              <div className="space-y-3 pl-6">
                <div className="space-y-2">
                  <Label htmlFor="title">Titre <span className="text-red-500">*</span></Label>
                  <Input
                    id="title"
                    placeholder="Titre court et descriptif"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    required
                    className={!title.trim() ? 'border-red-300' : ''}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="type">Type d&apos;item <span className="text-red-500">*</span></Label>
                  <Select value={type} onValueChange={(v: 'Epic' | 'Capability' | 'Feature' | 'US' | 'UC') => {
                    setType(v);
                    if (v === 'Epic' || v === 'Capability') {
                      setState('Funnel');
                    } else if (v === 'US' || v === 'UC') {
                      setState('Todo');
                    } else {
                      setState('');
                    }
                  }}>
                    <SelectTrigger id="type">
                      <SelectValue placeholder="Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Epic">Epic</SelectItem>
                      <SelectItem value="Capability">Capability</SelectItem>
                      <SelectItem value="Feature">Feature</SelectItem>
                      <SelectItem value="US">User Story (US)</SelectItem>
                      <SelectItem value="UC">Use Case (UC)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="parent">Parent item</Label>
                  <Select value={parentId?.toString() || "null"} onValueChange={(v: string) => setParentId(v === "null" ? null : Number(v))}>
                    <SelectTrigger id="parent">
                      <SelectValue placeholder="Aucun parent" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="null">Aucun</SelectItem>
                      {possibleParents.map(p => (
                        <SelectItem key={p.id} value={p.id.toString()}>
                          {p.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {(type === 'US' || type === 'UC') && (
              <AccordionItem value="user-story">
                <AccordionTrigger onClick={() => setSectionUserStory(!sectionUserStory)} open={sectionUserStory}>
                  <div className="flex items-center gap-2">
                    <Edit3 className="h-4 w-4" />
                    Format User Story
                  </div>
                </AccordionTrigger>
                <AccordionContent open={sectionUserStory}>
                  <div className="space-y-3 pl-6">
                    <p className="text-xs text-muted-foreground">Format recommandé pour clarifier le besoin utilisateur</p>
                    
                    <div className="space-y-2">
                      <Label htmlFor="userRole" className="text-xs">En tant que (rôle)</Label>
                      <Input
                        id="userRole"
                        placeholder="utilisateur, administrateur, client..."
                        value={userRole}
                        onChange={e => setUserRole(e.target.value)}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="userAction" className="text-xs">Je veux (action)</Label>
                      <Input
                        id="userAction"
                        placeholder="importer des fichiers DOCX"
                        value={userAction}
                        onChange={e => setUserAction(e.target.value)}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="userBenefit" className="text-xs">Afin de (bénéfice)</Label>
                      <Input
                        id="userBenefit"
                        placeholder="enrichir ma base documentaire rapidement"
                        value={userBenefit}
                        onChange={e => setUserBenefit(e.target.value)}
                      />
                    </div>
                    
                    {userRole && userAction && userBenefit && (
                      <div className="text-sm p-3 bg-blue-50 dark:bg-blue-950 rounded border border-blue-200 dark:border-blue-800">
                        <p className="font-medium mb-1 text-xs text-gray-500">Prévisualisation:</p>
                        <p className="italic text-blue-900 dark:text-blue-100">
                          En tant que {userRole}, je veux {userAction} afin de {userBenefit}
                        </p>
                      </div>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}

            <AccordionItem value="description">
              <AccordionTrigger onClick={() => setSectionDescription(!sectionDescription)} open={sectionDescription}>
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Description
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionDescription}>
                <div className="space-y-3 pl-6">
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
                      placeholder="Description complète (supporte le markdown: **gras**, *italique*, - listes)&#10;&#10;Contexte:&#10;- Point 1&#10;- Point 2&#10;&#10;Contraintes techniques:&#10;..."
                      value={description}
                      onChange={e => setDescription(e.target.value)}
                      className="font-mono text-sm h-[250px] resize-none"
                    />
                  )}
                </div>
              </AccordionContent>
            </AccordionItem>

            {(type === 'Feature' || type === 'US' || type === 'UC') && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-sm flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4" />
                    Critères d&apos;acceptation
                    <Badge variant="destructive" className="ml-2 text-xs">Obligatoire</Badge>
                  </h3>
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
                <div className="space-y-2 pl-6">
                  {acceptanceCriteria.map((criterion, index) => (
                    <div key={index} className="flex items-start gap-2">
                      <Textarea
                        placeholder={`Critère ${index + 1}: Étant donné [contexte], Quand [action], Alors [résultat]`}
                        value={criterion}
                        onChange={e => {
                          const newCriteria = [...acceptanceCriteria];
                          newCriteria[index] = e.target.value;
                          setAcceptanceCriteria(newCriteria);
                        }}
                        className="text-sm h-20 resize-none"
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
                  <p className="text-xs text-muted-foreground">
                    {criteriaCount < 2 && criteriaCount > 0 && (
                      <span className="text-yellow-600">⚠ Minimum 2 critères recommandés ({criteriaCount}/2)</span>
                    )}
                    {criteriaCount >= 2 && (
                      <span className="text-green-600">✓ {criteriaCount} critères définis</span>
                    )}
                  </p>
                </div>
              </div>
            )}

            {(type === 'US' || type === 'UC') && (
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
                        <Label htmlFor="priority">Priorité <span className="text-red-500">*</span></Label>
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
                        <Label htmlFor="storyPoints">Story Points <span className="text-yellow-600">*</span></Label>
                        <Input
                          id="storyPoints"
                          type="number"
                          placeholder="1, 2, 3, 5, 8, 13..."
                          value={storyPoints?.toString() || ''}
                          onChange={e => setStoryPoints(e.target.value ? Number(e.target.value) : null)}
                          className={!storyPoints ? 'border-yellow-300' : ''}
                        />
                      </div>
                      
                      <div className="space-y-2">
                        <Label htmlFor="status">Statut</Label>
                        <Select value={state} onValueChange={setState}>
                          <SelectTrigger id="status">
                            <SelectValue placeholder="Statut" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Todo">Todo</SelectItem>
                            <SelectItem value="Doing">Doing</SelectItem>
                            <SelectItem value="Done">Done</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="iteration">Itération/Sprint</Label>
                      <Input
                        id="iteration"
                        placeholder="Sprint 1, PI 2024.Q1..."
                        value={iteration}
                        onChange={e => setIteration(e.target.value)}
                      />
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}

            {(type === 'US' || type === 'UC') && (
              <AccordionItem value="quality">
                <AccordionTrigger onClick={() => setSectionQuality(!sectionQuality)} open={sectionQuality}>
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Qualité
                  </div>
                </AccordionTrigger>
                <AccordionContent open={sectionQuality}>
                  <div className="space-y-3 pl-6">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={investCompliant}
                        onChange={e => setInvestCompliant(e.target.checked)}
                        className="rounded"
                      />
                      <span className="text-sm">Conforme INVEST</span>
                      <Badge variant="outline" className="text-xs">Independent, Negotiable, Valuable, Estimable, Small, Testable</Badge>
                    </label>
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}

            {(type === 'Epic' || type === 'Capability') && (
              <div className="space-y-4">
                <h3 className="font-semibold text-sm">Détails SAFe</h3>
                <div className="space-y-3 pl-6">
                  <div className="space-y-2">
                    <Label>État</Label>
                    <Select value={state} onValueChange={setState}>
                      <SelectTrigger>
                        <SelectValue placeholder="État" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Funnel">Funnel</SelectItem>
                        <SelectItem value="Reviewing">Reviewing</SelectItem>
                        <SelectItem value="Analyzing">Analyzing</SelectItem>
                        <SelectItem value="Backlog">Backlog</SelectItem>
                        <SelectItem value="Implementing">Implementing</SelectItem>
                        <SelectItem value="Done">Done</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Hypothèse de bénéfice <span className="text-red-500">*</span></Label>
                    <Input
                      placeholder="Hypothèse de bénéfice"
                      value={benefitHypothesis}
                      onChange={e => setBenefitHypothesis(e.target.value)}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Indicateurs avancés</Label>
                    <Input
                      placeholder="Indicateurs avancés"
                      value={leadingIndicators}
                      onChange={e => setLeadingIndicators(e.target.value)}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Définition MVP</Label>
                    <Input
                      placeholder="Définition MVP"
                      value={mvpDefinition}
                      onChange={e => setMvpDefinition(e.target.value)}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label>WSJF</Label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="WSJF"
                      value={wsjf?.toString() || ''}
                      onChange={e => setWsjf(e.target.value ? Number(e.target.value) : null)}
                    />
                  </div>
                </div>
              </div>
            )}

            {type === 'Feature' && (
              <div className="space-y-4">
                <h3 className="font-semibold text-sm">Détails SAFe</h3>
                <div className="space-y-3 pl-6">
                  <div className="space-y-2">
                    <Label>Hypothèse de bénéfice <span className="text-red-500">*</span></Label>
                    <Input
                      placeholder="Hypothèse de bénéfice"
                      value={benefitHypothesis}
                      onChange={e => setBenefitHypothesis(e.target.value)}
                    />
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>WSJF</Label>
                      <Input
                        type="number"
                        step="0.1"
                        placeholder="WSJF"
                        value={wsjf?.toString() || ''}
                        onChange={e => setWsjf(e.target.value ? Number(e.target.value) : null)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Program Increment</Label>
                      <Input
                        placeholder="PI 2024.1"
                        value={programIncrement}
                        onChange={e => setProgramIncrement(e.target.value)}
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Propriétaire</Label>
                    <Input
                      placeholder="Nom du propriétaire"
                      value={owner}
                      onChange={e => setOwner(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="px-6 py-4 border-t flex-shrink-0">
          {item && (
            <Button variant="destructive" onClick={() => setShowDeleteConfirm(true)}>
              Supprimer
            </Button>
          )}
          {item && type === 'Epic' && (
            <Button
              variant="secondary"
              disabled={isGeneratingFeatures}
              onClick={async () => {
                setIsGeneratingFeatures(true);
                const resp = await apiFetch('/feature_proposals', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    project_id: projectId,
                    parent_id: item.id,
                    parent_title: title,
                  }),
                });
                if (resp.ok) {
                  await refreshItems();
                  onClose();
                }
                setIsGeneratingFeatures(false);
              }}
            >
              {isGeneratingFeatures ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Génération…
                </>
              ) : (
                'Générer features'
              )}
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
            {descendants.length > 0 ? (
              <>
                <p>L&apos;item suivant et ses sous-items seront supprimés :</p>
                <ul className="list-disc ml-6">
                  {descendants.map(d => (
                    <li key={d.id}>{d.title}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p>Voulez-vous supprimer cet item ?</p>
            )}
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
