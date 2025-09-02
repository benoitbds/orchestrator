export const dictionary = {
  fr: {
    projects: 'Projets',
    documents: 'Documents',
    upload: 'Téléverser',
    chooseFile: 'Choisir un fichier',
    newItem: 'Nouvel item',
    backlog: 'Backlog',
    diagramView: 'Vue Diagramme',
    treeView: 'Vue Arbre',
    tableView: 'Vue Table',
    conversationHistory: 'Historique de conversation',
    askMe: 'Demandez-moi',
    emptyBacklogTitle: 'Votre backlog est vide',
    emptyBacklogSubtitle: 'Ajoutez votre premier item pour commencer',
    createFirstItem: 'Créer mon premier item',
    or: 'ou',
    importDocument: 'Importer un document',
    dropHere: 'Déposez vos fichiers ici',
    dragDropHint: 'Glissez-déposez ou cliquez pour sélectionner des fichiers',
  },
  en: {
    projects: 'Projects',
    documents: 'Documents',
    upload: 'Upload',
    chooseFile: 'Choose a file',
    newItem: 'New item',
    backlog: 'Backlog',
    diagramView: 'Diagram view',
    treeView: 'Tree view',
    tableView: 'Table view',
    conversationHistory: 'Conversation history',
    askMe: 'Ask me',
    emptyBacklogTitle: 'Your backlog is empty',
    emptyBacklogSubtitle: 'Add your first item to get started',
    createFirstItem: 'Create my first item',
    or: 'or',
    importDocument: 'Import a document',
    dropHere: 'Drop files here',
    dragDropHint: 'Drag and drop or click to select files',
  },
} as const;

export type Lang = keyof typeof dictionary;

export function getDict(lang: Lang) {
  return dictionary[lang];
}
