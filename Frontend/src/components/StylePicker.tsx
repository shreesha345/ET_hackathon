"use client";

import { useState, useRef } from "react";
import { Plus } from "lucide-react";

interface CustomStyle {
  name: string;
  src: string;
  isCustom: true;
}

type StyleItem = { name: string; src: string } | CustomStyle;

const styles = [
  { name: "2D Line", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/2d%20line.webp" },
  { name: "Collage", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Blue%20collage.webp" },
  { name: "Animation", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/3d%20animatoin.webp" },
  { name: "Blue Vox", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Blue%20vox.webp" },
  { name: "Claymation", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Claymation.webp" },
  { name: "Claire", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Claire.webp" },
  { name: "Marcinelle", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Marcinelle.webp" },
  { name: "Pen&Ink", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Pen%20%26%20ink.webp" },
  { name: "Schematic", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Schematic.webp" },
  { name: "Vox", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Yellow%20vox.webp" },
  { name: "Watercolor", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Watercolor.webp" },
  { name: "Papercraft", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Papercraft.png" },
  { name: "Papercraft Mono", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Papercraft%20Peach.png" },
  { name: "Halftone", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Halftone.webp" },
  { name: "Economic", src: "https://prod-ao-ext.cdn.opus.pro/story-mode/styles/Economic.webp" },
];

export const StylePicker = ({ onHoverChange, onStyleSelect }: { onHoverChange?: (isHovering: boolean) => void; onStyleSelect?: (style: string | null) => void }) => {
  const [hoveredStyle, setHoveredStyle] = useState<string | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [customStyles, setCustomStyles] = useState<CustomStyle[]>([]);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allStyles: StyleItem[] = [...styles, ...customStyles];

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      const newStyle: CustomStyle = {
        name: `Custom ${customStyles.length + 1}`,
        src: url,
        isCustom: true,
      };
      setCustomStyles(prev => [...prev, newStyle]);
    }
    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-1">
      <p className="text-[11px] text-muted-foreground">Scroll to see more</p>
      <div className="w-full max-w-[460px] overflow-x-visible overflow-y-visible pr-14 scrollbar-hide cursor-grab relative">
        {hoveredStyle && hoveredIndex !== null && (
          <div
            className="absolute z-50 pointer-events-none"
            style={{
              left: `${(buttonRefs.current[hoveredIndex]?.offsetLeft ?? 0) + 35}px`,
              transform: 'translateX(-50%)',
              top: '-150px',
            }}
          >
            <div className="rounded-sm overflow-hidden border border-muted-foreground/20 shadow-lg">
              <video
                className="size-32 rounded-sm object-cover"
                loop
                playsInline
                poster={hoveredStyle}
                preload="auto"
                src={hoveredStyle.replace(/\.(webp|png)$/, '.webm')}
              />
            </div>
          </div>
        )}
        <div className="overflow-x-auto overflow-y-hidden scrollbar-hide">
          <div className="flex items-start gap-4">
            {/* Add style button */}
            <button
              className="flex w-[70px] shrink-0 flex-col items-center gap-1.5 group"
              type="button"
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="flex h-[68px] w-[50px] items-center justify-center rounded-sm border-2 border-white/[0.15] bg-white/[0.03] hover:bg-white/[0.06] transition-colors">
                <Plus className="w-4.5 h-4.5 text-secondary" />
              </div>
              <span className="text-secondary line-clamp-2 max-w-[70px] text-center text-xs font-medium leading-[15px]">
                Add style
              </span>
            </button>

            {/* Divider */}
            <div className="flex h-[68px] shrink-0 items-center justify-center px-1">
              <div className="h-8 w-px shrink-0 bg-white/20"></div>
            </div>

            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              className="hidden"
            />

            {allStyles.map((style, index) => (
              <button
                key={style.name}
                ref={(el) => (buttonRefs.current[index] = el)}
                className={`flex w-[70px] shrink-0 flex-col items-center gap-1.5 group transition-all ${
                  selectedIndex === index ? "opacity-100" : ""
                }`}
                type="button"
                onClick={() => {
                  setSelectedIndex(selectedIndex === index ? null : index);
                  onStyleSelect?.(selectedIndex === index ? null : style.src);
                }}
                onMouseEnter={() => {
                  setHoveredStyle(style.src);
                  setHoveredIndex(index);
                  onHoverChange?.(true);
                }}
                onMouseLeave={() => {
                  setHoveredStyle(null);
                  setHoveredIndex(null);
                  onHoverChange?.(false);
                }}
              >
                <div
                  className={`h-[68px] w-[50px] overflow-hidden rounded-sm transition-all duration-200 hover:opacity-35 border-2 ${
                    selectedIndex === index
                      ? "border-foreground"
                      : "border-transparent"
                  }`}
                >
                  <img
                    alt={style.name}
                    className="size-full rounded-sm object-cover"
                    src={style.src}
                  />
                </div>
                <span className="text-secondary line-clamp-2 max-w-[70px] overflow-hidden text-center text-xs font-medium leading-[15px]">
                  {style.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
