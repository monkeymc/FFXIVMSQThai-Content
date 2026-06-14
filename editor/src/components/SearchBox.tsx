"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, useEffect } from "react";

export default function SearchBox({ defaultValue }: { defaultValue?: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialSearch = defaultValue || searchParams.get("search") || "";
  
  const [searchTerm, setSearchTerm] = useState(initialSearch);

  useEffect(() => {
    // Debounce the search input to avoid spamming server
    const timer = setTimeout(() => {
      const currentQuery = searchParams.get("search") || "";
      const newQuery = searchTerm.trim();
      
      // ป้องกัน Infinite Loop: อัปเดต URL เฉพาะเวลาที่คำค้นหาต่างจากใน URL เท่านั้น
      if (currentQuery !== newQuery) {
        const currentParams = new URLSearchParams(searchParams.toString());
        if (newQuery) {
          currentParams.set("search", newQuery);
        } else {
          currentParams.delete("search");
        }
        
        router.push(`/?${currentParams.toString()}`);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [searchTerm, searchParams, router]);

  return (
    <input 
      type="text" 
      placeholder="ค้นหาชื่อไฟล์ หรือคำแปล..." 
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
      className="w-full bg-[var(--color-input-bg)] border border-[var(--color-input-border)] rounded p-2 text-[var(--color-ffxiv-text)] text-sm focus:outline-none focus:border-[var(--color-ffxiv-gold)] transition-colors"
    />
  );
}
