import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { PORTFOLIO_RISK, CORRELATION_MATRIX, CORRELATION_LABELS } from '../constants';
import { TrendingDown, ShieldAlert, Zap } from 'lucide-react';

export const RiskDashboard: React.FC = () => {
  return (
    <div className="space-y-4 h-full">
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-900 p-3 rounded-sm border border-slate-800">
            <div className="flex items-center space-x-2 text-slate-400 mb-1">
               <ShieldAlert size={14} />
               <span className="text-xs uppercase font-bold">Cap At Risk</span>
            </div>
            <span className="text-lg font-mono font-bold text-slate-100">${PORTFOLIO_RISK.totalCapitalAtRisk.toLocaleString()}</span>
        </div>
        <div className="bg-slate-900 p-3 rounded-sm border border-slate-800">
             <div className="flex items-center space-x-2 text-slate-400 mb-1">
               <TrendingDown size={14} />
               <span className="text-xs uppercase font-bold">Daily DD</span>
            </div>
            <span className="text-lg font-mono font-bold text-amber-500">{PORTFOLIO_RISK.dailyDrawdown}%</span>
        </div>
         <div className="bg-slate-900 p-3 rounded-sm border border-slate-800 col-span-2">
             <div className="flex items-center space-x-2 text-slate-400 mb-1">
               <Zap size={14} />
               <span className="text-xs uppercase font-bold">Net Portfolio Delta</span>
            </div>
            <div className="flex items-end justify-between">
               <span className="text-lg font-mono font-bold text-emerald-400">+{PORTFOLIO_RISK.netDelta.toFixed(1)}</span>
               <div className="h-1.5 w-24 bg-slate-700 rounded-full overflow-hidden">
                 <div className="h-full bg-emerald-500 w-[60%]"></div>
               </div>
            </div>
        </div>
      </div>

      {/* Sector Exposure Chart */}
      <div className="bg-slate-900 p-4 rounded-sm border border-slate-800 h-64">
         <h4 className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-4">Sector Exposure (%)</h4>
         <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={PORTFOLIO_RISK.sectorExposure} layout="vertical" margin={{ left: 0, right: 30 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" width={50} tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }} axisLine={false} tickLine={false} />
                <Tooltip 
                  cursor={{fill: '#1e293b'}} 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }} 
                  itemStyle={{ color: '#e2e8f0' }}
                />
                <Bar dataKey="value" barSize={12} radius={[0, 2, 2, 0]}>
                    {PORTFOLIO_RISK.sectorExposure.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#6366f1' : '#4f46e5'} />
                    ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
         </div>
      </div>

      {/* Correlation Matrix (Custom Grid) */}
      <div className="bg-slate-900 p-4 rounded-sm border border-slate-800">
         <h4 className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-3">Asset Correlation</h4>
         <div className="grid grid-cols-6 gap-1">
            <div className="col-span-1"></div>
            {CORRELATION_LABELS.map(l => (
              <div key={l} className="text-[10px] text-center text-slate-500 font-mono">{l}</div>
            ))}
            
            {CORRELATION_MATRIX.map((row, i) => (
               <React.Fragment key={i}>
                 <div className="text-[10px] text-right text-slate-500 font-mono pr-2 self-center">{CORRELATION_LABELS[i]}</div>
                 {row.map((val, j) => {
                   let bg = 'bg-slate-800';
                   if (val === 1) bg = 'bg-slate-700 text-slate-500';
                   else if (val > 0.7) bg = 'bg-rose-900/60 text-rose-300';
                   else if (val > 0.4) bg = 'bg-amber-900/50 text-amber-300';
                   else if (val < 0) bg = 'bg-emerald-900/50 text-emerald-300';
                   else bg = 'bg-slate-800 text-slate-400';

                   return (
                     <div key={`${i}-${j}`} className={`h-6 flex items-center justify-center text-[9px] font-mono rounded-[1px] ${bg}`}>
                       {val === 1 ? '' : val.toFixed(1)}
                     </div>
                   )
                 })}
               </React.Fragment>
            ))}
         </div>
      </div>
    </div>
  );
};
