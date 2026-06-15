"use client";
import { useEffect, useMemo, useState } from "react";

// ชุดสีคอนเฟตติแยกตามธีม
// - โหมดมืด: ทอง/น้ำเงิน/ขาว สว่างตัดพื้นเข้ม
// - โหมดสว่าง: สีเข้ม-สด ตัดกับพื้นกระดาษซีเปีย (ตัดสีขาว/ทองอ่อนที่กลืนพื้นออก)
const COLORS_DARK = ["#c3a260", "#e6c875", "#6b8cce", "#f0c265", "#ffffff", "#d4af37"];
const COLORS_LIGHT = ["#8a5a00", "#b8860b", "#2f4fa0", "#1f7a3f", "#a3322b", "#6b3fa0"];

// คอนเฟตติฉลองเมื่อเปิดเควสต์ที่เกลาภาษาไทยแล้ว (ไม่มีกล่อง dialog)
// คอมโพเนนต์นี้ถูก mount ใหม่ทุกครั้งที่เปลี่ยนเควสต์ (ผ่าน key) จึงเล่นอนิเมชันใหม่เสมอ
export default function RevisedCelebration() {
  const [visible, setVisible] = useState(true);
  const [light, setLight] = useState(false);

  useEffect(() => {
    setLight(document.documentElement.classList.contains("theme-light"));
    const t = setTimeout(() => setVisible(false), 4500);
    return () => clearTimeout(t);
  }, []);

  // สุ่มค่าตำแหน่ง/จังหวะของคอนเฟตติครั้งเดียวตอน mount (สีเลือกตามธีมตอน render)
  const pieces = useMemo(
    () =>
      Array.from({ length: 56 }, (_, i) => ({
        left: Math.random() * 100,
        delay: Math.random() * 0.6,
        duration: 2.4 + Math.random() * 1.8,
        width: 6 + Math.random() * 8,
        colorIndex: i % COLORS_DARK.length,
      })),
    []
  );

  if (!visible) return null;

  const palette = light ? COLORS_LIGHT : COLORS_DARK;

  return (
    <div className="absolute inset-0 z-40 pointer-events-none overflow-hidden" aria-hidden="true">
      {pieces.map((p, i) => (
        <span
          key={i}
          className="confetti-piece"
          style={{
            left: `${p.left}%`,
            width: `${p.width}px`,
            height: `${p.width * 0.4}px`,
            backgroundColor: palette[p.colorIndex],
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duration}s`,
          }}
        />
      ))}
    </div>
  );
}
