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
const Users = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Users })),
  { ssr: false }
);
const AlertCircle = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.AlertCircle })),
  { ssr: false }
);
const Play = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Play })),
  { ssr: false }
);
const GitBranch = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.GitBranch })),
  { ssr: false }
);
const XCircle = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.XCircle })),
  { ssr: false }
);
const CheckCircle = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.CheckCircle })),
  { ssr: false }
);

interface Step {
  actor: string;
  action: string;
  system: string;
}

interface AlternativeScenario {
  name: string;
  condition: string;
  steps: string;
}

interface ErrorScenario {
  name: string;
  steps: string;
  recoverable: boolean;
}

interface UseCaseDialogProps {
  isOpen: boolean;
  onClose: () => void;
  item?: BacklogItem;
  projectId: number;
  onSave: (item: Partial<BacklogItem>) => Promise<void>;
}

export function UseCaseDialog({ isOpen, onClose, item, projectId, onSave }: UseCaseDialogProps) {
  const { deleteItem, refreshItems } = useBacklog();
  const { data: items } = useItems(projectId);
  
  const [title, setTitle] = useState('');
  const [ucCode, setUcCode] = useState('');
  const [parentId, setParentId] = useState<number | null>(null);
  const [primaryActor, setPrimaryActor] = useState('');
  const [secondaryActors, setSecondaryActors] = useState<string[]>(['']);
  const [externalSystems, setExternalSystems] = useState<string[]>(['']);
  const [preconditions, setPreconditions] = useState<string[]>(['']);
  const [context, setContext] = useState('');
  const [trigger, setTrigger] = useState<'Manuel' | 'Automatique' | 'Événement'>('Manuel');
  const [nominalSteps, setNominalSteps] = useState<Step[]>([
    { actor: '', action: '', system: '' }
  ]);
  const [alternativeScenarios, setAlternativeScenarios] = useState<AlternativeScenario[]>([]);
  const [errorScenarios, setErrorScenarios] = useState<ErrorScenario[]>([]);
  const [postconditions, setPostconditions] = useState<string[]>(['']);
  const [systemState, setSystemState] = useState('');
  const [dataModified, setDataModified] = useState('');
  
  const [sectionActors, setSectionActors] = useState(true);
  const [sectionPreconditions, setSectionPreconditions] = useState(true);
  const [sectionNominal, setSectionNominal] = useState(true);
  const [sectionAlternative, setSectionAlternative] = useState(true);
  const [sectionError, setSectionError] = useState(true);
  const [sectionPostconditions, setSectionPostconditions] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setUcCode('UC-001');
      setParentId(item.parent_id);
      setPrimaryActor('');
      setContext(item.description || '');
      setTrigger('Manuel');
      
      setSecondaryActors(['']);
      setExternalSystems(['']);
      setPreconditions(['']);
      setNominalSteps([{ actor: '', action: '', system: '' }]);
      setAlternativeScenarios([]);
      setErrorScenarios([]);
      setPostconditions(['']);
      setSystemState('');
      setDataModified('');
    } else {
      setTitle('');
      setUcCode('UC-001');
      setParentId(null);
      setPrimaryActor('');
      setSecondaryActors(['']);
      setExternalSystems(['']);
      setPreconditions(['']);
      setContext('');
      setTrigger('Manuel');
      setNominalSteps([{ actor: '', action: '', system: '' }]);
      setAlternativeScenarios([]);
      setErrorScenarios([]);
      setPostconditions(['']);
      setSystemState('');
      setDataModified('');
    }
  }, [item, isOpen]);

  const handleSubmit = async () => {
    const description = `**Acteur principal**: ${primaryActor}\n\n**Scénario nominal**:\n${nominalSteps.map((s, i) => `${i + 1}. ${s.actor}: ${s.action} → ${s.system}`).join('\n')}`;
    
    const useCaseData = {
      id: item?.id,
      title,
      type: 'UC' as const,
      description,
      project_id: projectId,
      parent_id: parentId,
    };

    await onSave(useCaseData);
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
      toast.success('Use Case validé');
      onClose();
    } catch {
      toast.error('Impossible de valider ce Use Case');
    } finally {
      setValidating(false);
    }
  };

  const userStories = items?.filter(i => i.type === 'US') || [];
  const features = items?.filter(i => i.type === 'Feature') || [];
  const allParents = [...userStories, ...features];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[800px] max-h-[90vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b flex-shrink-0">
          <DialogTitle>{item ? 'Modifier' : 'Créer'} Use Case</DialogTitle>
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
                  <Label htmlFor="title">Titre du Use Case <span className="text-red-500">*</span></Label>
                  <Input
                    id="title"
                    placeholder="Format: Verbe + Complément (ex: Authentifier un utilisateur)"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    required
                    className={!title.trim() ? 'border-red-300' : ''}
                  />
                  <p className="text-xs text-muted-foreground">Utiliser un verbe d&apos;action à l&apos;infinitif</p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="type">Type d&apos;item</Label>
                    <Input
                      id="type"
                      value="Use Case"
                      disabled
                      className="bg-gray-100 dark:bg-gray-800 cursor-not-allowed"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="code">Identifiant</Label>
                    <Input
                      id="code"
                      placeholder="UC-001"
                      value={ucCode}
                      onChange={e => setUcCode(e.target.value)}
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="parent">User Story ou Feature parent</Label>
                  <Select value={parentId?.toString() || "null"} onValueChange={(v: string) => setParentId(v === "null" ? null : Number(v))}>
                    <SelectTrigger id="parent">
                      <SelectValue placeholder="Sélectionner un parent (optionnel)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="null">Aucun</SelectItem>
                      {allParents.map(p => (
                        <SelectItem key={p.id} value={p.id.toString()}>
                          <Badge variant="outline" className="mr-2">{p.type}</Badge>
                          {p.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <AccordionItem value="actors">
              <AccordionTrigger onClick={() => setSectionActors(!sectionActors)} open={sectionActors}>
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Acteurs
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionActors}>
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <Label htmlFor="primaryActor">Acteur principal <span className="text-red-500">*</span></Label>
                    <Input
                      id="primaryActor"
                      placeholder="Ex: Utilisateur final, Administrateur, Client"
                      value={primaryActor}
                      onChange={e => setPrimaryActor(e.target.value)}
                      className={!primaryActor.trim() ? 'border-red-300' : ''}
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Acteurs secondaires</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setSecondaryActors([...secondaryActors, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {secondaryActors.map((actor, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Input
                            placeholder="Ex: Système de notification, Service de paiement"
                            value={actor}
                            onChange={e => {
                              const newActors = [...secondaryActors];
                              newActors[index] = e.target.value;
                              setSecondaryActors(newActors);
                            }}
                            className="text-sm"
                          />
                          {secondaryActors.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newActors = secondaryActors.filter((_, i) => i !== index);
                                setSecondaryActors(newActors.length > 0 ? newActors : ['']);
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
                      <Label>Systèmes externes</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setExternalSystems([...externalSystems, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {externalSystems.map((system, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Input
                            placeholder="Ex: API de géolocalisation, Gateway de paiement Stripe"
                            value={system}
                            onChange={e => {
                              const newSystems = [...externalSystems];
                              newSystems[index] = e.target.value;
                              setExternalSystems(newSystems);
                            }}
                            className="text-sm"
                          />
                          {externalSystems.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newSystems = externalSystems.filter((_, i) => i !== index);
                                setExternalSystems(newSystems.length > 0 ? newSystems : ['']);
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

            <AccordionItem value="preconditions">
              <AccordionTrigger onClick={() => setSectionPreconditions(!sectionPreconditions)} open={sectionPreconditions}>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Préconditions & Contexte
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionPreconditions}>
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Préconditions <span className="text-red-500">*</span></Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setPreconditions([...preconditions, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">Conditions qui doivent être vraies avant l&apos;exécution</p>
                    <div className="space-y-2">
                      {preconditions.map((precondition, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Badge variant="outline" className="mt-2">{index + 1}</Badge>
                          <Input
                            placeholder="Ex: L'utilisateur doit être connecté au système"
                            value={precondition}
                            onChange={e => {
                              const newPreconditions = [...preconditions];
                              newPreconditions[index] = e.target.value;
                              setPreconditions(newPreconditions);
                            }}
                            className="text-sm"
                          />
                          {preconditions.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newPreconditions = preconditions.filter((_, i) => i !== index);
                                setPreconditions(newPreconditions.length > 0 ? newPreconditions : ['']);
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
                    <Label htmlFor="context">Contexte d&apos;utilisation</Label>
                    <Textarea
                      id="context"
                      placeholder="Décrivez le contexte dans lequel ce use case est exécuté...&#10;&#10;Ex: Ce use case est déclenché lorsqu'un utilisateur tente d'accéder à une page protégée sans être authentifié."
                      value={context}
                      onChange={e => setContext(e.target.value)}
                      className="text-sm h-20 resize-none"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="trigger">Déclencheur</Label>
                    <Select value={trigger} onValueChange={(v: 'Manuel' | 'Automatique' | 'Événement') => setTrigger(v)}>
                      <SelectTrigger id="trigger">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Manuel">Manuel (action utilisateur)</SelectItem>
                        <SelectItem value="Automatique">Automatique (tâche planifiée)</SelectItem>
                        <SelectItem value="Événement">Événement (réaction à un événement système)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="nominal">
              <AccordionTrigger onClick={() => setSectionNominal(!sectionNominal)} open={sectionNominal}>
                <div className="flex items-center gap-2">
                  <Play className="h-4 w-4" />
                  Scénario Nominal
                  <Badge variant="outline" className="ml-2 text-xs">{nominalSteps.length} étapes</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionNominal}>
                <div className="space-y-3 pl-6">
                  <p className="text-xs text-muted-foreground">Déroulement normal du cas d&apos;usage sans erreur ni exception</p>
                  
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Étapes du scénario</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setNominalSteps([...nominalSteps, { actor: '', action: '', system: '' }])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter une étape
                      </Button>
                    </div>
                    
                    <div className="space-y-3">
                      {nominalSteps.map((step, index) => (
                        <div key={index} className="border rounded-lg p-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <Badge>{index + 1}</Badge>
                            {nominalSteps.length > 1 && (
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const newSteps = nominalSteps.filter((_, i) => i !== index);
                                  setNominalSteps(newSteps.length > 0 ? newSteps : [{ actor: '', action: '', system: '' }]);
                                }}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                            <div className="space-y-1">
                              <Label className="text-xs">Acteur</Label>
                              <Input
                                placeholder="L'utilisateur"
                                value={step.actor}
                                onChange={e => {
                                  const newSteps = [...nominalSteps];
                                  newSteps[index].actor = e.target.value;
                                  setNominalSteps(newSteps);
                                }}
                                className="text-sm"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs">Action</Label>
                              <Input
                                placeholder="saisit ses identifiants"
                                value={step.action}
                                onChange={e => {
                                  const newSteps = [...nominalSteps];
                                  newSteps[index].action = e.target.value;
                                  setNominalSteps(newSteps);
                                }}
                                className="text-sm"
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs">Système</Label>
                              <Input
                                placeholder="vérifie les identifiants"
                                value={step.system}
                                onChange={e => {
                                  const newSteps = [...nominalSteps];
                                  newSteps[index].system = e.target.value;
                                  setNominalSteps(newSteps);
                                }}
                                className="text-sm"
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="alternative">
              <AccordionTrigger onClick={() => setSectionAlternative(!sectionAlternative)} open={sectionAlternative}>
                <div className="flex items-center gap-2">
                  <GitBranch className="h-4 w-4" />
                  Scénarios Alternatifs
                  <Badge variant="outline" className="ml-2 text-xs">{alternativeScenarios.length}</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionAlternative}>
                <div className="space-y-3 pl-6">
                  <p className="text-xs text-muted-foreground">Variantes et chemins alternatifs du scénario nominal</p>
                  
                  <div className="space-y-3">
                    {alternativeScenarios.map((scenario, index) => (
                      <div key={index} className="border rounded-lg p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <Badge variant="secondary">{index + 1}a</Badge>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setAlternativeScenarios(alternativeScenarios.filter((_, i) => i !== index));
                            }}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                        <div className="space-y-2">
                          <Input
                            placeholder="Nom du scénario (ex: Email invalide)"
                            value={scenario.name}
                            onChange={e => {
                              const newScenarios = [...alternativeScenarios];
                              newScenarios[index].name = e.target.value;
                              setAlternativeScenarios(newScenarios);
                            }}
                            className="text-sm font-medium"
                          />
                          <Input
                            placeholder="Condition: À l'étape X, si..."
                            value={scenario.condition}
                            onChange={e => {
                              const newScenarios = [...alternativeScenarios];
                              newScenarios[index].condition = e.target.value;
                              setAlternativeScenarios(newScenarios);
                            }}
                            className="text-sm"
                          />
                          <Textarea
                            placeholder="Étapes alternatives...&#10;1a. Le système affiche un message d'erreur&#10;2a. L'utilisateur corrige l'email&#10;3a. Retour à l'étape 2"
                            value={scenario.steps}
                            onChange={e => {
                              const newScenarios = [...alternativeScenarios];
                              newScenarios[index].steps = e.target.value;
                              setAlternativeScenarios(newScenarios);
                            }}
                            className="text-sm h-20 resize-none"
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setAlternativeScenarios([...alternativeScenarios, { name: '', condition: '', steps: '' }])}
                    className="w-full"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Ajouter un scénario alternatif
                  </Button>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="error">
              <AccordionTrigger onClick={() => setSectionError(!sectionError)} open={sectionError}>
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4" />
                  Scénarios d&apos;Erreur
                  <Badge variant="destructive" className="ml-2 text-xs">{errorScenarios.length}</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionError}>
                <div className="space-y-3 pl-6">
                  <p className="text-xs text-muted-foreground">Cas d&apos;erreur et exceptions à gérer</p>
                  
                  <div className="space-y-3">
                    {errorScenarios.map((scenario, index) => (
                      <div key={index} className="border border-red-200 dark:border-red-900 rounded-lg p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <Badge variant="destructive">E{index + 1}</Badge>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setErrorScenarios(errorScenarios.filter((_, i) => i !== index));
                            }}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                        <div className="space-y-2">
                          <Input
                            placeholder="Nom de l'erreur (ex: Connexion serveur perdue)"
                            value={scenario.name}
                            onChange={e => {
                              const newScenarios = [...errorScenarios];
                              newScenarios[index].name = e.target.value;
                              setErrorScenarios(newScenarios);
                            }}
                            className="text-sm font-medium"
                          />
                          <Textarea
                            placeholder="Étapes de gestion de l'erreur...&#10;E1. Le système affiche un message d'erreur&#10;E2. Le système propose de réessayer&#10;E3. Fin du use case"
                            value={scenario.steps}
                            onChange={e => {
                              const newScenarios = [...errorScenarios];
                              newScenarios[index].steps = e.target.value;
                              setErrorScenarios(newScenarios);
                            }}
                            className="text-sm h-20 resize-none"
                          />
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={scenario.recoverable}
                              onChange={e => {
                                const newScenarios = [...errorScenarios];
                                newScenarios[index].recoverable = e.target.checked;
                                setErrorScenarios(newScenarios);
                              }}
                              className="rounded"
                            />
                            <span className="text-sm">Récupération possible</span>
                          </label>
                        </div>
                      </div>
                    ))}
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setErrorScenarios([...errorScenarios, { name: '', steps: '', recoverable: false }])}
                    className="w-full"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Ajouter un scénario d&apos;erreur
                  </Button>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="postconditions">
              <AccordionTrigger onClick={() => setSectionPostconditions(!sectionPostconditions)} open={sectionPostconditions}>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  Postconditions
                </div>
              </AccordionTrigger>
              <AccordionContent open={sectionPostconditions}>
                <div className="space-y-4 pl-6">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Postconditions de succès</Label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setPostconditions([...postconditions, ''])}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Ajouter
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">État du système après exécution réussie</p>
                    <div className="space-y-2">
                      {postconditions.map((postcondition, index) => (
                        <div key={index} className="flex items-start gap-2">
                          <Badge variant="outline" className="mt-2">{index + 1}</Badge>
                          <Input
                            placeholder="Ex: L'utilisateur est authentifié et a une session active"
                            value={postcondition}
                            onChange={e => {
                              const newPostconditions = [...postconditions];
                              newPostconditions[index] = e.target.value;
                              setPostconditions(newPostconditions);
                            }}
                            className="text-sm"
                          />
                          {postconditions.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                const newPostconditions = postconditions.filter((_, i) => i !== index);
                                setPostconditions(newPostconditions.length > 0 ? newPostconditions : ['']);
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
                    <Label htmlFor="systemState">État du système</Label>
                    <Textarea
                      id="systemState"
                      placeholder="Décrivez l'état final du système...&#10;&#10;Ex: Une nouvelle session utilisateur est créée en base de données avec un token d'authentification valide pour 24h."
                      value={systemState}
                      onChange={e => setSystemState(e.target.value)}
                      className="text-sm h-16 resize-none"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="dataModified">Données créées/modifiées</Label>
                    <Textarea
                      id="dataModified"
                      placeholder="Quelles données ont été créées ou modifiées ?&#10;&#10;Ex:&#10;- Table 'sessions': nouvelle ligne créée&#10;- Table 'users': champ 'last_login' mis à jour"
                      value={dataModified}
                      onChange={e => setDataModified(e.target.value)}
                      className="text-sm h-16 resize-none"
                    />
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
            <p>Voulez-vous vraiment supprimer ce Use Case ?</p>
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
