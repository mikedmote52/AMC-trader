import React, { useState } from "react";

export default function RecommendationCard({ item, onBuy }: { item: any, onBuy: (sym:string)=>void }) {
  const p = (x:number|undefined)=> (x==null? "—" : (Math.abs(x)>=1? x.toFixed(2) : x.toFixed(3)));
  const pct = (x:number|undefined)=> (x==null? "—" : `${(x*100).toFixed(1)}%`);
  return (
    <div className="bg-slate-800 rounded-2xl p-4 shadow-md">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xl font-semibold">{item.symbol}</h3>
        <button className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded-lg" onClick={()=>onBuy(item.symbol)}>Buy</button>
      </div>
      <p className="text-sm opacity-80">{item.thesis}</p>
      <div className="grid grid-cols-3 gap-2 text-sm mt-3">
        <div><span className="opacity-70">Price</span><div>${p(item.price)}</div></div>
        <div><span className="opacity-70">Tightness</span><div>{(item.score*100).toFixed(1)}%</div></div>
        <div><span className="opacity-70">5d RS</span><div>{pct(item.rs_5d)}</div></div>
        <div><span className="opacity-70">ATR%</span><div>{pct(item.atr_pct)}</div></div>
        <div><span className="opacity-70">$ Vol</span><div>${Math.round((item.dollar_vol||0)/1_000_000)}M</div></div>
      </div>
    </div>
  );
}