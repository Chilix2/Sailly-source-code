'use client';
import React from 'react';
export function TranscriptViewer({ words, currentTime, onWordClick }) {
    return (<div className="space-y-3 font-mono text-sm">
      {words.map((word, idx) => (<div key={idx} className="flex gap-2">
          <span className={`text-xs min-w-12 ${word.speaker === 'caller' ? 'text-accent-warn' : 'text-accent-3'}`}>
            {word.speaker.toUpperCase()}
          </span>
          <button onClick={() => onWordClick(word.timestamp)} className={`transition-colors ${Math.abs(word.timestamp - currentTime) < 0.5
                ? 'bg-accent/20 text-accent font-semibold'
                : 'hover:text-accent cursor-pointer'}`}>
            {word.word}
          </button>
        </div>))}
    </div>);
}
