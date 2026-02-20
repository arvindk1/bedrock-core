import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';
import { PORTFOLIO_RISK, MOCK_POSITIONS, CORRELATION_MATRIX, CORRELATION_LABELS } from '../constants';
import { AlertTriangle, TrendingUp, Clock, ShieldAlert, Zap, Activity, MoreHorizontal, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export const PortfolioView: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
        
        {/* TOP SECTION: AGGREGATE RISK METRICS */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Capital At Risk */}
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-sm flex flex-col justify-between">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Capital Utilization</span>
                    <ShieldAlert size={14} className="text-amber-500" />
                </div>
                <div>
                    <div className="text-2xl font-mono font-bold text-slate-100">$145,250</div>
                    <div className="w-full bg-slate-800 h-1.5 mt-3 rounded-full overflow-hidden">
                        <div className="bg-amber-500 h-full w-[45%]"></div>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-2 text-right">45% of Buying Power</div>
                </div>
            </div>

            {/* Net Delta */}
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-sm flex flex-col justify-between">
                 <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Net Portfolio Delta</span>
                    <TrendingUp size={14} className="text-emerald-500" />
                </div>
                <div>
                    <div className="text-2xl font-mono font-bold text-emerald-400">+{PORTFOLIO_RISK.netDelta}</div>
                    <div className="flex items-center space-x-2 mt-2">
                         <span className="text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">SPY Beta: 0.85</span>
                         <span className="text-[10px] text-slate-500">Long Bias</span>
                    </div>
                </div>
            </div>

            {/* Daily Drawdown */}
             <div className="bg-slate-900 border border-slate-800 p-4 rounded-sm flex flex-col justify-between">
                 <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Daily P/L & DD</span>
                    <Activity size={14} className="text-rose-500" />
                </div>
                <div>
                    <div className="flex items-end space-x-2">
                         <div className="text-2xl font-mono font-bold text-rose-400">-0.45%</div>
                         <div className="text-sm font-mono text-slate-500 mb-1">(-$1,240)</div>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-2">Max Drawdown Limit: -2.00%</div>
                </div>
            </div>

             {/* Volatility Exposure */}
             <div className="bg-slate-900 border border-slate-800 p-4 rounded-sm flex flex-col justify-between">
                 <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Net Vega / Theta</span>
                    <Zap size={14} className="text-indigo-500" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <span className="block text-[10px] text-slate-500">Short Vega</span>
                        <span className="text-lg font-mono font-bold text-rose-300">-420</span>
                    </div>
                     <div>
                        <span className="block text-[10px] text-slate-500">Daily Theta</span>
                        <span className="text-lg font-mono font-bold text-emerald-300">+$850</span>
                    </div>
                </div>
            </div>
        </div>

        {/* MIDDLE SECTION: CHARTS & MATRIX */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-80">
            {/* Sector Exposure */}
            <div className="bg-slate-900 border border-slate-800 rounded-sm p-5 flex flex-col">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-4">Sector Concentration Risk</h3>
                <div className="flex-grow w-full h-full min-h-0">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={PORTFOLIO_RISK.sectorExposure} layout="vertical" margin={{ left: 10, right: 30, top: 10, bottom: 0 }}>
                            <XAxis type="number" hide />
                            <YAxis dataKey="name" type="category" width={60} tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'monospace', fontWeight: 'bold' }} axisLine={false} tickLine={false} />
                            <Tooltip 
                                cursor={{fill: '#1e293b'}} 
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }} 
                                itemStyle={{ color: '#e2e8f0' }}
                            />
                            <Bar dataKey="value" barSize={16} radius={[0, 4, 4, 0]}>
                                {PORTFOLIO_RISK.sectorExposure.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={index === 0 ? '#6366f1' : '#334155'} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Correlation Matrix - Full Size */}
            <div className="bg-slate-900 border border-slate-800 rounded-sm p-5">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest">Cross-Asset Correlation</h3>
                    <span className="text-[10px] text-slate-500 font-mono">Lookback: 30D</span>
                </div>
                
                <div className="h-full flex flex-col justify-center">
                    <div className="grid grid-cols-6 gap-1">
                        <div className="col-span-1"></div>
                        {CORRELATION_LABELS.map(l => (
                        <div key={l} className="text-xs text-center text-slate-400 font-mono font-bold">{l}</div>
                        ))}
                        
                        {CORRELATION_MATRIX.map((row, i) => (
                        <React.Fragment key={i}>
                            <div className="text-xs text-right text-slate-400 font-mono font-bold pr-3 self-center">{CORRELATION_LABELS[i]}</div>
                            {row.map((val, j) => {
                            let bg = 'bg-slate-800';
                            let text = 'text-slate-500';
                            
                            if (val === 1) { bg = 'bg-slate-800'; text = 'text-slate-600'; }
                            else if (val > 0.7) { bg = 'bg-rose-900/80'; text = 'text-rose-200'; }
                            else if (val > 0.4) { bg = 'bg-amber-900/60'; text = 'text-amber-200'; }
                            else if (val < -0.4) { bg = 'bg-emerald-900/60'; text = 'text-emerald-200'; }
                            
                            return (
                                <div key={`${i}-${j}`} className={`aspect-square flex items-center justify-center text-xs font-mono rounded-sm transition-transform hover:scale-105 ${bg} ${text}`}>
                                {val === 1 ? '1.0' : val.toFixed(1)}
                                </div>
                            )
                            })}
                        </React.Fragment>
                        ))}
                    </div>
                </div>
            </div>
        </div>

        {/* BOTTOM SECTION: ACTIVE POSITIONS */}
        <div className="bg-slate-900 border border-slate-800 rounded-sm overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest">Active Positions</h3>
                <div className="flex space-x-2">
                    <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Normal</span>
                    <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Warning</span>
                    <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Critical</span>
                </div>
            </div>
            
            <table className="w-full text-left border-collapse">
                <thead className="bg-slate-950 text-[10px] text-slate-500 uppercase font-bold">
                    <tr>
                        <th className="p-4 border-b border-slate-800">Symbol</th>
                        <th className="p-4 border-b border-slate-800">Strategy</th>
                        <th className="p-4 border-b border-slate-800 text-right">Qty</th>
                        <th className="p-4 border-b border-slate-800 text-right">Cost Basis</th>
                        <th className="p-4 border-b border-slate-800 text-right">Mark</th>
                        <th className="p-4 border-b border-slate-800 text-right">Unrealized P/L</th>
                        <th className="p-4 border-b border-slate-800">Risk Alerts</th>
                        <th className="p-4 border-b border-slate-800 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody className="text-xs font-mono">
                    {MOCK_POSITIONS.map(pos => (
                        <tr key={pos.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30 transition-colors group">
                            <td className="p-4 font-bold text-white flex items-center space-x-2">
                                <span>{pos.symbol}</span>
                                {pos.status === 'Critical' && <ShieldAlert size={12} className="text-rose-500 animate-pulse"/>}
                            </td>
                            <td className="p-4 text-slate-400">{pos.strategy}</td>
                            <td className="p-4 text-right text-slate-300">{pos.quantity}</td>
                            <td className="p-4 text-right text-slate-500">{pos.entryPrice.toFixed(2)}</td>
                            <td className="p-4 text-right text-slate-300">{pos.currentPrice.toFixed(2)}</td>
                            <td className="p-4 text-right">
                                <div className={`font-bold ${pos.plOpen >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {pos.plOpen >= 0 ? '+' : ''}{pos.plOpen}
                                </div>
                                <div className={`text-[10px] ${pos.plOpen >= 0 ? 'text-emerald-500/70' : 'text-rose-500/70'}`}>
                                    {pos.plOpenPercent}%
                                </div>
                            </td>
                            <td className="p-4">
                                {pos.alerts.map((alert, i) => (
                                    <span key={i} className="inline-flex items-center px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-slate-800 border border-slate-700 text-slate-400 mr-2">
                                        {alert}
                                    </span>
                                ))}
                                {pos.alerts.length === 0 && <span className="text-slate-600 text-[10px] italic">No active alerts</span>}
                            </td>
                            <td className="p-4 text-right">
                                <div className="flex justify-end space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white" title="Analyze">
                                        <Activity size={14} />
                                    </button>
                                    <button className="p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-white" title="Adjust / Roll">
                                        <MoreHorizontal size={14} />
                                    </button>
                                     <button className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded text-[10px] text-slate-300 font-bold">
                                        CLOSE
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
  );
};
