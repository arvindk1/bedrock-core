import React from 'react';
import { PIPELINE_STAGES } from '../constants';
import { ChevronRight } from 'lucide-react';

interface PipelineBarProps {
  selectedStageId: string;
  onSelectStage: (id: string) => void;
}

export const PipelineBar: React.FC<PipelineBarProps> = ({ selectedStageId, onSelectStage }) => {
  return (
    <div className="w-full bg-slate-950 border-y border-slate-800 mb-6 shadow-sm">
      <div className="flex items-center justify-between max-w-[1600px] mx-auto">
        {PIPELINE_STAGES.map((stage, index) => {
          const isLast = index === PIPELINE_STAGES.length - 1;
          const isSelected = selectedStageId === stage.id;
          
          let colorClass = 'text-slate-500';
          let countClass = 'bg-slate-800 text-slate-400';
          let borderClass = 'border-transparent';

          if (isSelected) {
             borderClass = 'border-indigo-500 bg-slate-900';
             colorClass = 'text-white';
          }

          if (stage.status === 'warning') {
            if(isSelected) {
                 borderClass = 'border-amber-500 bg-amber-950/20';
                 colorClass = 'text-amber-100';
            } else {
                 colorClass = 'text-amber-500/80';
            }
            countClass = 'bg-amber-900/40 text-amber-200 border border-amber-900/50';
          } else if (stage.status === 'success') {
             if(isSelected) {
                 borderClass = 'border-emerald-500 bg-emerald-950/20';
                 colorClass = 'text-emerald-100';
             } else {
                 colorClass = 'text-emerald-500/80';
             }
            countClass = 'bg-emerald-900/40 text-emerald-200 border border-emerald-900/50';
          } else if (stage.status === 'critical') {
             if(isSelected) {
                 borderClass = 'border-rose-500 bg-rose-950/20';
                 colorClass = 'text-rose-100';
             } else {
                 colorClass = 'text-rose-500/80';
             }
             countClass = 'bg-rose-900/40 text-rose-200 border border-rose-900/50';
          }

          return (
            <React.Fragment key={stage.id}>
              <div 
                onClick={() => onSelectStage(stage.id)}
                className={`flex-1 flex items-center justify-between px-6 py-3 border-b-2 cursor-pointer transition-all hover:bg-slate-900 ${borderClass} group`}
              >
                <span className={`text-xs font-bold uppercase tracking-widest transition-colors ${colorClass} group-hover:text-white`}>
                  {stage.label}
                </span>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-[2px] ${countClass}`}>
                  {stage.count}
                </span>
              </div>
              {!isLast && (
                <div className="px-2 text-slate-800">
                  <ChevronRight size={16} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
