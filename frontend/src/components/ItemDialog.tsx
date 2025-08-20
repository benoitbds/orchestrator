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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BacklogItem } from '@/models/backlogItem';
import { useItems } from '@/lib/hooks';
import { useBacklog } from '@/context/BacklogContext';
import { mutate } from 'swr';
import { http } from '@/lib/api';
import dynamic from 'next/dynamic';
const Loader2 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Loader2 })),
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
  const { deleteItem } = useBacklog();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<'Epic' | 'Capability' | 'Feature' | 'US' | 'UC'>('US');
  const [parentId, setParentId] = useState<number | null>(null);
  const [state, setState] = useState('Funnel');
  const [benefitHypothesis, setBenefitHypothesis] = useState('');
  const [leadingIndicators, setLeadingIndicators] = useState('');
  const [mvpDefinition, setMvpDefinition] = useState('');
  const [wsjf, setWsjf] = useState<number | null>(null);
  const [acceptanceCriteria, setAcceptanceCriteria] = useState('');
  const [storyPoints, setStoryPoints] = useState<number | null>(null);
  const [programIncrement, setProgramIncrement] = useState('');
  const [iteration, setIteration] = useState('');
  const [owner, setOwner] = useState('');
  const [investCompliant, setInvestCompliant] = useState(false);
  const { data: items } = useItems(projectId);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const saveLabel = item?.generated_by_ai ? 'Valider' : 'Enregistrer';
  const [isGeneratingFeatures, setIsGeneratingFeatures] = useState(false);

  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setDescription(item.description || '');
      setType(item.type);
      setParentId(item.parent_id);
      setState(item.state || '');
      setBenefitHypothesis(item.benefit_hypothesis || '');
      setLeadingIndicators(item.leading_indicators || '');
      setMvpDefinition(item.mvp_definition || '');
      setWsjf(item.wsjf);
      setAcceptanceCriteria(item.acceptance_criteria || '');
      setStoryPoints(item.story_points);
      setProgramIncrement(item.program_increment || '');
      setIteration(item.iteration || '');
      setOwner(item.owner || '');
      setInvestCompliant(item.invest_compliant || false);
    } else {
      setTitle('');
      setDescription('');
      setType('US');
      setParentId(null);
      setState('Todo'); // Default pour US/UC
      setBenefitHypothesis('');
      setLeadingIndicators('');
      setMvpDefinition('');
      setWsjf(null);
      setAcceptanceCriteria('');
      setStoryPoints(null);
      setProgramIncrement('');
      setIteration('');
      setOwner('');
      setInvestCompliant(false);
    }
  }, [item, isOpen]);

  const handleSubmit = async () => {
    // Préparer les données selon le type
    const baseData = {
      id: item?.id,
      title,
      description,
      type,
      parent_id: parentId,
      project_id: projectId,
    };

    // Ajouter les champs spécifiques selon le type
    let extraData: any = {};
    
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
        acceptance_criteria: acceptanceCriteria || undefined,
        wsjf: wsjf || undefined,
        program_increment: programIncrement || undefined,
        owner: owner || undefined,
      };
    } else if (type === 'US' || type === 'UC') {
      extraData = {
        story_points: storyPoints || undefined,
        acceptance_criteria: acceptanceCriteria || undefined,
        invest_compliant: investCompliant,
        iteration: iteration || undefined,
        status: state || 'Todo',
      };
    }

    // Si c'était généré par l'IA, on marque validé
    if (item?.generated_by_ai) {
      extraData.generated_by_ai = false;
    }

    await onSave({ ...baseData, ...extraData });
    onClose();
  };

  // Logique de filtrage des parents selon le type sélectionné
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
        return []; // Les Epics n'ont pas de parent
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

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{item ? 'Modifier' : 'Nouvel'} item</DialogTitle>
        </DialogHeader>
        <Tabs defaultValue="base" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="base">Base</TabsTrigger>
            <TabsTrigger value="safe">Détails SAFe</TabsTrigger>
          </TabsList>
          
          <TabsContent value="base" className="space-y-4 mt-4">
            <Input
              placeholder="Titre"
              value={title}
              onChange={e => setTitle(e.target.value)}
            />
            <Input
              placeholder="Description"
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
            <Select value={type} onValueChange={(v: any) => {
              setType(v);
              // Ajuster l'état selon le type
              if (v === 'Epic' || v === 'Capability') {
                setState('Funnel');
              } else if (v === 'US' || v === 'UC') {
                setState('Todo');
              } else {
                setState(''); // Feature n'a pas de state
              }
            }}>
              <SelectTrigger>
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Epic">Epic</SelectItem>
                <SelectItem value="Capability">Capability</SelectItem>
                <SelectItem value="Feature">Feature</SelectItem>
                <SelectItem value="US">US</SelectItem>
                <SelectItem value="UC">UC</SelectItem>
              </SelectContent>
            </Select>
            <Select value={parentId?.toString() || "null"} onValueChange={(v: any) => setParentId(v === "null" ? null : Number(v))}>
              <SelectTrigger>
                <SelectValue placeholder="Parent" />
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
          </TabsContent>
          
          <TabsContent value="safe" className="space-y-4 mt-4 max-h-80 overflow-y-auto">
            {/* Champs spécifiques selon le type */}
            {(type === 'Epic' || type === 'Capability') && (
              <>
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
                
                <Input
                  placeholder="Hypothèse de bénéfice *"
                  value={benefitHypothesis}
                  onChange={e => setBenefitHypothesis(e.target.value)}
                  required
                />
                
                <Input
                  placeholder="Indicateurs avancés"
                  value={leadingIndicators}
                  onChange={e => setLeadingIndicators(e.target.value)}
                />
                
                <Input
                  placeholder="Définition MVP"
                  value={mvpDefinition}
                  onChange={e => setMvpDefinition(e.target.value)}
                />
                
                <Input
                  type="number"
                  step="0.1"
                  placeholder="WSJF"
                  value={wsjf?.toString() || ''}
                  onChange={e => setWsjf(e.target.value ? Number(e.target.value) : null)}
                />
              </>
            )}

            {type === 'Feature' && (
              <>
                <Input
                  placeholder="Hypothèse de bénéfice *"
                  value={benefitHypothesis}
                  onChange={e => setBenefitHypothesis(e.target.value)}
                  required
                />
                
                <Input
                  placeholder="Critères d'acceptation *"
                  value={acceptanceCriteria}
                  onChange={e => setAcceptanceCriteria(e.target.value)}
                  required
                />
                
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    step="0.1"
                    placeholder="WSJF"
                    value={wsjf?.toString() || ''}
                    onChange={e => setWsjf(e.target.value ? Number(e.target.value) : null)}
                  />
                  <Input
                    placeholder="Program Increment"
                    value={programIncrement}
                    onChange={e => setProgramIncrement(e.target.value)}
                  />
                </div>
                
                <Input
                  placeholder="Propriétaire"
                  value={owner}
                  onChange={e => setOwner(e.target.value)}
                />
              </>
            )}

            {(type === 'US' || type === 'UC') && (
              <>
                <Input
                  type="number"
                  placeholder="Story Points *"
                  value={storyPoints?.toString() || ''}
                  onChange={e => setStoryPoints(e.target.value ? Number(e.target.value) : null)}
                  required
                />
                
                <Input
                  placeholder="Critères d'acceptation *"
                  value={acceptanceCriteria}
                  onChange={e => setAcceptanceCriteria(e.target.value)}
                  required
                />
                
                <div className="grid grid-cols-2 gap-2">
                  <Select value={state} onValueChange={setState}>
                    <SelectTrigger>
                      <SelectValue placeholder="Statut" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Todo">Todo</SelectItem>
                      <SelectItem value="Doing">Doing</SelectItem>
                      <SelectItem value="Done">Done</SelectItem>
                    </SelectContent>
                  </Select>
                  
                  <Input
                    placeholder="Itération"
                    value={iteration}
                    onChange={e => setIteration(e.target.value)}
                  />
                </div>
                
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={investCompliant}
                    onChange={e => setInvestCompliant(e.target.checked)}
                  />
                  <span>Conforme INVEST</span>
                </label>
              </>
            )}
            
            {!['Epic', 'Capability', 'Feature', 'US', 'UC'].includes(type) && (
              <p className="text-muted-foreground text-center py-8">
                Sélectionnez un type dans l'onglet Base pour voir les détails SAFe
              </p>
            )}
          </TabsContent>
        </Tabs>
        <DialogFooter>
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
                const resp = await http('/feature_proposals', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    project_id: projectId,
                    parent_id: item.id,
                    parent_title: title,
                  }),
                });
                if (resp.ok) {
                  await mutate(`/items?project_id=${projectId}`);
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
          <Button onClick={handleSubmit}>{saveLabel}</Button>
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
                <p>L'item suivant et ses sous-items seront supprimés :</p>
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
                  // rafraîchir la liste des items
                  mutate(`/items?project_id=${projectId}`);
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
''
