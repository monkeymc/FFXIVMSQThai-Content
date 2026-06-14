"use client";
import { useEffect, useState } from "react";

export default function StickyHeader({ 
  filePath, 
  dialogueCount 
}: { 
  filePath: string; 
  dialogueCount: number;
}) {
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const scrollContainer = document.getElementById('scroll-container');
    
    const handleScroll = () => {
      if (!scrollContainer) return;
      
      const totalScroll = scrollContainer.scrollTop;
      const windowHeight = scrollContainer.scrollHeight - scrollContainer.clientHeight;
      
      if (windowHeight <= 0) {
        setScrollProgress(0);
        return;
      }
      
      const progress = totalScroll / windowHeight;
      setScrollProgress(progress);
    };

    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', handleScroll);
      // รันครั้งแรกเผื่อเคสที่เนื้อหาไม่ยาวพอให้เลื่อน
      handleScroll();
    }
    
    return () => {
      if (scrollContainer) {
        scrollContainer.removeEventListener('scroll', handleScroll);
      }
    };
  }, [filePath]);

  // เลือกลูกเล่นข้อความให้กำลังใจตามเปอร์เซ็นต์ที่เลื่อน
  let encouragement = "มาเริ่มแปลกันเลย! ✌️";
  let color = "text-[var(--color-ffxiv-muted)]";

  if (scrollProgress >= 0.95) {
    encouragement = "จบเควสต์แล้ว! เก่งมากครับ 🎉";
    color = "text-green-400 font-bold drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]";
  } else if (scrollProgress >= 0.75) {
    encouragement = "ใกล้จะจบแล้ว อีกอึดใจเดียว! 🔥";
    color = "text-orange-400";
  } else if (scrollProgress >= 0.5) {
    encouragement = "มาได้ครึ่งทางแล้ว สุดยอด! ✨";
    color = "text-yellow-400";
  } else if (scrollProgress >= 0.2) {
    encouragement = "กำลังไปได้สวยเลย ลุยต่อครับ! 🚀";
    color = "text-[var(--color-ffxiv-gold-light)]";
  }

  // เลือกลูกเล่นสีหลอด EXP ตามเปอร์เซ็นต์ที่เลื่อน
  let expColor = "from-blue-700 via-blue-500 to-cyan-400"; // ช่วงเริ่มต้น (Blue)
  if (scrollProgress >= 0.95) {
    expColor = "from-green-600 via-emerald-400 to-green-300"; // ใกล้เสร็จ (Green)
  } else if (scrollProgress >= 0.6) {
    expColor = "from-[#8b6b22] via-[#d4af37] to-[#fce488]"; // ค่อนข้างเยอะ (Gold)
  } else if (scrollProgress >= 0.3) {
    expColor = "from-purple-700 via-fuchsia-500 to-pink-400"; // ครึ่งทาง (Purple)
  }

  return (
    <div className="flex-none px-6 py-4 flex justify-between items-center border-b border-[var(--color-panel-border)] z-20">
      <div>
        <h2 className="text-xl font-semibold text-[var(--color-ffxiv-text)]">
          <span className="text-[var(--color-ffxiv-gold-light)]">{filePath}</span>
        </h2>
      </div>
      
      {/* โซนให้กำลังใจ (Gamified Progress) */}
      <div className="hidden sm:flex flex-col justify-end w-64 relative pt-12 pb-1">
        {/* GIF ตัวละครที่วิ่งไปตามหลอด */}
        <div 
          className="absolute bottom-3 transition-all duration-300 ease-out z-10"
          style={{ 
            left: `${Math.max(0, Math.min(100, scrollProgress * 100))}%`, 
            transform: `translateX(-${Math.max(0, Math.min(100, scrollProgress * 100))}%)` 
          }}
        >
          <img 
            src="https://media1.tenor.com/m/aE183c3f36QAAAAC/ffxiv-ff14.gif" 
            alt="FFXIV running" 
            className="h-10 w-auto max-w-none flex-shrink-0 drop-shadow-lg"
          />
        </div>
        
        {/* หลอด Progress Bar สไตล์หลอด EXP */}
        <div className="w-full bg-[var(--color-progress-bg)] rounded-full h-2.5 border border-[var(--color-panel-border)] shadow-inner overflow-hidden relative">
          {/* ขีดบอกระยะ */}
          <div className="absolute inset-0 flex justify-between px-1/4 opacity-20 pointer-events-none">
            <div className="h-full w-px bg-white ml-[25%]"></div>
            <div className="h-full w-px bg-white ml-[25%]"></div>
            <div className="h-full w-px bg-white ml-[25%]"></div>
          </div>
          {/* ตัวหลอด */}
          <div 
            className="absolute left-0 top-0 h-full transition-all duration-300 ease-out bg-gradient-to-r from-[#b8860b] via-[#d4af37] to-[#f0c265]"
            style={{ width: `${Math.max(2, scrollProgress * 100)}%` }}
          >
            {/* แสงวิบวับปลายหลอด */}
            <div className="absolute right-0 top-0 bottom-0 w-4 bg-white opacity-40 blur-[2px]"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
