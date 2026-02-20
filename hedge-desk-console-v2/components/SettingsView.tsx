import React from 'react';
import { StrategyControls } from './StrategyControls';

export const SettingsView: React.FC = () => {
  return (
    <div>
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-4">System Configuration & Lab</h2>
        <p className="text-xs text-slate-500 mb-6 max-w-2xl">
            Adjust global execution parameters, risk thresholds, and scan sensitivity. 
            Changes here affect the "Discovery Mode" pipeline immediately.
        </p>
        <StrategyControls />
    </div>
  );
};
