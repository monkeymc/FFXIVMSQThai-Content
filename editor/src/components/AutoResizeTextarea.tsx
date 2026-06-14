"use client";
import { useEffect, useRef, forwardRef, useImperativeHandle } from "react";

export interface AutoResizeTextareaHandle {
  textarea: HTMLTextAreaElement | null;
  adjustHeight: () => void;
}

interface AutoResizeTextareaProps {
  defaultValue: string;
  className?: string;
  name?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
}

const AutoResizeTextarea = forwardRef<AutoResizeTextareaHandle, AutoResizeTextareaProps>(
  ({ defaultValue, className, name, onChange }, ref) => {
    const internalRef = useRef<HTMLTextAreaElement>(null);

    const adjustHeight = () => {
      if (internalRef.current) {
        internalRef.current.style.height = "auto";
        internalRef.current.style.height = `${internalRef.current.scrollHeight}px`;
      }
    };

    useImperativeHandle(ref, () => ({
      adjustHeight,
      get textarea() {
        return internalRef.current;
      }
    }));

    useEffect(() => {
      adjustHeight();
      window.addEventListener("resize", adjustHeight);
      return () => window.removeEventListener("resize", adjustHeight);
    }, [defaultValue]);

    return (
      <textarea
        name={name}
        ref={internalRef}
        defaultValue={defaultValue}
        onChange={(e) => {
          adjustHeight();
          if (onChange) onChange(e);
        }}
        rows={1}
        className={`${className} overflow-hidden resize-none`}
      />
    );
  }
);

AutoResizeTextarea.displayName = "AutoResizeTextarea";
export default AutoResizeTextarea;
