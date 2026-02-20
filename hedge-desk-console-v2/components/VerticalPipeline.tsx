import React from 'react';
import { PIPELINE_STAGES } from '../constants';
import { ArrowDown, Check, X, Filter } from 'lucide-react';

interface VerticalPipelineProps {
  selectedStageId: string;
  onSelectStage: (id: string) => void;
}

export const VerticalPipeline: React.FC<VerticalPipelineProps> = ({ selectedStageId, onSelectStage }) => {
  return (
    <div className="flex flex-col space-y-2">
      {PIPELINE_STAGES.map((stage, index) => {
        const isLast = index === PIPELINE_STAGES.length - 1;
        const isSelected = selectedStageId === stage.id;
        
        // Dynamic colors based on status and selection
        let containerClass = "bg-slate-900 border-slate-800 text-slate-500";
        if (isSelected) containerClass = "bg-indigo-900/20 border-indigo-500/50 text-indigo-200 ring-1 ring-indigo-500/30";
        else if (stage.status === 'success') containerClass = "bg-emerald-900/10 border-emerald-900/30 text-emerald-200";
        else if (stage.status === 'warning') containerClass = "bg-amber-900/10 border-amber-900/30 text-amber-200";

        return (
          <div key={stage.id} className="relative group">
            <div 
                onClick={() => onSelectStage(stage.id)}
                className={`flex items-center justify-between p-4 border rounded-sm cursor-pointer transition-all hover:bg-slate-800 ${containerClass}`}
            >
                <div className="flex items-center space-x-3">
                    {stage.id === 'gen' && <Filter size={16} />}
                    {stage.status === 'warning' && <X size={16} className="text-amber-500" />}
                    {stage.status === 'success' && <Check size={16} className="text-emerald-500" />}
                    <span className="text-xs font-bold uppercase tracking-widest">{stage.label}</span>
                </div>
                <span className="text-sm font-mono font-bold">{stage.count}</span>
            </div>
            
            {/* Visual connector line */}
            {!isLast && (
                <div className="h-4 flex justify-center items-center">
                    <div className="w-px h-full bg-slate-800"></div>
                </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
