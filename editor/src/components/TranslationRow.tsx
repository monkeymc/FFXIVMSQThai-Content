"use client";
import { useRef, useState } from "react";
import AutoResizeTextarea, { AutoResizeTextareaHandle } from "./AutoResizeTextarea";

import { TextChunk } from "@/lib/parser";

export default function TranslationRow({ 
  chunks, 
  defaultTextTh,
  name
}: { 
  chunks: TextChunk[]; 
  defaultTextTh: string;
  name: string;
}) {
  const handleRef = useRef<AutoResizeTextareaHandle>(null);
  const [isModified, setIsModified] = useState(false);

  const handleReset = () => {
    if (handleRef.current && handleRef.current.textarea) {
      // 1. Reset the text
      handleRef.current.textarea.value = defaultTextTh;
      // 2. Call the adjustHeight directly exposed via useImperativeHandle
      handleRef.current.adjustHeight();
      setIsModified(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setIsModified(e.target.value !== defaultTextTh);
  };

  return (
    <div className={`ffxiv-panel p-5 flex flex-col gap-3 group relative transition-colors border ${isModified ? 'border-[var(--color-ffxiv-gold)] shadow-[0_0_15px_rgba(212,175,55,0.15)]' : 'border-transparent focus-within:border-gray-600'}`}>
      
      {/* Modified Badge */}
      {isModified && (
        <div className="absolute -left-2 -top-2 bg-[var(--color-btn-from)] text-[var(--color-btn-text)] text-xs font-bold px-2 py-0.5 rounded shadow-md transform -rotate-6 z-10 border border-[var(--color-panel-border)]">
          EDITED
        </div>
      )}

      {/* English Original */}
      <div className="text-lg text-[var(--color-ffxiv-text)] leading-relaxed">
        {chunks.map((chunk, i) => {
          if (chunk.type === "search") {
            return (
              <span key={i} className="bg-[var(--color-btn-from)] text-[var(--color-btn-text)] px-1 rounded font-bold">
                {chunk.content}
              </span>
            );
          } else if (chunk.type === "glossary") {
            return (
              <span 
                key={i} 
                className="group/tooltip relative inline-block border-b-2 border-dotted border-[var(--color-ffxiv-gold)] text-[var(--color-ffxiv-gold)] font-semibold cursor-help transition-colors hover:bg-[var(--color-btn-from)] hover:text-[var(--color-btn-text)]"
              >
                {chunk.content}
                {chunk.tooltip && (
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs px-3 py-1.5 bg-black text-white text-sm rounded shadow-lg opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none z-50">
                    {chunk.tooltip}
                    <svg className="absolute text-black w-3 h-3 left-1/2 -translate-x-1/2 top-full" x="0px" y="0px" viewBox="0 0 255 255" xmlSpace="preserve"><polygon className="fill-current" points="0,0 127.5,127.5 255,0"/></svg>
                  </span>
                )}
              </span>
            );
          }
          return <span key={i}>{chunk.content}</span>;
        })}
      </div>
      
      {/* Thai Translation */}
      <div className="flex gap-2">
        <AutoResizeTextarea 
          ref={handleRef}
          name={name}
          onChange={handleChange}
          className={`w-full bg-[var(--color-input-bg)] border rounded p-3 text-[var(--color-ffxiv-text)] text-lg focus:outline-none focus:ring-1 transition-all ${isModified ? 'border-[var(--color-ffxiv-gold-light)] focus:border-[var(--color-ffxiv-gold-light)] focus:ring-[var(--color-ffxiv-gold-light)]' : 'border-[var(--color-input-border)] focus:border-gray-500 focus:ring-gray-500'}`}
          defaultValue={defaultTextTh}
        />
      </div>

      {/* Action Buttons */}
      <div className={`flex justify-end mt-1 transition-opacity ${isModified ? 'opacity-100' : 'opacity-0 group-focus-within:opacity-100 group-hover:opacity-100'}`}>
        <button 
          type="button" 
          onClick={handleReset}
          className="px-3 py-1 text-xs border border-[var(--color-panel-border)] text-[var(--color-ffxiv-muted)] rounded hover:bg-red-900/50 hover:text-red-300 hover:border-red-800 transition-colors"
        >
          ⟲ Undo Changes
        </button>
      </div>
    </div>
  );
}
