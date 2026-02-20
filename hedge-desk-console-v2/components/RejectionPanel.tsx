import React, { useState } from 'react';
import { MOCK_REJECTIONS } from '../constants';
import { XCircle, Shield, Link2, Activity } from 'lucide-react';

export const RejectionPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'Risk' | 'Gatekeeper' | 'Correlation'>('Risk');

  const filteredRejections = MOCK_REJECTIONS.filter(r => r.category === activeTab);

  const TabButton = ({ category, icon: Icon }: { category: 'Risk' | 'Gatekeeper' | 'Correlation', icon: any }) => (
    <button
      onClick={() => setActiveTab(category)}
      className={`flex items-center space-x-2 px-4 py-2 text-xs font-bold uppercase tracking-wide border-b-2 transition-colors ${
        activeTab === category 
          ? 'border-indigo-500 text-indigo-400 bg-slate-800/50' 
          : 'border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-800/30'
      }`}
    >
      <Icon size={14} />
      <span>{category} ({MOCK_REJECTIONS.filter(r => r.category === category).length})</span>
    </button>
  );

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-sm mt-6">
      <div className="flex border-b border-slate-700">
        <TabButton category="Risk" icon={Shield} />
        <TabButton category="Gatekeeper" icon={Activity} />
        <TabButton category="Correlation" icon={Link2} />
      </div>

      <div className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-950 text-xs text-slate-500 uppercase font-bold">
              <tr>
                <th className="p-3 border-b border-slate-800 w-16">Time</th>
                <th className="p-3 border-b border-slate-800 w-20">Symbol</th>
                <th className="p-3 border-b border-slate-800">Reason Code</th>
                <th className="p-3 border-b border-slate-800">Description</th>
              </tr>
            </thead>
            <tbody className="text-sm font-mono text-slate-400">
              {filteredRejections.map(rej => (
                <tr key={rej.id} className="hover:bg-slate-800/30 transition-colors border-b border-slate-800/50 last:border-0">
                  <td className="p-3 text-slate-500 text-xs">{rej.timestamp}</td>
                  <td className="p-3 font-bold text-slate-300">{rej.symbol}</td>
                  <td className="p-3 text-rose-400">{rej.reasonCode}</td>
                  <td className="p-3 text-slate-400">{rej.message}</td>
                </tr>
              ))}
              {filteredRejections.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-slate-600 text-sm">
                    No rejections in this category.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
