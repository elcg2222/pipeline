import React, { useState } from 'react';
import { Film, Play } from 'lucide-react';

interface ImageWithFallbackProps {
  src?: string;
  alt: string;
  className?: string;
  category?: string;
}

export const ImageWithFallback: React.FC<ImageWithFallbackProps> = ({
  src,
  alt,
  className = '',
  category = 'video'
}) => {
  const [error, setError] = useState(false);

  if (!src || error) {
    return (
      <div 
        className={`bg-gradient-to-br from-orange-100 via-amber-50 to-orange-200/50 flex flex-col items-center justify-center relative overflow-hidden text-orange-950 select-none ${className}`}
      >
        <div className="absolute inset-0 bg-[radial-gradient(#ea580c_1px,transparent_1px)] [background-size:16px_16px] opacity-15" />
        <div className="relative z-10 w-10 h-10 rounded-full bg-white/90 shadow-sm border border-orange-200/60 flex items-center justify-center text-orange-600 mb-1.5">
          <Play className="w-4 h-4 fill-orange-500 text-orange-500 ml-0.5" />
        </div>
        <span className="relative z-10 text-[11px] font-semibold text-stone-700 px-3 text-center truncate max-w-full">
          {alt || 'Video Preview'}
        </span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      referrerPolicy="no-referrer"
      onError={() => setError(true)}
      className={className}
    />
  );
};
