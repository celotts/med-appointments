import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface UnsavedChangesContextType {
  hasUnsavedChanges: boolean;
  registerUnsavedChanges: (componentId: string, hasChanges: boolean) => void;
  unregisterUnsavedChanges: (componentId: string) => void;
}

const UnsavedChangesContext = createContext<UnsavedChangesContextType | undefined>(undefined);

export const UnsavedChangesProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [dirtyComponents, setDirtyComponents] = useState<Record<string, boolean>>({});

  const registerUnsavedChanges = useCallback((componentId: string, hasChanges: boolean) => {
    setDirtyComponents(prev => ({ ...prev, [componentId]: hasChanges }));
  }, []);

  const unregisterUnsavedChanges = useCallback((componentId: string) => {
    setDirtyComponents(prev => {
      const next = { ...prev };
      delete next[componentId];
      return next;
    });
  }, []);

  const hasUnsavedChanges = Object.values(dirtyComponents).some(v => v);

  return (
    <UnsavedChangesContext.Provider value={{ hasUnsavedChanges, registerUnsavedChanges, unregisterUnsavedChanges }}>
      {children}
    </UnsavedChangesContext.Provider>
  );
};

export const useUnsavedChanges = () => {
  const context = useContext(UnsavedChangesContext);
  if (!context) {
    throw new Error('useUnsavedChanges must be used within an UnsavedChangesProvider');
  }
  return context;
};

export default UnsavedChangesContext;