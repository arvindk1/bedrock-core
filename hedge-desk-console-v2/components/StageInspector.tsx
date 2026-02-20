import React from 'react';
import { MOCK_REJECTIONS } from '../constants';
import { Shield, Activity, Link2, AlertTriangle, XCircle, Search } from 'lucide-react';

interface StageInspectorProps {
  stageId: string;
}

export const StageInspector: React.FC<StageInspectorProps> = ({ stageId }) => {
  // Map stage ID to rejection category for mock data
  let category: 'Risk' | 'Gatekeeper' | 'Correlation' | null = null;
  let title = 'Pipeline Inspection';
  let description = 'Detailed view of filtered candidates.';
  
  switch(stageId) {
    case 'risk':
        category = 'Risk';
        title = 'Risk Gate Rejections';
        description = 'Trades filtered due to excessive portfolio risk parameters.';
        break;
    case 'gate':
        category = 'Gatekeeper';
        title = 'Gatekeeper Logic';
        description = 'Trades failing quantitative scoring thresholds (IV Rank, Liquidity).';
        break;
    case 'corr':
        category = 'Correlation';
        title = 'Correlation Matrix Filters';
        description = 'Trades removed to prevent over-concentration in correlated assets.';
        break;
    default:
        category = null;
  }

  const items = category ? MOCK_REJECTIONS.filter(r => r.category === category) : [];

  if (!category) {
      return (
          <div className="bg-slate-900 border border-slate-800 p-8 text-center rounded-sm">
              <Search className="mx-auto text-slate-600 mb-2" size={32} />
              <h3 className="text-slate-300 font-bold">Raw Candidate Data</h3>
              <p className="text-slate-500 text-sm mt-1">Select a filtered stage (Risk, Gatekeeper, Correlation) to inspect rejections.</p>
          </div>
      )
  }

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-sm flex flex-col h-full animate-in fade-in duration-300">
      <div className="p-4 border-b border-slate-700 bg-slate-900 flex justify-between items-start">
         <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                {stageId === 'risk' && <Shield size={16} className="text-amber-500" />}
                {stageId === 'gate' && <Activity size={16} className="text-indigo-500" />}
                {stageId === 'corr' && <Link2 size={16} className="text-emerald-500" />}
                {title}
            </h3>
            <p className="text-xs text-slate-400 mt-1 font-mono">{description}</p>
         </div>
         <span className="text-xs font-mono bg-slate-800 px-2 py-1 rounded text-slate-300">
            Count: {items.length}
         </span>
      </div>

      <div className="overflow-auto">
        <table className="w-full text-left border-collapse">
            <thead className="bg-slate-950 text-[10px] text-slate-500 uppercase font-bold sticky top-0">
              <tr>
                <th className="p-3 border-b border-slate-800 w-16">Time</th>
                <th className="p-3 border-b border-slate-800 w-20">Symbol</th>
                <th className="p-3 border-b border-slate-800 w-32">Strategy</th>
                <th className="p-3 border-b border-slate-800 w-32">Reason Code</th>
                <th className="p-3 border-b border-slate-800">Message</th>
              </tr>
            </thead>
            <tbody className="text-xs font-mono text-slate-400">
              {items.map(item => (
                <tr key={item.id} className="hover:bg-slate-800/30 transition-colors border-b border-slate-800/50">
                  <td className="p-3 text-slate-500">{item.timestamp}</td>
                  <td className="p-3 font-bold text-indigo-200">{item.symbol}</td>
                  <td className="p-3 text-slate-400">{item.strategy}</td>
                  <td className="p-3 text-rose-400 font-bold">{item.reasonCode}</td>
                  <td className="p-3 text-slate-400">{item.message}</td>
                </tr>
              ))}
              {items.length === 0 && (
                  <tr>
                      <td colSpan={5} className="p-8 text-center text-slate-500 italic">No rejection data available for this session.</td>
                  </tr>
              )}
            </tbody>
        </table>
      </div>
    </div>
  );
};
