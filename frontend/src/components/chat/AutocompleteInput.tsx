"use client";

import { useState, useRef, useEffect, useMemo } from 'react';
import { ChevronDown, Hash, Layers, Target, User, Zap } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface BacklogItem {
  id: number;
  title: string;
  type: 'Epic' | 'Capability' | 'Feature' | 'US' | 'UC';
  description?: string;
}

interface ItemType {
  key: string;
  type: 'Epic' | 'Capability' | 'Feature' | 'US' | 'UC';
  label: string;
  icon: React.ReactNode;
  shortcut: string;
  color: string;
}

interface AutocompleteInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  projectId?: number;
  className?: string;
  disabled?: boolean;
}

const ITEM_TYPES: ItemType[] = [
  {
    key: 'epic',
    type: 'Epic',
    label: 'Epic',
    icon: <Layers className="h-4 w-4" />,
    shortcut: 'e',
    color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
  },
  {
    key: 'capability',
    type: 'Capability', 
    label: 'Capability',
    icon: <Target className="h-4 w-4" />,
    shortcut: 'c',
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
  },
  {
    key: 'feature',
    type: 'Feature',
    label: 'Feature', 
    icon: <Zap className="h-4 w-4" />,
    shortcut: 'f',
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
  },
  {
    key: 'us',
    type: 'US',
    label: 'User Story',
    icon: <User className="h-4 w-4" />,
    shortcut: 'u',
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300'
  },
  {
    key: 'uc',
    type: 'UC', 
    label: 'Use Case',
    icon: <Hash className="h-4 w-4" />,
    shortcut: 'uc',
    color: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300'
  }
];

export function AutocompleteInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Type your message... (use / for item references)",
  projectId,
  className,
  disabled = false
}: AutocompleteInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [autocompleteMode, setAutocompleteMode] = useState<'types' | 'items' | null>(null);
  const [selectedType, setSelectedType] = useState<ItemType | null>(null);
  const [items, setItems] = useState<BacklogItem[]>([]);
  const [isLoadingItems, setIsLoadingItems] = useState(false);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Parse the current autocomplete context from cursor position
  const autocompleteContext = useMemo(() => {
    const cursorPos = inputRef.current?.selectionStart ?? value.length;
    const textBeforeCursor = value.slice(0, cursorPos);
    
    // Look for the last "/" in the text
    const lastSlashIndex = textBeforeCursor.lastIndexOf('/');
    
    if (lastSlashIndex === -1) {
      return { active: false, query: '', startPos: 0 };
    }
    
    // Check if there's whitespace between the slash and cursor
    const afterSlash = textBeforeCursor.slice(lastSlashIndex + 1);
    if (afterSlash.includes(' ') || afterSlash.includes('\n')) {
      return { active: false, query: '', startPos: 0 };
    }
    
    return {
      active: true,
      query: afterSlash.toLowerCase(),
      startPos: lastSlashIndex,
      endPos: cursorPos
    };
  }, [value, inputRef.current?.selectionStart]);

  // Fetch items for a specific type
  const fetchItems = async (type: ItemType) => {
    if (!projectId) return;
    
    setIsLoadingItems(true);
    try {
      const response = await fetch(`/api/items?project_id=${projectId}&type=${type.type}`);
      if (response.ok) {
        const data = await response.json();
        setItems(data || []);
      } else {
        setItems([]);
      }
    } catch (error) {
      console.error('Failed to fetch items:', error);
      setItems([]);
    } finally {
      setIsLoadingItems(false);
    }
  };

  // Filter suggestions based on current mode and query
  const filteredSuggestions = useMemo(() => {
    const { query } = autocompleteContext;
    
    if (autocompleteMode === 'types') {
      return ITEM_TYPES.filter(type => 
        type.label.toLowerCase().includes(query) || 
        type.shortcut.toLowerCase().includes(query) ||
        type.key.toLowerCase().includes(query)
      );
    } else if (autocompleteMode === 'items' && selectedType) {
      return items.filter(item =>
        item.title.toLowerCase().includes(query) ||
        item.description?.toLowerCase().includes(query)
      );
    }
    
    return [];
  }, [autocompleteContext, autocompleteMode, selectedType, items]);

  // Update autocomplete state based on context
  useEffect(() => {
    if (!autocompleteContext.active) {
      setIsOpen(false);
      setAutocompleteMode(null);
      setSelectedType(null);
      setActiveIndex(0);
      return;
    }

    const { query } = autocompleteContext;
    
    // Check if we're selecting a type first
    const typeMatch = ITEM_TYPES.find(type => 
      type.shortcut === query || type.key === query
    );
    
    if (typeMatch && query.length > 0) {
      // User typed a specific type shortcut
      setSelectedType(typeMatch);
      setAutocompleteMode('items');
      fetchItems(typeMatch);
    } else if (selectedType && autocompleteMode === 'items') {
      // Continue with items mode
      setIsOpen(true);
    } else {
      // Show types
      setAutocompleteMode('types');
      setSelectedType(null);
      setIsOpen(true);
    }
    
    setActiveIndex(0);
  }, [autocompleteContext, projectId]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || filteredSuggestions.length === 0) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        onSubmit();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex(prev => Math.min(prev + 1, filteredSuggestions.length - 1));
        break;
        
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex(prev => Math.max(prev - 1, 0));
        break;
        
      case 'Enter':
        e.preventDefault();
        if (filteredSuggestions[activeIndex]) {
          handleSuggestionSelect(filteredSuggestions[activeIndex]);
        }
        break;
        
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        setAutocompleteMode(null);
        break;
        
      case 'Tab':
        if (filteredSuggestions[activeIndex]) {
          e.preventDefault();
          handleSuggestionSelect(filteredSuggestions[activeIndex]);
        }
        break;
    }
  };

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion: ItemType | BacklogItem) => {
    const { startPos, endPos } = autocompleteContext;
    
    if ('type' in suggestion && suggestion.id) {
      // It's a BacklogItem
      const item = suggestion as BacklogItem;
      const replacement = `[${item.type} #${item.id}] `;
      const newValue = value.slice(0, startPos) + replacement + value.slice(endPos || startPos);
      onChange(newValue);
      
      // Move cursor to end of replacement
      setTimeout(() => {
        const newCursorPos = startPos + replacement.length;
        inputRef.current?.setSelectionRange(newCursorPos, newCursorPos);
        inputRef.current?.focus();
      }, 0);
      
    } else {
      // It's an ItemType - switch to items mode
      const itemType = suggestion as ItemType;
      setSelectedType(itemType);
      setAutocompleteMode('items');
      fetchItems(itemType);
      
      // Replace the query with the type shortcut
      const newValue = value.slice(0, startPos + 1) + itemType.shortcut + value.slice(endPos || startPos);
      onChange(newValue);
      
      setTimeout(() => {
        const newCursorPos = startPos + 1 + itemType.shortcut.length;
        inputRef.current?.setSelectionRange(newCursorPos, newCursorPos);
        inputRef.current?.focus();
      }, 0);
    }
    
    setIsOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative">
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className={cn("pr-8", className)}
      />

      {/* Dropdown */}
      {isOpen && filteredSuggestions.length > 0 && (
        <Card
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 max-h-64 overflow-y-auto border shadow-lg"
        >
          <div className="p-1">
            {autocompleteMode === 'types' && (
              <div className="px-2 py-1 text-xs text-muted-foreground border-b mb-1">
                Select item type
              </div>
            )}
            {autocompleteMode === 'items' && selectedType && (
              <div className="px-2 py-1 text-xs text-muted-foreground border-b mb-1 flex items-center gap-2">
                {selectedType.icon}
                {selectedType.label} items
                {isLoadingItems && <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />}
              </div>
            )}

            {filteredSuggestions.map((suggestion, index) => {
              if ('shortcut' in suggestion) {
                // ItemType
                const itemType = suggestion as ItemType;
                return (
                  <div
                    key={itemType.key}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded cursor-pointer transition-colors",
                      index === activeIndex
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-muted/50"
                    )}
                    onClick={() => handleSuggestionSelect(itemType)}
                  >
                    <div className="flex items-center gap-2">
                      {itemType.icon}
                      <span className="font-medium">{itemType.label}</span>
                    </div>
                    <div className="flex items-center gap-2 ml-auto">
                      <Badge variant="outline" className="text-xs">
                        /{itemType.shortcut}
                      </Badge>
                    </div>
                  </div>
                );
              } else {
                // BacklogItem
                const item = suggestion as BacklogItem;
                return (
                  <div
                    key={item.id}
                    className={cn(
                      "flex items-start gap-3 px-3 py-2 rounded cursor-pointer transition-colors",
                      index === activeIndex
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-muted/50"
                    )}
                    onClick={() => handleSuggestionSelect(item)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{item.title}</span>
                        <Badge variant="outline" className="text-xs">
                          #{item.id}
                        </Badge>
                      </div>
                      {item.description && (
                        <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {item.description}
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
            })}

            {autocompleteMode === 'items' && filteredSuggestions.length === 0 && !isLoadingItems && (
              <div className="px-3 py-2 text-sm text-muted-foreground">
                No {selectedType?.label.toLowerCase()} items found
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}